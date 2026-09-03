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


def minutes_link(panel):
    """Return the minutes URL for a meeting panel."""

    paragraphs = panel.find_all("p")
    
    minutes_para = None
    for p in paragraphs:
        if "Minutes" in p.get_text():
            minutes_para = p
            break

    links = minutes_para.find_all("a")

    # PDF link preferable over HTML
    for link in links:
        if link.get_text() == "PDF":
            return link["href"]

    if len(links) != 0:
        return links[0]['href']


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
            minutes_url = minutes_link(panel)


if __name__ == "__main__":
    main()