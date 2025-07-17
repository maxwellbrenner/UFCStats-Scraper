#src/scraper/models/fighter.py

"""Fighter model for the UFC Stats Scraper.

This module defines the `Fighter` class, which represents a UFC fighter and their attributes (name, height, reach, and date of birth). 
It provides functionality to parse fighter details from a fighter's page and cache the results for efficiency.

Key components:
- `Fighter`: A dataclass representing a UFC fighter with attributes for link, name, height, reach, and DOB.
- `create_fighter()`: Populates the Fighter object by parsing fighter page HTML.
- `parse_fighter_name()`, `parse_height()`, `parse_reach()`, `parse_dob()`: Helper methods for parsing specific attributes.
- `to_string()`: Formats fighter details into a string for display.

The class integrates with the `fetch` module for HTML retrieval and uses thread-safe caching to avoid redundant requests.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup
from ..fetch import get_page_content, FIGHTER_CACHE, CACHE_LOCK

@dataclass(init=False)
class Fighter:
    """
    Attributes
    ----------
    link        : URL of the fighter-details page (always kept)
    name        : Fighter’s full name
    height_in   : Height in inches              
    reach_in    : Reach in inches               
    dob         : Date of birth as datetime.date
    """
    link: str
    name: Optional[str] = field(default=None, init=False)
    height_in: Optional[int] = field(default=None, init=False)
    reach_in: Optional[int] = field(default=None, init=False)
    dob: Optional[date] = field(default=None, init=False)

    def __init__(self, link: str, fighter_soup: Optional[BeautifulSoup] = None) -> None:
        self.link = link
        with CACHE_LOCK:
            if self.link in FIGHTER_CACHE:
                cached = FIGHTER_CACHE[self.link]
                self.name = cached.name
                self.height_in = cached.height_in
                self.reach_in = cached.reach_in
                self.dob = cached.dob
                return
        self.create_fighter(fighter_soup)  # Pass fighter_soup to create_fighter()
        with CACHE_LOCK:
            FIGHTER_CACHE[self.link] = self

    def create_fighter(self, fighter_page_soup: Optional[BeautifulSoup] = None) -> None:
        """
        Populates fighter attributes from a pre-fetched BeautifulSoup object or by fetching the fighter's page.
    
        Parameters:
            fighter_page_soup (Optional[BeautifulSoup]): Pre-fetched BeautifulSoup object containing the fighter's page HTML.
                                                         If None, the method fetches the page using the fighter's link.
    
        Returns:
            None
    
        Functionality:
            - Fetches the fighter's page HTML using get_page_content() if no fighter_page_soup is provided.
            - Parses the fighter's name from the highlighted title section.
            - Extracts fighter details (height, reach, date of birth) from the page's list elements.
            - Populates the Fighter object's attributes: name, height_in, reach_in, and dob.
            - Caches the Fighter object only if the name is successfully parsed to avoid incomplete data.
        """
        # Fetch fighter page HTML if no soup is provided
        fighter_page_soup = get_page_content(self.link) if fighter_page_soup is None else fighter_page_soup
        if fighter_page_soup is None:
            print(f"[Fighter] Could not fetch page: {self.link}")
            return

        # Parse fighter name
        self.name = self.parse_fighter_name(fighter_page_soup)

        # Extract details from list elements
        details = {}
        for li in fighter_page_soup.select('ul.b-list__box-list li'):
            try:
                label = li.i.get_text(strip=True).rstrip(':').upper()
                value = li.i.next_sibling.strip()
                details[label] = value
            except AttributeError:
                print("[Fighter] Malformed <li> skipped.")
                continue

        # Parse and assign height, reach, and date of birth
        self.height_in = self.parse_height(details.get("HEIGHT"))
        self.reach_in = self.parse_reach(details.get("REACH"))
        self.dob = self.parse_dob(details.get("DOB"))
    
        # Skip caching if name is missing to avoid incomplete data
        if self.name is None:
            print(f"[Fighter] Skipping cache due to missing name: {self.link}")
            return

    # -----------------------------------------------------------------------
    # individual helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def parse_fighter_name(fighter_page_soup: BeautifulSoup) -> Optional[str]:
        """
        Extracts the fighter's name from the highlighted title section of their page.
        """
        span = fighter_page_soup.find('span', class_='b-content__title-highlight')
        if span:
            return span.get_text(strip=True)
        print("[Fighter] Name not found.")
        return None

    @staticmethod
    def parse_height(height_string: Optional[str]) -> Optional[int]:
        """
        Converts a height string in the format 'X' Y"' to total inches (e.g. 6' 1" → 73).
        """
        if not height_string:
            return None
        match = re.match(r"(\d+)'[\s]*(\d+)", height_string)
        if match:
            feet, inches = map(int, match.groups())
            return feet * 12 + inches
        print(f"[Fighter] Height parse fail: {height_string}")
        return None

    @staticmethod
    def parse_reach(reach_string: Optional[str]) -> Optional[int]:
        """
        Converts a reach string in the format 'X"' to an integer (e.g. 76"   → 76).
        """
        if not reach_string:
            return None
        match = re.search(r"\d+", reach_string)
        if match:
            return int(match.group(0))
        print(f"[Fighter] Reach parse fail: {reach_string}")
        return None


    @staticmethod
    def parse_dob(dob_string: Optional[str]) -> Optional[date]:
        """
        Parses a date of birth string in 'Mon DD, YYYY' format into a date object.
        """
        if not dob_string:
            return None
        try:
            return datetime.strptime(dob_string, '%b %d, %Y').date()
        except ValueError:
            print(f"[Fighter] DOB parse fail: {dob_string}")
            return None
    
    def to_string(self) -> str:
        return (
            f"Fighter Profile:\n"
            f"Link: {self.link}\n"
            f"Name: {self.name}\n"
            f"Height (in): {self.height_in}\n"
            f"Reach (in): {self.reach_in}\n"
            f"DOB: {self.dob}"
        )
