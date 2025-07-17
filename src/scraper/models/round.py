#src/scraper/models/round.py

"""Round model for the UFC Stats Scraper.

This module defines the `Round` class, which represents a single round in a UFC fight, including per-fighter statistics. 
It provides functionality to parse round-specific data from fight page HTML and assign `RoundStats` objects for each fighter.

Key components:
- `Round`: A dataclass representing a UFC fight round with attributes for round number and fighter statistics.
- `create_round()`: Populates the Round object by parsing fight page HTML and creating RoundStats objects for both fighters.

The class integrates with the `RoundStats` model for statistics parsing and relies on fighter links to map statistics correctly.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from .roundstats import RoundStats

@dataclass
class Round:
    """
    Attributes
    ----------
    round_number          : The number of the round (1-5)
    fighter_a_roundstats  : RoundStats object containing statistics for fighter A in this round
    fighter_b_roundstats  : RoundStats object containing statistics for fighter B in this round
    """
    round_number: int
    fighter_a_roundstats: Optional[RoundStats] = field(init=False)
    fighter_b_roundstats: Optional[RoundStats] = field(init=False)

    # -----------------------------------------------------------------------
    # constructor
    # -----------------------------------------------------------------------
    def __init__(self, round_number: int, fight_page_soup: BeautifulSoup, fighter_links: Tuple[str, str]):
        self.round_number = round_number
        self.fight_page_soup = fight_page_soup
        self.fighter_links = fighter_links
        self.create_round()

    # -----------------------------------------------------------------------
    # main driver
    # -----------------------------------------------------------------------
    def create_round(self) -> None:
        """
        Populates the Round object by parsing per-round statistics from the fight page HTML and assigning RoundStats objects for both fighters.
    
        Returns:
            None
    
        Functionality:
            - Locates all <th> elements in the fight page HTML (self.fight_page_soup) with text matching 'Round N', where N is self.round_number.
            - Finds the first two <tr> elements with class 'b-fight-details__table-row' following each matching <th> in document order, representing the 'totals' and 'significant strikes' rows.
            - Creates RoundStats objects for both fighters (positions 0 and 1) using the totals and significant strikes table rows.
            - Maps each RoundStats object to its corresponding fighter link, retrieved from self.fighter_links.
            - Assigns the appropriate RoundStats objects to self.fighter_a_roundstats and self.fighter_b_roundstats based on matching fighter links.
            - Raises a ValueError if the fighter links in the RoundStats objects do not match the expected fighter links, indicating a parsing error.
        """
        target_text = f"Round {self.round_number}"

        headers = self.fight_page_soup.find_all(
            "th",
            string=lambda tag_text: tag_text is not None and tag_text.strip() == target_text
        )

        rows = [header.find_next(lambda tag: tag.name == "tr") for header in headers] + [None, None]
        totals_tr, sig_strikes_tr = rows[:2]

        # Create RoundStats for each table position (0 and 1)
        round_stats = [RoundStats(totals_tr, sig_strikes_tr, pos) for pos in (0, 1)]
        
        # Map from fighter link to corresponding RoundStats
        stats_by_link = {rs.fighter_link: rs for rs in round_stats}
        
        # Unpack fighter links
        link_a, link_b = self.fighter_links
        
        # Ensure both links are present
        if link_a not in stats_by_link or link_b not in stats_by_link:
            raise ValueError(
                f"Could not match Round {self.round_number} stats to fighter links.\n"
                f"Expected: {self.fighter_links}\n"
                f"Found: {list(stats_by_link.keys())}"
            )
        
        # Assign correctly
        self.fighter_a_roundstats = stats_by_link[link_a]
        self.fighter_b_roundstats = stats_by_link[link_b]
