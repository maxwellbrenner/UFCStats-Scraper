import concurrent.futures
import csv
import mysql.connector
from mysql.connector import Error
import random
import re
import requests
import time
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import date, datetime
from threading import Lock
from typing import Dict, List, Optional, Tuple
from urllib3.exceptions import NameResolutionError
import os

# -----------------------------------------------------------------------
#  WEB FETCHING UTILITIES
# -----------------------------------------------------------------------

"""
This module provides functions to retrieve and parse HTML content from web pages, specifically for scraping UFC statistics from ufcstats.com. 
It includes thread-safe caching for Fighter objects, a global HTTP session for connection reuse, and parallel fetching capabilities using a thread pool.

Key components:
- FIGHTER_CACHE: A thread-safe dictionary for caching Fighter objects by URL.
- CACHE_LOCK: A Lock object to synchronize access to FIGHTER_CACHE.
- SESSION: A global requests.Session for reusing HTTP connections.
- HEADERS: HTTP headers with a user-agent to mimic a browser.
- `get_page_content()`: Fetches and parses a single URL with retry logic and exponential backoff.
- `fetch_parallel()`: Fetches multiple URLs concurrently using ThreadPoolExecutor.

All functions are designed to handle errors gracefully and log issues for debugging.
"""

# Cache for storing Fighter objects to avoid redundant HTTP requests
# Key: Fighter URL, Value: Fighter object
FIGHTER_CACHE: Dict[str, "Fighter"] = {}

# Thread-safe lock to synchronize access to FIGHTER_CACHE
CACHE_LOCK = Lock()

# Global session for reusing connections
SESSION = requests.Session()

# Define headers for the HTTP request
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/85.0.4183.121 Safari/537.36'
    )
}

def get_page_content(url: str) -> Optional[BeautifulSoup]:
    """
    Retrieves and parses HTML content from a specified URL with (exp. backoff) retry logic.

    Parameters:
        url (str): The URL to fetch and parse.

    Returns:
        Optional[BeautifulSoup]: A BeautifulSoup object containing the parsed HTML
        if the request is successful, otherwise None.

    Functionality:
        - Sends an HTTP GET request to the provided URL using a global session.
        - Implements exponential backoff with up to 5 retries on failure.
        - Introduces a random delay (0.1-0.5 seconds) on success to avoid overwhelming the server.
        - Uses the 'lxml' parser for faster HTML parsing.
    """
    max_retries = 5
    base_delay = 1
    
    for attempt in range(1, max_retries + 1):
        # Log retry attempts after the first
        if attempt > 1:
            print(f"[DEBUG] Attempt {attempt}/{max_retries} for URL: {url}")
        try:
            response = SESSION.get(url, headers=HEADERS, timeout=30)
            if attempt > 1:
                print(f"[DEBUG] Status code: {response.status_code} for {url}")
            if response.status_code == 200:
                if attempt > 1:
                    print(f"[DEBUG] Successfully fetched {url}")
                # Random delay to prevent server overload
                time.sleep(random.uniform(0.1, 0.5))  # Reduced delay for speed
                # Parse HTML content with lxml parser
                return BeautifulSoup(response.content, 'lxml')
            else:
                print(f"[ERROR] Failed to retrieve page: status {response.status_code} for {url}")
        except requests.RequestException as e:
            print(f"[ERROR] Request failed on attempt {attempt}: {type(e).__name__} - {e} for {url}")
        except NameResolutionError as dns_e:
            # Handle DNS resolution failures with a longer delay
            print(f"[ERROR] DNS resolution failed on attempt {attempt}: {dns_e} for {url}")
            time.sleep(10)
        except Exception as e:
            print(f"[ERROR] Unexpected error on attempt {attempt}: {type(e).__name__} - {e} for {url}")
        
        # Calculate exponential backoff delay
        delay = base_delay * (2 ** (attempt - 1))
        if attempt < max_retries:
            print(f"[DEBUG] Retrying after {delay} seconds...")
        time.sleep(delay)
        
    # Log failure after max retries
    print(f"[ERROR] Max retries exceeded for {url}")
    return None

def fetch_parallel(urls: List[str], max_workers: int = 10) -> Dict[str, Optional[BeautifulSoup]]:
    """
    Fetches multiple URLs in parallel using a thread pool.

    Parameters:
        urls (List[str]): A list of URLs to fetch.
        max_workers (int): Maximum number of threads to use. Defaults to 10.

    Returns:
        Dict[str, Optional[BeautifulSoup]]: A dictionary mapping each URL to its
        parsed BeautifulSoup object, or None if the fetch failed.

    Functionality:
        - Utilizes ThreadPoolExecutor to fetch multiple URLs concurrently.
        - Calls get_page_content() for each URL to retrieve and parse HTML.
        - Limits the number of concurrent threads to prevent overwhelming the server.
        - Returns a dictionary with results for all URLs, even if some fail.
    """
    # Initialize result dictionary to store URL to BeautifulSoup mappings
    results = {}
    # Create thread pool with specified max workers  
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map futures to URLs for tracking
        future_to_url = {executor.submit(get_page_content, url): url for url in urls}
        # Process completed futures as they finish
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:
                # Log failure but continue processing other URLs
                print(f"[ERROR] Parallel fetch failed for {url}: {e}")
                results[url] = None
    return results


# -----------------------------------------------------------------------
#  EVENT
# -----------------------------------------------------------------------

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
        
# -----------------------------------------------------------------------
#  EVENTS
# -----------------------------------------------------------------------

"""
This module defines the `Events` class, which orchestrates the scraping of UFC events from ufcstats.com and manages data output to CSV and MySQL. 
It provides functionality to parse event data, create `Event` objects, and store the collected data.

Key components:
- `Events`: A class to manage the collection and storage of UFC event data.
- `create_event()`: Creates an Event object from a table row of event data.
- `create_events()`: Populates the events list with Event objects for events after a specified date.
- `parse_event_link()`, `parse_event_name()`, `parse_event_date()`, `parse_event_location()`: Helper methods for parsing event attributes.
- `to_csv()`: Writes event, fight, fighter, and round statistics to a CSV file.
- `to_sql()`: Inserts scraped data into a MySQL database.

The class integrates with the `fetch`, `database`, and `Event` modules for data retrieval and storage.
"""

class Events:
    # -----------------------------------------------------------------------
    # constructor
    # -----------------------------------------------------------------------
    def __init__(self, events_page_url: str = "http://ufcstats.com/statistics/events/completed?page=all"):
        self.events_page_url = events_page_url
        self.events: List[Event] = []
        
    # -----------------------------------------------------------------------
    # main driver
    # -----------------------------------------------------------------------    
    def create_event(self, row) -> Event:
        """
        Creates an Event object from a table row of event data.

        Parameters:
            row: A BeautifulSoup object representing a table row (<tr>) containing event data.

        Returns:
            Event: An Event object with parsed attributes (link, name, date, location).

        Functionality:
            - Extracts event details (link, name, date, location) from the provided table row.
            - Returns a new Event object with the parsed data.
        """
        # Extract event attributes using helper methods
        link = self.parse_event_link(row)
        name = self.parse_event_name(row)
        date = self.parse_event_date(row)
        location = self.parse_event_location(row)
        return Event(link=link, name=name, date=date, location=location)

    def create_events(self, start_date: Optional[date] = None) -> None:
        """
        Populates the events list with Event objects for events newer than the specified date.

        Parameters:
            start_date (Optional[date]): Only include events after this date. If None, all events are included.

        Returns:
            None

        Functionality:
            - Fetches the events page HTML using get_page_content().
            - Locates the events table and processes rows after the 'first' marker row, which represents the upcoming (future) event.
            - Stops processing if an event's date is older than or equal to start_date.
            - Creates and appends Event objects to self.events for each valid row.
        """
        # Fetch events page HTML
        events_page_soup = get_page_content(self.events_page_url)
        if not events_page_soup:
            print("Could not load page content.")
            return

        # Locate the events table
        events_table = events_page_soup.find('table', class_='b-statistics__table-events')
        if not events_table:
            print("Events table not found on page.")
            return
        # Find the table body     
        tbody = events_table.find('tbody')
        if not tbody:
            print("Table body is missing.")
            return

        # Skip the 'first' row, which represents the upcoming (future) event that has not yet occurred
        future_event = tbody.find('tr', class_='b-statistics__table-row_type_first')
        if not future_event:
            print("First marker row not found; no events to parse.")
            return
        
        # Process completed event rows after the future event
        for event_row in future_event.find_next_siblings('tr', class_='b-statistics__table-row'):
            event_date = self.parse_event_date(event_row)
            # Stop processing if event is older than or equal to the start_date
            if start_date and event_date and event_date <= start_date:
                break
            event = self.create_event(event_row)
            self.events.append(event)

    # -----------------------------------------------------------------------
    # individual helpers
    # -----------------------------------------------------------------------   
    @staticmethod
    def parse_event_link(row) -> Optional[str]:
        """
        Extracts the event link from a table row.
        """
        try:
            return row.a['href'].strip()
        except (AttributeError, KeyError, TypeError):
            return None

    @staticmethod
    def parse_event_name(row) -> Optional[str]:
        """
        Extracts the event name from a table row.
        """
        try:
            return row.a.get_text(strip=True)
        except AttributeError:
            return None

    @staticmethod
    def parse_event_date(row) -> Optional[datetime.date]:
        """
        Extracts and parses the event date from a table row.
        """
        try:
            date_str = row.find('span').text.strip()
            return datetime.strptime(date_str, '%B %d, %Y').date()
        except (AttributeError, ValueError):
            return None

    @staticmethod
    def parse_event_location(row) -> Optional[str]:
        """
        Extracts the event location from a table row.
        """
        try:
            return row.find_all('td')[1].get_text(strip=True)
        except (IndexError, AttributeError):
            return None
  
    def to_csv(self, filename: str) -> None:
        """
        Writes UFC event, fight, fighter, and round statistics data to a CSV file.

        Parameters:
            filename (str): The name of the CSV file to write to.

        Returns:
            None

        Functionality:
            - Creates a CSV file where each row represents a fight, including associated event details,
              fighter information, fight outcomes, and per-round statistics for up to 5 rounds.
            - Missing rounds are filled with None values.
        """
        # Define round statistics fields
        round_stat_fields = [
        "knockdowns", "non_sig_strikes_landed", "non_sig_strikes_attempted",
        "takedowns_landed", "takedowns_attempted", "submission_attempts", "reversals",
        "control_time_seconds", "head_strikes_landed", "head_strikes_attempted",
        "body_strikes_landed", "body_strikes_attempted", "leg_strikes_landed",
        "leg_strikes_attempted", "distance_strikes_landed", "distance_strikes_attempted",
        "clinch_strikes_landed", "clinch_strikes_attempted", "ground_strikes_landed",
        "ground_strikes_attempted"
        ]

        # Initialize list to store rows for CSV
        rows = []
        
        # Iterate through each fight within each event
        for event in self.events:
            for fight in event.fights:
                # Create base row with event and fight details
                base_row = {
                    "event_name": event.name,
                    "event_date": event.date,
                    "event_location": event.location,
                    "event_link": event.link,

                    "fighter_a_name": fight.fighter_a.name if fight.fighter_a else None,
                    "fighter_a_link": fight.fighter_a.link if fight.fighter_a else None,
                    "fighter_a_height_in": fight.fighter_a.height_in if fight.fighter_a else None,
                    "fighter_a_reach_in": fight.fighter_a.reach_in if fight.fighter_a else None,
                    "fighter_a_dob": fight.fighter_a.dob if fight.fighter_a else None,
    
                    "fighter_b_name": fight.fighter_b.name if fight.fighter_b else None,
                    "fighter_b_link": fight.fighter_b.link if fight.fighter_b else None,
                    "fighter_b_height_in": fight.fighter_b.height_in if fight.fighter_b else None,
                    "fighter_b_reach_in": fight.fighter_b.reach_in if fight.fighter_b else None,
                    "fighter_b_dob": fight.fighter_b.dob if fight.fighter_b else None,
                    
                    "fight_link": fight.link,
                    "winner": fight.winner,
                    "weight_class": fight.weight_class,
                    "gender": fight.gender,
                    "title_fight": fight.title_fight,
                    "method_of_victory": fight.method_of_victory,
                    "round_of_victory": fight.round_of_victory,
                    "time_of_victory_sec": fight.time_of_victory_sec,
                    "time_format": fight.time_format,
                    "referee": fight.referee,
                }
    
                # Add round stats for up to 5 rounds
                for rnd in range(5):
                    prefix_a = f"round_{rnd+1}_fighter_a_"
                    prefix_b = f"round_{rnd+1}_fighter_b_"
                    stats_a = fight.rounds[rnd].fighter_a_roundstats if rnd < len(fight.rounds) else None
                    stats_b = fight.rounds[rnd].fighter_b_roundstats if rnd < len(fight.rounds) else None
    
                    # Add stats for fighter_a and fighter_b using dictionary comprehension
                    for prefix, stats in [(prefix_a, stats_a), (prefix_b, stats_b)]:
                        base_row.update({
                            f"{prefix}{field}": getattr(stats, field, None) for field in round_stat_fields
                        })
    
                rows.append(base_row)

        # Check if there is data to write
        if not rows:
            print("No data to write.")
            return

        # Write data to CSV file
        with open(filename, mode='w', newline='', encoding='utf-8', errors='replace') as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    
        print(f"CSV written to {filename}")

    def to_sql(self, user: str, password: str, host: str = 'localhost', database: str = 'UFCStats', auth_plugin: str = 'mysql_native_password') -> None:
        """
        Inserts scraped UFC event data, including events, fights, fighters, referees, rounds, and round statistics, into a MySQL database.

        Parameters:
            user (str): The MySQL database username.
            password (str): The password for the database user.
            host (str): The database host address. Defaults to 'localhost'.
            database (str): The name of the database to connect to. Defaults to 'UFCStats'.
            auth_plugin (str): The MySQL authentication plugin to use. Defaults to 'mysql_native_password'.

        Returns:
            None

        Functionality:
            - Establishes a connection to the MySQL database using provided credentials.
            - Iterates through all events in self.events and inserts:
                1. Event details (name, date, location) into the 'event' table.
                2. Fighter details (name, height, reach, DOB) into the 'fighter' table, using upsert to avoid duplicates.
                3. Referee details (name) into the 'referee' table, using upsert to avoid duplicates.
                4. Fight details (event ID, fighter IDs, winner, weight class, etc.) into the 'fight' table.
                5. Round details (fight ID, round number) and per-fighter round statistics (knockdowns, strikes, etc.) into the 'round' and 'roundstats' tables.
            - Commits all changes to the database and closes the connection.

        Raises:
            mysql.connector.Error: If a database operation fails.
        """
        # Establish database connection
        conn = connect_to_mysql(host=host, user=user, password=password, database=database, auth_plugin=auth_plugin)
        cursor = conn.cursor()
    
        for event in self.events:
            # 1) Insert event into the 'event' table
            print(f"Inserting event: {event.name}")
            cursor.execute(
                "INSERT INTO event (name, date, location) VALUES (%s, %s, %s)",
                (event.name, event.date, event.location)
            )
            event_id = cursor.lastrowid
    
            for fight in event.fights:
                # 2) Upsert fighters A and B into the 'fighter' table
                fighter_ids = {}
                for side, fighter in (('a', fight.fighter_a), ('b', fight.fighter_b)):
                    if fighter:
                        # Check if fighter exists
                        cursor.execute(
                            "SELECT fighter_id FROM fighter WHERE name = %s",
                            (fighter.name,)
                        )
                        row = cursor.fetchone()
                        if row:
                            fighter_ids[side] = row[0]
                        else:
                            # Insert new fighter
                            cursor.execute(
                                "INSERT INTO fighter (name, height_in, reach_in, dob) "
                                "VALUES (%s, %s, %s, %s)",
                                (fighter.name, fighter.height_in, fighter.reach_in, fighter.dob)
                            )
                            fighter_ids[side] = cursor.lastrowid
    
                # 3) Upsert referee into the 'referee' table (if present)
                referee_id = None
                if fight.referee:
                    cursor.execute(
                        "SELECT referee_id FROM referee WHERE name = %s",
                        (fight.referee,)
                    )
                    row = cursor.fetchone()
                    if row:
                        referee_id = row[0]
                    else:
                        # Insert new referee
                        cursor.execute(
                            "INSERT INTO referee (name) VALUES (%s)",
                            (fight.referee,)
                        )
                        referee_id = cursor.lastrowid
    
                # 4) Insert fight into the 'fight' table
                cursor.execute(
                    "INSERT INTO fight (event_id, fighter_a_id, fighter_b_id, winner, "
                    "weight_class, gender, title_fight, method_of_victory, "
                    "round_of_victory, time_of_victory, time_format, referee_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        event_id,
                        fighter_ids.get('a'),
                        fighter_ids.get('b'),
                        fight.winner,
                        fight.weight_class,
                        fight.gender,
                        int(fight.title_fight),
                        fight.method_of_victory,
                        fight.round_of_victory,
                        fight.time_of_victory_sec,
                        fight.time_format,
                        referee_id
                    )
                )
                fight_id = cursor.lastrowid
    
                # 5) Insert rounds and round statistics into 'round' and 'roundstats' tables
                for rnd in fight.rounds:
                    # Insert round
                    cursor.execute(
                        "INSERT INTO round (fight_id, round_number) VALUES (%s, %s)",
                        (fight_id, rnd.round_number)
                    )
                    round_id = cursor.lastrowid

                    # Insert round statistics for each fighter
                    for rs in (rnd.fighter_a_roundstats, rnd.fighter_b_roundstats):
                        fid = fighter_ids['a'] if rs is rnd.fighter_a_roundstats else fighter_ids['b']
                        cursor.execute(
                            "INSERT INTO roundstats (round_id, fighter_id, "
                            "knockdowns, non_sig_strikes_landed, non_sig_strikes_attempted, "
                            "takedowns_landed, takedowns_attempted, submission_attempts, "
                            "reversals, control_time_seconds, head_strikes_landed, "
                            "head_strikes_attempted, body_strikes_landed, body_strikes_attempted, "
                            "leg_strikes_landed, leg_strikes_attempted, distance_strikes_landed, "
                            "distance_strikes_attempted, clinch_strikes_landed, clinch_strikes_attempted, "
                            "ground_strikes_landed, ground_strikes_attempted) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                round_id, fid,
                                rs.knockdowns,
                                rs.non_sig_strikes_landed, rs.non_sig_strikes_attempted,
                                rs.takedowns_landed, rs.takedowns_attempted,
                                rs.submission_attempts, rs.reversals,
                                rs.control_time_seconds,
                                rs.head_strikes_landed, rs.head_strikes_attempted,
                                rs.body_strikes_landed, rs.body_strikes_attempted,
                                rs.leg_strikes_landed, rs.leg_strikes_attempted,
                                rs.distance_strikes_landed, rs.distance_strikes_attempted,
                                rs.clinch_strikes_landed, rs.clinch_strikes_attempted,
                                rs.ground_strikes_landed, rs.ground_strikes_attempted
                            )
                        )
    
        # Commit all changes to the database
        conn.commit()
        print("Data committed to database successfully.")
        # Close cursor and connection
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------
#  FIGHTER
# -----------------------------------------------------------------------

"""
This module defines the `Fighter` class, which represents a UFC fighter and their attributes (name, height, reach, and date of birth). 
It provides functionality to parse fighter details from a fighter's page and cache the results for efficiency.

Key components:
- `Fighter`: A dataclass representing a UFC fighter with attributes for link, name, height, reach, and DOB.
- `create_fighter()`: Populates the Fighter object by parsing fighter page HTML.
- `parse_fighter_name()`, `parse_height()`, `parse_reach()`, `parse_dob()`: Helper methods for parsing specific attributes.
- `to_string()`: Formats fighter details into a string for display.

The class integrates with the `fetch` module for HTML retrieval and uses thread-safe caching to avoid redundant requests.
"""

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

    def __init__(self, link: str, soup: Optional[BeautifulSoup] = None) -> None:
        self.link = link
        with CACHE_LOCK:
            if self.link in FIGHTER_CACHE:
                cached = FIGHTER_CACHE[self.link]
                self.name = cached.name
                self.height_in = cached.height_in
                self.reach_in = cached.reach_in
                self.dob = cached.dob
                return
        self.create_fighter(soup)  # Pass soup to create_fighter
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


# -----------------------------------------------------------------------
#  ROUNDSTATS
# -----------------------------------------------------------------------

"""
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
        

# -----------------------------------------------------------------------
#  ROUND
# -----------------------------------------------------------------------

"""
This module defines the `Round` class, which represents a single round in a UFC fight, including per-fighter statistics. 
It provides functionality to parse round-specific data from fight page HTML and assign `RoundStats` objects for each fighter.

Key components:
- `Round`: A dataclass representing a UFC fight round with attributes for round number and fighter statistics.
- `create_round()`: Populates the Round object by parsing fight page HTML and creating RoundStats objects for both fighters.

The class integrates with the `RoundStats` model for statistics parsing and relies on fighter links to map statistics correctly.
"""

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


# --------------------------------------------------------
#  FIGHT
# --------------------------------------------------------

"""
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
    weight_class: Optional[int] = field(init=False)
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


# -----------------------------------------------------------------------
# DATABASE UTILITIES
# -----------------------------------------------------------------------

"""
This module provides functions to interact with the MySQL database used for storing UFC event data. 
It includes utilities for establishing a database connection and retrieving the latest event date.

Key components:
- `connect_to_mysql()`: Establishes a connection to the MySQL database using specified credentials.
- `get_latest_event_date()`: Retrieves the most recent event date from the database.

The module integrates with the MySQL database to support data storage for the scraper.
"""

def connect_to_mysql(
    host: str = 'localhost',
    user: str = None,
    password: str = None,
    database: str = 'UFCStats',
    auth_plugin: str = 'mysql_native_password'
) -> mysql.connector.connection.MySQLConnection:
    """
    Connect to a MySQL database, creating it and its schema if it does not exist.

    Args:
        host (str): The database host. Defaults to 'localhost'.
        user (str): The database user. Must be provided.
        password (str): The user's password. Must be provided.
        database (str): The database name. Defaults to 'UFCStats'.
        auth_plugin (str): The authentication plugin to use. Defaults to 'mysql_native_password'.

    Returns:
        mysql.connector.connection.MySQLConnection: A MySQL connection object to the specified database.

    Raises:
        mysql.connector.Error: If the connection or database creation fails.
        FileNotFoundError: If the create_database.sql file is not found.
        ValueError: If required parameters (user, password) are missing.
    """
    # Validate required parameters
    if not user or not password:
        raise ValueError("Database user and password must be provided.")

    try:
        # Connect to MySQL server without specifying a database to check existence
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            auth_plugin=auth_plugin
        )
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute("SHOW DATABASES LIKE %s", (database,))
        db_exists = cursor.fetchone() is not None

        if not db_exists:
            print(f"Database {database} does not exist. Creating database and schema...")
            # Read the SQL script from the external file
            try:
                with open('create_database.sql', 'r', encoding='utf-8') as f:
                    sql_script = f.read()
            except FileNotFoundError:
                print("Error: create_database.sql file not found in the current directory.")
                raise
            except Exception as e:
                print(f"Error reading create_database.sql: {e}")
                raise

            # Execute each statement in the SQL script
            for statement in sql_script.split(';'):
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                    except mysql.connector.Error as e:
                        print(f"Error executing SQL statement: {e}")
                        raise
            conn.commit()
            print(f"Database {database} and schema created successfully.")

        cursor.close()
        conn.close()

        # Connect to the specified database
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            auth_plugin=auth_plugin
        )

    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during database setup: {e}")
        raise

def get_latest_event_date(conn) -> Optional[date]:
    """
    Retrieve the date of the most recent event from the event table.

    Returns:
        Optional[date]: The latest event date, or None if no events exist.

    Raises:
        mysql.connector.Error: If the database query fails.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM event")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row and row[0] else None


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------

"""
This module defines the `main()` function, which orchestrates the scraping of UFC event data from ufcstats.com, processes fight details, 
and stores the results in a MySQL database and CSV file. It integrates with the `Events` class and database utilities to manage the scraping workflow.

Key components:
- `main()`: The primary function that initializes the scraper, fetches new events, processes fight details, and handles data storage.
- Integrates with `Events` class for event scraping and `database` module for MySQL connectivity.
- Handles errors gracefully and ensures data is saved to CSV even on failure.

The script is designed to be executed as the entry point for the UFC Stats Scraper application.
"""

def main():
    """
    Runs the UFCStats scraper, fetching new events, processing fight details, and storing results in a MySQL database and CSV file.

    Functionality:
        - Prompts the user for database credentials (host, user, password, database name, auth plugin).
        - Initializes an Events manager and retrieves the latest event date from the database.
        - Scrapes new UFC events after the latest date, including fight and round statistics.
        - Stores scraped data in a MySQL database and exports it to a CSV file ('UFCStats.csv').
        - Handles database and general errors gracefully, ensuring data is saved to CSV even on failure.

    Raises:
        ValueError: If required database credentials are missing or invalid.
        mysql.connector.Error: If a database operation fails.
        Exception: For other unexpected errors during execution.

    Returns:
        None
    """
    # Initialize events_manager outside try block to avoid UnboundLocalError
    events_manager = Events()

    try:
        # Prompt user for database credentials
        print("Enter MySQL database connection details:")
        db_config = {
            'host': input("Host (default: localhost): ") or 'localhost',
            'user': input("Username: "),
            'password': input("Password: "),
            'database': input("Database name (default: UFCStats): ") or 'UFCStats',
            'auth_plugin': input("Authentication plugin (default: mysql_native_password): ") or 'mysql_native_password'
        }

        # Validate required credentials
        required_vars = ['user', 'password']
        missing_vars = [key for key in required_vars if not db_config[key]]
        if missing_vars:
            raise ValueError(f"Missing required database credentials: {', '.join(missing_vars)}")

        # Connect to MySQL and get latest event date
        conn = connect_to_mysql(**db_config)
        latest_date = get_latest_event_date(conn)
        
        # Populate events
        events_manager.create_events(start_date=latest_date)

        if not events_manager.events:
            print("No new events found.")
            return

        print(f"[DEBUG] Found {len(events_manager.events)} events to process")
        # Process all events
        for i, event in enumerate(events_manager.events, 1):
            print(f"\n\n=== EVENT {i} ===")
            # Measure scrape time for create_fights
            start_time = time.time()
            try:
                event.create_fights()
            except KeyboardInterrupt:
                print(f"\n[INFO] Keyboard interrupt received during event {i} ({event.name}). Saving scraped data...")
                # Save to database
                events_manager.to_sql(**db_config)
                # Save to CSV
                events_manager.to_csv("UFCStats.csv")
                print("[INFO] Data saved successfully. Exiting.")
                return  # Exit after saving
            scrape_time = time.time() - start_time
            # Pass scrape_time to to_string
            print(event.to_string(scrape_time=scrape_time))

        # Insert all events into MySQL
        events_manager.to_sql(**db_config)

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt received. Saving scraped data...")
        # Save to database
        events_manager.to_sql(**db_config)
        # Save to CSV
        events_manager.to_csv("UFCStats.csv")
        print("[INFO] Data saved successfully. Exiting.")
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Execution interrupted: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
