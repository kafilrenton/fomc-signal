# Imports
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime


# Link extractor functions

def statement_link(panel):
    """Return the statement URL for a meeting panel."""
  
    link = panel.find("a", string="Statement") 

    if link is not None:
        return link['href']


def minutes_info(panel):
    """Return the minutes release date and URL for a meeting panel."""

    paragraphs = panel.find_all("p")

    minutes_para = None
    for p in paragraphs:
        if "Minutes" in p.get_text():
            minutes_para = p
            break

    if minutes_para is None:
        return None, None

    # Regex for release date
    date = re.search(
        r"\(Released\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\)",
        minutes_para.get_text(),
    )
    date = date.groups() if date else None

    links = minutes_para.find_all("a")

    # HTML link over PDF (simpler with text extraction as some PDFs are split page text)
    for link in links:
        if link["href"].endswith(".htm"):
            return link["href"], date

    return None, None


def conference_link(panel):
    """Return the press conference transcript URL for a meeting panel"""

    # Does not return the immediate link within the panel
    # Rather it returns the PDF URL within the press conference page of said immediate link

    link = panel.find("a", string="Press Conference")

    if link is not None:
        r = requests.get(f"https://www.federalreserve.gov{link['href']}")
        s = BeautifulSoup(r.content, "html.parser")

        pdf_link = s.find("a", string=re.compile(r"Press Conference Transcript.*"))

        if pdf_link is not None:
            return pdf_link['href']

    return None


# Text extractor functions

def clean_text(text):
    """Normalise whitespace in extracted paragraph text."""

    if text is None:
        return ""
    text = text.replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def statement_text(url):
    """Return cleaned statement text for a statement URL."""
    
    if url is None:
        return None
    
    r = requests.get(f"https://www.federalreserve.gov{url}")
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

    r = requests.get(f"https://www.federalreserve.gov{url}")
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
        date = date_text
        
    else:
        # Regex targetted towards labelling for panels in 2000-2020
        date = re.search(
        r"(?:[A-Za-z]+/)?([A-Za-z]+)\s+(?:\d{1,2}-)?(\d{1,2})\s+Meeting\s+-\s+(\d{4})",
        date_text
        ).groups() 

    month, day, year = date

    # Formatting possibilites from the regex output (e.g. January 10 2000 OR Jan 10 2000)
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(f"{month} {day} {year}", fmt).date()
        except ValueError:
            continue
    return None


# Main implementation

def main():
    """Scrape FOMC statement, minutes and press conference material from 2000-2026."""

    all_rows = []

    # Response loop for meeting data over years 2000-2020
    # Filters <div>'s only relevant to meetings, excluding conference calls etc
    for year in range(2000, 2021):
        response = requests.get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
        soup = BeautifulSoup(response.content, "html.parser")

        top_panels = soup.find_all("div", class_=re.compile(r"panel panel-default.*")) 
        
        top_panels = [
            panel for panel in top_panels
            if panel.find("h5", string=re.compile("Meeting"))
            and panel.find("a", string="Statement")
            and re.search(r"\(Released\s+", panel.get_text())
        ]       

        for panel in top_panels:
            meeting_date = panel.find("h5").string
            statement_url = statement_link(panel)
            minutes_url, minutes_date = minutes_info(panel)
            transcript_url = conference_link(panel)

            row = {
                "date": convert_to_iso(meeting_date),
                "statement": statement_text(statement_url),
                "minutes_release": convert_to_iso(minutes_date),
                "minutes": minutes_text(minutes_url),
                "conference": ...,
            }
            all_rows.append(row)


if __name__ == "__main__":
    main()