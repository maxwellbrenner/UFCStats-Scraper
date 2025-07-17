#src/scraper/events_manager.py

"""Events manager for the UFC Stats Scraper.

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

import csv
from typing import List, Optional
from datetime import date
from bs4 import BeautifulSoup
from .models.event import Event
from ..fetch import get_page_content
from .database import connect_to_mysql

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
