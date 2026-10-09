# Imports
import re
import requests
from bs4 import BeautifulSoup


# Functions to be used in main loop
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

    date = re.search(
        r"\(Released\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\)",
        minutes_para.get_text(),
    )
    date = date.groups() if date else None

    links = minutes_para.find_all("a")

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


def main():
    """Scrape FOMC statement, minutes and press conference material from 2000-2026."""

    # Response loop for meeting data over years 2000-2020
    # Filters <div>'s only relevant to meetings, excluding conference calls etc
    for year in range(2000, 2021):
        response = requests.get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
        soup = BeautifulSoup(response.content, "html.parser")

        top_panels = soup.find_all("div", class_=re.compile(r"panel panel-default.*")) 
        
        top_panels = [panel for panel in top_panels if panel.find("h5", string=re.compile("Meeting"))]

        for panel in top_panels:
            statement_url = statement_link(panel)
            minutes_url, minutes_date = minutes_info(panel)
            transcript_url = conference_link(panel)


if __name__ == "__main__":
    main()