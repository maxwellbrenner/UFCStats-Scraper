#src/scraper/models/fight.py

"""Fight model for the UFC Stats Scraper.

This module defines the `Fight` class, which represents a UFC fight and its associated details, including fighters, outcome, and round statistics. 
It provides functionality to parse fight details, create `Fighter` and `Round` objects, and format fight information for output.

Key components:
- `Fight`: A dataclass representing a UFC fight with attributes for link, gender, title fight status, fighters, winner, weight class, and rounds.
- `create_fight()`: Populates the Fight object by parsing fight page HTML.
- `parse_fighters()`: Extracts and creates Fighter objects for both fighters.
- `create_rounds()`: Populates the rounds list with Round objects.
- `parse_fight_details()`, `parse_winner()`, `parse_weight_class()`, etc.: Helper methods for parsing specific fight attributes.
- `to_string()`: Formats fight details into a string for display.

The class integrates with the `fetch`, `Fighter`, and `Round` modules for data retrieval and processing.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup
import re
from .fighter import Fighter
from .round import Round
from ..fetch import fetch_parallel, get_page_content

@dataclass(init=False)
class Fight:
    """
    Attributes
    ----------
    link                : URL of the fight-details page
    gender              : Gender of the fight ("M" for men, "F" for women)
    title_fight         : Boolean indicating if the fight is a title fight
    fighter_a           : Fighter object for the first fighter
    fighter_b           : Fighter object for the second fighter
    winner              : Outcome of the fight ("A", "B", "Draw", or "NC")
    weight_class        : Weight class in pounds (e.g., 155 for lightweight, 0 for catchweight)
    method_of_victory   : Method by which the fight was decided (e.g., "KO", "Submission")
    round_of_victory    : Round in which the fight ended (1-5)
    time_of_victory_sec : Time of fight conclusion in seconds
    time_format         : Scheduled number of rounds (3 or 5)
    referee             : Name of the referee
    rounds              : List of Round objects containing per-round statistics
    """
    link: str
    gender: str  # "M" for men, "F" for women
    title_fight: bool # Defaults to False 
    fighter_a: Optional[Fighter] = field(init=False)
    fighter_b: Optional[Fighter] = field(init=False)
    winner: Optional[str] = field(init=False)   # "A", "B", "Draw", or "NC"
    weight_class: Optional[int] = field(init=False) # Catchweight = 0
    method_of_victory: Optional[str] = field(init=False)
    round_of_victory: Optional[int] = field(init=False)  # takes int value 1-5
    time_of_victory_sec: Optional[int] = field(init=False) # converted from mm:ss to sec (int)
    time_format: Optional[int] = field(init=False) # takes int value of either 3 or 5
    referee: Optional[str] = field(init=False)
    rounds: List[Round] = field(init=False)     # populated by create_rounds()

    # -----------------------------------------------------------------------
    # constructor
    # -----------------------------------------------------------------------
    def __init__(self, link: str, fight_page_soup: Optional[BeautifulSoup] = None) -> None:
        self.link = link
        self.gender = "M"
        self.title_fight = False
        self.create_fight(fight_page_soup)

    def create_fight(self, pre_fetched_content: Optional[BeautifulSoup] = None) -> None:
        """
        Populates the Fight object by parsing fight details from a pre-fetched BeautifulSoup object or by fetching the fight page.
    
        Parameters:
            pre_fetched_content (Optional[BeautifulSoup]): Pre-fetched BeautifulSoup object containing the fight page HTML.
                                                           If None, the method fetches the page using the fight's link.
    
        Returns:
            None
    
        Functionality:
            - Fetches the fight page HTML using `get_page_content` if no pre-fetched content is provided.
            - Calls parse_fighters() to extract and create Fighter objects for both fighters.
            - Calls parse_winner() and parse_weight_class() to populate winner, weight class, gender, and title fight attributes.
            - Parses fight details (method, round, time, time format, referee) using parse_fight_details() and helper methods.
            - Calls create_rounds() to populate the rounds list if both fighters are valid and fighter links are available.
        """
        fight_page_soup = pre_fetched_content or get_page_content(self.link)
        if fight_page_soup is None:
            print(f"[Fight] Could not fetch page: {self.link}")
            return
            
        self.parse_fighters(fight_page_soup)
        if self.fighter_a is None or self.fighter_b is None:
            print(f"[Fight] Skipping further processing due to missing fighter data: {self.link}")
            return

        self.parse_winner(fight_page_soup)
        self.parse_weight_class(fight_page_soup)

        details = self.parse_fight_details(fight_page_soup)

        self.method_of_victory = details.get("METHOD")
        self.round_of_victory = self.parse_round_of_victory(details.get("ROUND"))
        self.time_of_victory_sec = self.parse_mm_ss(details.get("TIME"))
        self.time_format = self.parse_time_format(details.get("TIME FORMAT"))
        self.referee = details.get("REFEREE")

        fighter_links = (self.fighter_a.link, self.fighter_b.link) if self.fighter_a and self.fighter_b else None

        if fighter_links:
            self.create_rounds(self.round_of_victory, fight_page_soup, fighter_links)

    def parse_fighters(self, fight_page_soup: BeautifulSoup) -> None:
        """
        Extracts fighter information from the fight page HTML and populates fighter_a and fighter_b attributes.
    
        Parameters:
            fight_page_soup (BeautifulSoup): A BeautifulSoup object containing the fight page HTML.
    
        Returns:
            None
    
        Functionality:
            - Selects anchor tags with class 'b-fight-details__person-link' to extract fighter links.
            - Raises a ValueError if exactly two fighter links are not found, indicating a malformed fight page.
            - Fetches fighter pages in parallel using fetch_parallel() with a maximum of two workers for efficiency.
            - Creates Fighter objects for both fighters using their respective links and pre-fetched HTML content.
            - Assigns the created Fighter objects to self.fighter_a and self.fighter_b.
        """
        anchors = fight_page_soup.select("div.b-fight-details__persons a.b-fight-details__person-link")
        if len(anchors) != 2:
            raise ValueError("[Fight] Expected two fighter links, found different count.")
        
        fighter_links = [anchors[0]["href"].strip(), anchors[1]["href"].strip()]
        fighter_soups = fetch_parallel(fighter_links, max_workers=2)
        
        self.fighter_a = Fighter(fighter_links[0], fighter_soups.get(fighter_links[0]))
        self.fighter_b = Fighter(fighter_links[1], fighter_soups.get(fighter_links[1]))
        
        if self.fighter_a is None or self.fighter_b is None:
            print(f"[Fight] Failed to create one or both fighters for fight: {self.link}")

    def create_rounds(self, num_rounds: int, fight_page_soup: BeautifulSoup, fighter_links: Tuple[str, str]) -> None:
        """
        Populates the rounds list with Round objects for the specified number of rounds.
    
        Parameters:
            num_rounds (int): The number of rounds to create (tderived from round_of_victory).
            fight_page_soup (BeautifulSoup): A BeautifulSoup object containing the fight page HTML.
            fighter_links (Tuple[str, str]): A tuple containing the links of the two fighters (fighter_a, fighter_b).
    
        Returns:
            None
    
        Functionality:
            - Initializes an empty list for self.rounds.
            - Iterates from 1 to num_rounds (inclusive) to create a Round object for each round.
            - Instantiates each Round object with the round number, fight page HTML, and fighter links.
            - Appends each Round object to self.rounds.
            - Relies on the Round class to handle per-round statistics parsing and assignment.
            - Assumes num_rounds is valid (1-5) and derived from round_of_victory.
        """
        self.rounds = []

        for round_number in range(1, num_rounds + 1):
            # Round class will later accept (round_number, soup)
            self.rounds.append(Round(round_number, fight_page_soup, fighter_links))
            
    # -----------------------------------------------------------------------
    # individual helpers
    # -----------------------------------------------------------------------
    def parse_fight_details(self, fight_page_soup: BeautifulSoup) -> dict[str, str]:
        """
        Parses the fight details section of the fight page HTML into a dictionary keyed by uppercase labels.
    
        Parameters:
            fight_page_soup (BeautifulSoup): A BeautifulSoup object containing the fight page HTML.
    
        Returns:
            dict[str, str]: A dictionary mapping uppercase labels (e.g., 'METHOD', 'ROUND') to their corresponding values.
    
        Functionality:
            - Selects the fight details block using the CSS selector 'div.b-fight-details__content p.b-fight-details__text'.
            - Returns an empty dictionary if the details block is not found.
            - Iterates through all <i> elements with class 'b-fight-details__label' to extract labels and their associated values.
            - For each label, extracts the text following the colon in the parent element, strips whitespace, and normalizes multiple spaces.
            - Converts labels to uppercase and stores them with their values in the dictionary.
        """
        details = {}
        block = fight_page_soup.select_one("div.b-fight-details__content p.b-fight-details__text")
        if not block:
            return details
    
        for label_tag in block.select("i.b-fight-details__label"):
            label = label_tag.get_text(strip=True).rstrip(":").upper()
            parent = label_tag.parent
            value = parent.get_text(" ", strip=True).split(":", 1)[-1].strip()
            details[label] = re.sub(r"\s+", " ", value)
    
        return details

    def parse_round_of_victory(self, value: Optional[str]) -> Optional[int]:
        """
        Converts a string representing the round of victory to an integer.
        """
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    
    def parse_mm_ss(self, value: Optional[str]) -> Optional[int]:
        """
        Converts a time string in 'MM:SS' format to total seconds.
        """
        if value and (match := re.match(r"(\d+):(\d+)", value)):
            minutes, seconds = map(int, match.groups())
            return minutes * 60 + seconds
        return None
    
    def parse_time_format(self, value: Optional[str]) -> Optional[int]:
        """
        Extracts the scheduled number of rounds from a time format string.
        """
        if value and (match := re.match(r"\d+", value)):
            return int(match.group())
        return None
    
    def parse_winner(self, fight_page_soup: BeautifulSoup) -> None:
        """
        Determines the winner based on result icons in the fight detail section.
    
        Looks for:
        - <i class="b-fight-details__person-status">W/L/D/NC</i>
    
        Mapping:
        - 'W' => "A" (fighter_a)
        - 'L' => "B" (fighter_b)
        - 'D' => "Draw" (draw)
        - 'NC' => "NC" (no contest)
    
        If no result is found, winner remains None.
        """
        result_tag = fight_page_soup.select_one("div.b-fight-details__person i.b-fight-details__person-status")
        result_text = result_tag.get_text(strip=True) if result_tag else None
        result_mapping = {"W": "A", "L": "B", "D": "Draw", "NC": "NC"}
        self.winner = result_mapping.get(result_text)
        
    @staticmethod
    def map_weight_class(weight_class_tag: str) -> Optional[int]:
        """
        Maps a weight class string to its weight limit in pounds.
        """
        weight_class_tag = weight_class_tag.lower()
        
        # Ordered patterns: more specific ones first
        mapping = [
                ("catch", 0),
                ("light heavy", 205),
                ("straw", 115),
                ("fly", 125),
                ("bantam", 135),
                ("feather", 145),
                ("light", 155),
                ("welter", 170),
                ("middle", 185),
                ("heavy", 265),
        ]

        return next((limit for key, limit in mapping if key in weight_class_tag), None)
    
    def parse_weight_class(self, fight_page_soup: BeautifulSoup) -> None:
        """
        Extracts the weight class string, infers gender and title fight status, then maps it to a numerical value.
        """
        weight_class_tag = fight_page_soup.select_one("i.b-fight-details__fight-title")
        weight_class_str = weight_class_tag.get_text(strip=True) if weight_class_tag else None
    
        self.weight_class = self.map_weight_class(weight_class_str) if weight_class_str else None
    
        if weight_class_str:
            if self.is_womens_fight(weight_class_str):
                self.gender = "F"
            if self.is_title_fight(weight_class_str):
                self.title_fight = True          
    
    def is_womens_fight(self, weight_class_tag: str) -> bool:
        """
        Determines if the fight is a women's fight based on the weight class string.
        """
        return 'women' in weight_class_tag.lower()
    
    def is_title_fight(self, weight_class_tag: str) -> bool:
        """
        Determines if the fight is a title fight based on the weight class string.
        """
        return 'title' in weight_class_tag.lower()
        
    def to_string(self) -> str:
        return (
            f"Fight Summary:\n"
            f"Link: {self.link}\n"
            f"Fighter A: {self.fighter_a.name}\n"
            f"Fighter B: {self.fighter_b.name}\n"
            f"Winner: {self.winner}\n"
            f"Weight Class: {self.weight_class}\n"
            f"Gender: {self.gender}\n"
            f"Title Fight: {self.title_fight}\n"
            f"Method of Victory: {self.method_of_victory}\n"
            f"Round of Victory: {self.round_of_victory}\n"
            f"Time of Victory (sec): {self.time_of_victory_sec}\n"
            f"Time Format: {self.time_format}\n"
            f"Referee: {self.referee}"
        )
