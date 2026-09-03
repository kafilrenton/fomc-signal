# Imports
import re
import requests
from bs4 import BeautifulSoup


def main():

    # Response loop for meeting data over years 2000-2020
    # Filters <div>'s only relevant to meetings, excluding conference calls etc
    for year in range(2000, 2021):
        response = requests.get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
        soup = BeautifulSoup(response.content, "html.parser")

        top_panels = soup.find_all("div", class_=re.compile(r"panel panel-default.*")) 
        
        top_panels = [panel for panel in top_panels if panel.find("h5", string=re.compile("Meeting"))]


if __name__ == "__main__":
    main()