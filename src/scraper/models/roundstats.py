#src/scraper/models/roundstats.py

"""RoundStats model for the UFC Stats Scraper.

This module defines the `RoundStats` class, which represents per-fighter statistics for a single round in a UFC fight. 
It provides functionality to parse performance metrics from fight page HTML table rows.

Key components:
- `RoundStats`: A dataclass representing per-fighter round statistics.
- `create_roundstats()`: Populates the RoundStats object by parsing totals and significant strikes table rows.
- `parse_total_stats()`, `parse_sig_strikes_stats()`: Extract specific performance metrics from HTML.
- `split_x_of_y()`, `parse_control_time_to_seconds()`, `to_int()`, `get_text()`: Helper methods for parsing data.
- `to_string()`: Formats round statistics into a string for display.

The class processes HTML table rows to extract detailed fight statistics for integration with the `Round` model.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
from bs4 import BeautifulSoup
import re

@dataclass(init=False)
class RoundStats:
    """
    Attributes
    ----------
    totals_tr                   : BeautifulSoup object representing the totals table row
    sig_strikes_tr              : BeautifulSoup object representing the significant strikes table row
    position                    : Fighter position in the table (0 or 1)
    
    fighter_link                : URL of the fighter's details page
    knockdowns                  : Number of knockdowns scored
    non_sig_strikes_landed      : Number of non-significant strikes landed
    non_sig_strikes_attempted   : Number of non-significant strikes attempted
    takedowns_landed            : Number of takedowns successfully landed
    takedowns_attempted         : Number of takedowns attempted
    submission_attempts         : Number of submission attempts
    reversals                   : Number of reversals performed
    control_time_seconds        : Control time in seconds
    
    head_strikes_landed         : Number of significant head strikes landed
    head_strikes_attempted      : Number of significant head strikes attempted
    body_strikes_landed         : Number of significant body strikes landed
    body_strikes_attempted      : Number of significant body strikes attempted
    leg_strikes_landed          : Number of significant leg strikes landed
    leg_strikes_attempted       : Number of significant leg strikes attempted
    distance_strikes_landed     : Number of significant strikes landed at distance
    distance_strikes_attempted  : Number of significant strikes attempted at distance
    clinch_strikes_landed       : Number of significant strikes landed in clinch
    clinch_strikes_attempted    : Number of significant strikes attempted in clinch
    ground_strikes_landed       : Number of significant strikes landed on ground
    ground_strikes_attempted    : Number of significant strikes attempted on ground
    """
    totals_tr: Optional[BeautifulSoup]
    sig_strikes_tr: Optional[BeautifulSoup]
    position: Optional[int]   # 0 or 1

    fighter_link: Optional[str] = field(default=None)
    knockdowns: Optional[int] = field(default=None)
    non_sig_strikes_landed: Optional[int] = field(default=None)
    non_sig_strikes_attempted: Optional[int] = field(default=None)
    takedowns_landed: Optional[int] = field(default=None)
    takedowns_attempted: Optional[int] = field(default=None)
    submission_attempts: Optional[int] = field(default=None)
    reversals: Optional[int] = field(default=None)
    control_time_seconds: Optional[int] = field(default=None)

    head_strikes_landed: Optional[int] = field(default=None)
    head_strikes_attempted: Optional[int] = field(default=None)
    body_strikes_landed: Optional[int] = field(default=None)
    body_strikes_attempted: Optional[int] = field(default=None)
    leg_strikes_landed: Optional[int] = field(default=None)
    leg_strikes_attempted: Optional[int] = field(default=None)
    distance_strikes_landed: Optional[int] = field(default=None)
    distance_strikes_attempted: Optional[int] = field(default=None)
    clinch_strikes_landed: Optional[int] = field(default=None)
    clinch_strikes_attempted: Optional[int] = field(default=None)
    ground_strikes_landed: Optional[int] = field(default=None)
    ground_strikes_attempted: Optional[int] = field(default=None)

    # -----------------------------------------------------------------------
    # constructor
    # -----------------------------------------------------------------------
    def __init__(self, totals_tr: Optional[BeautifulSoup], sig_strikes_tr: Optional[BeautifulSoup], position: Optional[int]) -> None:
        self.totals_tr = totals_tr
        self.sig_strikes_tr = sig_strikes_tr
        self.position = position
        self.create_roundstats()

    # -----------------------------------------------------------------------
    # main driver
    # -----------------------------------------------------------------------
    def create_roundstats(self) -> None:
        """
        Populates the RoundStats object by parsing statistics from the provided totals and significant strikes table rows.
    
        Returns:
            None
    
        Functionality:
            - Checks if the totals table row (`totals_tr`) is provided and calls `parse_total_stats()` to extract statistics.
            - Checks if the significant strikes table row (`sig_strikes_tr`) is provided and calls `parse_sig_strikes_stats()` to extract statistics.
            - Does not modify attributes if the corresponding table row is None, leaving them as their default None values.
        """
        if self.totals_tr:
            self.parse_total_stats(self.totals_tr)
        if self.sig_strikes_tr:
            self.parse_sig_strikes_stats(self.sig_strikes_tr)

    def parse_total_stats(self, totals_tr: BeautifulSoup):
        """
        Parses significant strike statistics from a significant strikes table row and updates the RoundStats attributes.
    
        Parameters:
            sig_strikes_tr (BeautifulSoup): A BeautifulSoup object representing the significant strikes table row (<tr>).
    
        Returns:
            None
    
        Functionality:
            - Extracts data from the provided table row for fighter performance metrics.
            - Populates attributes for knockdowns, non-significant strikes, takedowns, submission attempts, reversals, and control time.
        """
        rows = totals_tr.find_all('td')

        # 1. Fighter link
        fighter_link = rows[0]
        p = fighter_link.find_all('p')[self.position]
        a = p.find('a')
        self.fighter_link = a['href'].strip() if a and a.has_attr('href') else None

        # 2. Knockdowns
        self.knockdowns = self.to_int(self.get_text(rows[1]))

        # 2. Non-significant strikes (Derived)
        sig_landed, sig_attempted = self.split_x_of_y(self.get_text(rows[2]))
        total_landed, total_attempted = self.split_x_of_y(self.get_text(rows[4]))

        if sig_landed >= 0 and total_landed >= 0:
            self.non_sig_strikes_landed = total_landed - sig_landed
            self.non_sig_strikes_attempted = total_attempted - sig_attempted

        # 3. Takedowns
        self.takedowns_landed, self.takedowns_attempted = self.split_x_of_y(self.get_text(rows[5]))

        # 4. Submission attempts
        self.submission_attempts = self.to_int(self.get_text(rows[7]))

        # 5. Reversals
        self.reversals = self.to_int(self.get_text(rows[8]))

        # 6. Control time
        self.control_time_seconds = self.parse_control_time_to_seconds(self.get_text(rows[9]))

    def parse_sig_strikes_stats(self, sig_strikes_tr: BeautifulSoup):
        """
        Parses significant strike statistics from a significant strikes table row and updates the RoundStats attributes.
    
        Parameters:
            sig_strikes_tr (BeautifulSoup): A BeautifulSoup object representing the significant strikes table row (<tr>).
    
        Returns:
            None
    
        Functionality:
            - Extracts data from the provided table row for significant strikes by target and position.
            - Populates attributes for head, body, leg, distance, clinch, and ground strikes (landed and attempted).
        """
        rows = sig_strikes_tr.find_all('td')

        # 1. Head strikes
        self.head_strikes_landed, self.head_strikes_attempted = self.split_x_of_y(self.get_text(rows[3]))

        # 2. Body strikes        
        self.body_strikes_landed, self.body_strikes_attempted = self.split_x_of_y(self.get_text(rows[4]))

        # 3. Leg strikes
        self.leg_strikes_landed, self.leg_strikes_attempted = self.split_x_of_y(self.get_text(rows[5]))
        
        # 4. Distance strikes
        self.distance_strikes_landed, self.distance_strikes_attempted = self.split_x_of_y(self.get_text(rows[6]))
        
        # 5. Clinch strikes
        self.clinch_strikes_landed, self.clinch_strikes_attempted = self.split_x_of_y(self.get_text(rows[7]))
        
        # 6. Ground strikes
        self.ground_strikes_landed, self.ground_strikes_attempted = self.split_x_of_y(self.get_text(rows[8]))

    # -----------------------------------------------------------------------
    # individual helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def split_x_of_y(stat_string: str) -> Tuple[int, int]:
        """
        Parses a string in the format 'X of Y' into a tuple of integers (X, Y). 
        
        Returns (-1, -1) if parsing fails.
        """
        match = re.match(r'(\d+)\s*of\s*(\d+)', stat_string)
        if match:
            return int(match.group(1)), int(match.group(2))
        return -1, -1

    @staticmethod
    def parse_control_time_to_seconds(time_str: str) -> Optional[int]:
        """
        Converts a time string in 'MM:SS' format to total seconds.
        """
        match = re.match(r"(\d+):(\d+)", time_str)
        if match:
            minutes, seconds = map(int, match.groups())
            return minutes * 60 + seconds
        return None

    @staticmethod
    def to_int(text: str) -> Optional[int]:
        """
        Converts a text string to an integer if it represents a valid digit.
        """
        return int(text) if text.isdigit() else None

    def get_text(self, td: BeautifulSoup) -> str:
        """
        Extracts text from a specific <p> element within a table cell based on the fighter's position.
        """
        try:
            return td.find_all('p')[self.position].get_text(strip=True)
        except (IndexError, AttributeError):
            return ""

    def to_string(self) -> str:
        return (
            f"Fighter Link: {self.fighter_link}\n"
            f"Knockdowns: {self.knockdowns}\n"
            f"Non-Sig Strikes Landed: {self.non_sig_strikes_landed}\n"
            f"Non-Sig Strikes Attempted: {self.non_sig_strikes_attempted}\n"
            f"Takedowns Landed: {self.takedowns_landed}\n"
            f"Takedowns Attempted: {self.takedowns_attempted}\n"
            f"Submission Attempts: {self.submission_attempts}\n"
            f"Reversals: {self.reversals}\n"
            f"Control Time (sec): {self.control_time_seconds}\n"
            f"Head Strikes Landed: {self.head_strikes_landed}\n"
            f"Head Strikes Attempted: {self.head_strikes_attempted}\n"
            f"Body Strikes Landed: {self.body_strikes_landed}\n"
            f"Body Strikes Attempted: {self.body_strikes_attempted}\n"
            f"Leg Strikes Landed: {self.leg_strikes_landed}\n"
            f"Leg Strikes Attempted: {self.leg_strikes_attempted}\n"
            f"Distance Strikes Landed: {self.distance_strikes_landed}\n"
            f"Distance Strikes Attempted: {self.distance_strikes_attempted}\n"
            f"Clinch Strikes Landed: {self.clinch_strikes_landed}\n"
            f"Clinch Strikes Attempted: {self.clinch_strikes_attempted}\n"
            f"Ground Strikes Landed: {self.ground_strikes_landed}\n"
            f"Ground Strikes Attempted: {self.ground_strikes_attempted}"
        )
