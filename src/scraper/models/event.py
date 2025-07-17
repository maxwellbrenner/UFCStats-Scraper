#src/scraper/models/event.py

"""Event model for the UFC Stats Scraper.

This module defines the `Event` class, which represents a UFC event and its associated fights. 
It provides functionality to parse fight links from an event page, create `Fight` objects, and format event details for output.

Key components:
- `Event`: A dataclass representing a UFC event with attributes for link, name, date, location, and a list of fights.
- `parse_fight_links()`: Extracts fight detail URLs from the event page HTML.
- `create_fights()`: Populates the fights list by fetching and parsing fight pages.
- `to_string()`: Formats event details into a string for display.

The class integrates with the `fetch` module for HTML retrieval and the `Fight` model for fight data processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
import re
from ..fetch import get_page_content, fetch_parallel
from .fight import Fight

@dataclass
class Event:
    """
    Attributes
    ----------
    link     : URL of the event-details page
    name     : Name of the UFC event
    date     : Date of the event as datetime.date
    location : Location of the event (city, state/country)
    fights   : List of Fight objects associated with the event
    """
    link: str
    name: Optional[str]
    date: Optional[datetime.date]
    location: Optional[str]
    fights: List["Fight"] = field(default_factory=list)  # Forward Reference as Fight Class has not yet been defined

    def parse_fight_links(self) -> List[str]:
        """
        Parses fight links from an event page.

        Returns:
            List[str]: A list of URLs pointing to fight pages.

        Functionality:
            - Fetches the event page HTML using get_page_content().
            - Identifies table rows (<tr>) with an onclick attribute containing 'doNav()'.
            - Extracts fight links from the doNav() function calls.
            - Returns an empty list if the page fetch fails or no valid fight links are found.
        """
        # Fetch event page HTML
        event_page_soup = get_page_content(self.link)
        if not event_page_soup:
            print(f"[Event] Could not fetch event page: {self.link}")
            return []
    
        # Find all <tr> elements with onclick containing doNav()
        fight_rows = event_page_soup.find_all('tr', onclick=lambda value: value and 'doNav(' in value)
        if not fight_rows:
            print(f"[Event] No fight rows with onclick='doNav()' found: {self.link}")
            return []
    
        # Extract URLs from the doNav() call
        fight_links = []
        for row in fight_rows:
            onclick = row.get('onclick', '')
            match = re.search(r"doNav\('([^']+)'\)", onclick)
            if match:
                link = match.group(1)
                # Ensure the link is a valid fight details URL
                if link.startswith('http://ufcstats.com/fight-details/'):
                    fight_links.append(link.strip())
    
        return fight_links
    
    def create_fights(self) -> None:
        """
        Populates the event's fights list by creating Fight objects from parsed fight links.

        Returns:
            None

        Functionality:
            - Calls parse_fight_links() to retrieve fight links.
            - Fetches fight pages in parallel using fetch_parallel() for efficiency.
            - Creates a Fight object for each valid fight page and appends it to self.fights.
        """
        # Retrieve fight links for the event
        fight_links = self.parse_fight_links()
        if not fight_links:
            print(f"[Event] No fight links found for event: {self.link}")
            return
        
        # Parallel fetch all fight pages
        fight_soups = fetch_parallel(fight_links)
        
        for link in fight_links:
            try:
                if fight_soups.get(link) is None:
                    print(f"[Event] Skipping fight due to failed fetch: {link}")
                    continue
                # Create Fight object with pre-fetched soup
                fight = Fight(link, fight_soups.get(link))
                self.fights.append(fight)
            except Exception as e:
                print(f"[Event] Failed to create Fight from link {link}: {e}")
                
    def to_string(self, scrape_time: Optional[float] = None) -> str:
        output = (
            f"Name: {self.name}\n"
            f"Date: {self.date}\n"
            f"Location: {self.location}\n"
            f"Link: {self.link}\n"
            f"Number of Fights: {len(self.fights)}"
        )
        if scrape_time is not None:
            output += f"\nScrape Time (sec): {scrape_time:.2f}"
        return output
