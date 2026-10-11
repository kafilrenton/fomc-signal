# Imports
import re
import requests
import io
import pdfplumber
import csv
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm


# Path to output folder
datasets = Path(__file__).resolve().parents[2]/"datasets"


# Link extractor functions

def full_url(href):
    """Prepend the base URL unless href is already complete."""
    
    base = "https://www.federalreserve.gov"
    return href if href.startswith("http") else base + href


def statement_link(panel):
    """Return the statement URL for a meeting panel."""
  
    link = panel.find("a", string="Statement") 

    if link is not None:
        return link['href']

    # Accounting for different formatting in years 2021+
    strong = panel.find("strong", string=re.compile("Statement"))
    if strong is not None:
        for a in strong.find_next_siblings("a"):
            if a.get_text() == "PDF":
                return a["href"]


def minutes_info(panel):
    """Return the minutes release date and URL for a meeting panel."""

    # Regex for release date
    date_pattern = r"\(Released\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\)"

    # Old era       
    paragraphs = panel.find_all("p")
    minutes_para = None
    for p in paragraphs:
        if "Minutes" in p.get_text():
            minutes_para = p
            break

    if minutes_para is not None:
        match = re.search(date_pattern, minutes_para.get_text())
        date = match.groups() if match else None

        for link in minutes_para.find_all("a"):
            if link["href"].endswith(".htm"):
                return link["href"], date

        return None, None

    # New era
    strong = panel.find("strong", string=re.compile("Minutes"))
    if strong is not None:
        container = strong.parent
        match = re.search(date_pattern, container.get_text())
        date = match.groups() if match else None

        # HTML link over PDF (simpler with text extraction as some PDFs are split page text)
        for link in container.find_all("a"):
            if link.get_text() == "HTML":
                return link["href"], date

    return None, None


def conference_link(panel):
    """Return the press conference transcript URL for a meeting panel"""

    # Does not return the immediate link within the panel
    # Rather it returns the PDF URL within the press conference page of said immediate link

    link = panel.find("a", string="Press Conference")
    if link is None:
        return None

    r = requests.get(full_url(link["href"]))
    if r.status_code != 200:
        return None
    s = BeautifulSoup(r.content, "html.parser")

    pdf_link = s.find("a", string=re.compile(r"Press Conference Transcript.*"))
    if pdf_link is not None:
        return pdf_link["href"]

    return None


# Text extractor functions

def clean_text(text):
    """Normalise whitespace in extracted paragraph text."""

    if text is None:
        return ""
    text = text.replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def pdf_text(url):
    """Return the full text of a PDF at the given URL"""
    
    if url is None:
        return None

    r = requests.get(full_url(url))
    if r.status_code != 200:
        return None

    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        text = " ".join(page.extract_text() or "" for page in pdf.pages)

    return clean_text(text)


def statement_text(url):
    """Return cleaned statement text for a statement URL."""
    
    if url is None:
        return None

    if url.endswith(".pdf"):
        return pdf_text(url)
    
    r = requests.get(full_url(url))
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.content, "html.parser")

    # Text extraction route for HTML text is dependent on year of release

    # Modern era 
    article = soup.find("div", id="article")
    if article is not None:
        paras = [clean_text(p.get_text()) for p in article.find_all("p")]
        text = " ".join(p for p in paras if p)
        if "Federal Open Market Committee" in text:
            return text

    # Old era 
    table = soup.find("table", attrs={"width": "600"})
    if table is not None:
        text = clean_text(table.get_text())

        # Trim trailing footer
        text = re.sub(r"\s*\d{4} Monetary policy.*$", "", text).strip()
        return text

    return None


def minutes_text(url):
    """Return cleaned minutes body text for an HTML minutes URL"""

    if url is None:
        return None

    r = requests.get(full_url(url))
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.content, "html.parser")

    # Similar to statement HTMLs, formatting for the minutes is dependent on year of release
    # Found three eras of different source code so three extraction routes

    # Modern era
    article = soup.find("div", id="article")
    if article is not None:
        paras = [clean_text(p.get_text()) for p in article.find_all("p")]
        return " ".join(p for p in paras if p)

    # Middle era
    left = soup.find("div", id="leftText")
    if left is not None:
        paras = [clean_text(p.get_text()) for p in left.find_all("p")]
        return " ".join(p for p in paras if p)

    # Old era formatting
    marker = soup.find("hr", attrs={"size": "+4"})
    if marker is not None:
        body = marker.find_next("td", attrs={"width": "600"})
        if body is not None:
            paras = [clean_text(p.get_text()) for p in body.find_all("p")]
            return " ".join(p for p in paras if p)

    return None


# Other functions

def convert_to_iso(date_text):
    """Convert a written date to a datetime.date object."""

    if date_text is None:
        return None

    if isinstance(date_text, tuple):
        month, day, year = date_text
    else:
        # Regex targetted towards labelling for panels in 2000-2020
        match = re.search(
            r"([A-Za-z]+)\s+(?:\d{1,2}-)?(\d{1,2})\s*(?:\([^)]*\))?\s+Meeting\s+-\s+(\d{4})",
            date_text,
        )
        if match is None:
            return None
        month, day, year = match.groups()

    month = month.split("/")[-1]
    # Formatting possibilites from the regex output (e.g. January 10 2000 OR Jan 10 2000)
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(f"{month} {day} {year}", fmt).date()
        except ValueError:
            continue
    return None


def quick_date(panel, year):
    """Return tuple containing date from new-era meeting panel."""

    month = panel.find("div", class_=re.compile(r".*fomc-meeting__month.*")).string

    # Meetings typical over two day periods, so final date is when statemtent and press conference happen,
    # and some are meetings associated with a Summary of Economic Projections, indicated by * which need removal
    day = re.sub(
        r"\d{1,2}-", "",
        panel.find("div", class_=re.compile(r".*fomc-meeting__date.*")).string,
    ).rstrip("*") # Some meetings associated with a Summary of Economic Projections, indicated by *

    return month, day, year


# Main implementation

def main():
    """Scrape FOMC statement, minutes and press conference material from 2000-2026."""

    all_rows = []

    # Response loop for meeting data over years 2000-2026
    # Filters <div>'s only relevant to meetings, excluding conference calls etc
    for year in tqdm(range(2000, 2027), desc="Scraping"):

        if year < 2021:
            fed_link = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
        else:
            fed_link = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"        

        response = requests.get(fed_link)
        soup = BeautifulSoup(response.content, "html.parser")

        # Branches for recent years versus older years as the HTML is not consistent across these periods
        if year < 2021:
            top_panels = soup.find_all("div", class_=re.compile(r"panel panel-default.*")) 
            
            top_panels = [
                panel for panel in top_panels
                if panel.find("h5", string=re.compile("Meeting"))
                and panel.find("a", string="Statement")
                and re.search(r"\(Released\s+", panel.get_text())
            ]
        else:
            panel_marker = soup.find("a", string=f"{year}")["href"]  
            anchor_id = panel_marker.lstrip("#")  
            anchor = soup.find("a", id=anchor_id)
            panel = anchor.find_parent("div", class_="panel panel-default")
            top_panels = panel.find_all("div", class_=re.compile(r".*row fomc-meeting$"))
            top_panels = [p for p in top_panels if p.find("strong", string=re.compile("Statement"))]

        # Build one row per meeting for the CSV export
        for panel in top_panels:
            if year < 2021:
                meeting_date = panel.find("h5").string
            else:
                meeting_date = quick_date(panel, year)
            statement_url = statement_link(panel)
            minutes_url, minutes_date = minutes_info(panel)
            conference_url = conference_link(panel)

            row = {
                "date": convert_to_iso(meeting_date),
                "statement": statement_text(statement_url),
                "minutes_release": convert_to_iso(minutes_date),
                "minutes": minutes_text(minutes_url),
                "conference": pdf_text(conference_url),
            }

            all_rows.append(row)

    # Create output folder on first run, no error if it exists already
    datasets.mkdir(exist_ok=True)

    # CSV exports for each content type
    with open(datasets/"statement.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["date", "statement"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in all_rows:
            writer.writerow({"date": row["date"], "statement": row["statement"]})

    with open(datasets/"minutes.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["date", "minutes_release", "minutes"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in all_rows:
            writer.writerow({"date": row["date"], "minutes_release": row["minutes_release"], "minutes": row["minutes"]})

    with open(datasets/"conference.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["date", "conference_transcript"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in all_rows:
            writer.writerow({"date": row["date"], "conference_transcript": row["conference"]})


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScraping interrupted. No CSVs written.")