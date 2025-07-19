# UFC Stats Scraper

The **UFC Stats Scraper** is a Python application designed to scrape detailed UFC event data from [ufcstats.com](http://ufcstats.com/), process it into structured objects, and store it in both a MySQL database and a CSV file. The scraper retrieves comprehensive event, fight, fighter, and round statistics, handling data extraction with thread-safe caching, parallel fetching, and robust error handling. This README provides an overview of the program's functionality, data structures, setup instructions, and usage.

## Table of Contents
- [Overview](#overview)
- [Data Structures](#data-structures)
  - [Events](#events)
  - [Event](#event)
  - [Fight](#fight)
  - [Fighter](#fighter)
  - [Round](#round)
  - [RoundStats](#roundstats)
  - [Relationships Between Data Structures](#relationships-between-data-structures)
- [Setup](#setup)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Dependencies](#dependencies)
- [Database Schema](#database-schema)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)

## Overview
The UFC Stats Scraper fetches data from the completed events page on ufcstats.com, extracts details about events, fights, fighters, and per-round statistics, and organizes them into structured Python objects. It supports:
- **Parallel fetching** of web pages using `ThreadPoolExecutor` for efficiency.
- **Thread-safe caching** of fighter data to avoid redundant HTTP requests.
- **Exponential backoff** for robust handling of network failures.
- **Data storage** in a MySQL database and CSV file, with support for incremental updates based on the latest event date in the database.

The scraper processes events newer than the latest date stored in the database, ensuring no redundant scraping. It handles errors gracefully, saving partial results to CSV and database even if interrupted.

## Data Structures
The program uses a set of interrelated Python dataclasses to represent UFC data hierarchically. Below is a detailed description of each class and their relationships.

### Events
The `Events` class serves as the top-level manager for scraping and storing UFC event data.

- **Purpose**: Orchestrates the scraping of all UFC events from the completed events page (`http://ufcstats.com/statistics/events/completed?page=all`) and manages data output.
- **Attributes**:
  - `events_page_url: str`: URL of the events page (default: the completed events page).
  - `events: List[Event]`: List of `Event` objects representing individual UFC events.
- **Key Methods**:
  - `create_events(start_date: Optional[date])`: Fetches and parses events newer than `start_date`.
  - `to_csv(filename: str)`: Writes event, fight, fighter, and round data to a CSV file.
  - `to_sql(user, password, host, database, auth_plugin)`: Inserts data into a MySQL database.
- **Role**: Acts as the entry point for scraping, coordinating the creation of `Event` objects and their storage.

### Event
The `Event` class represents a single UFC event, such as "UFC 300: Pereira vs. Hill."

- **Purpose**: Stores event metadata and associated fights, parsing fight links from the event page.
- **Attributes**:
  - `link: str`: URL of the event details page (e.g., `http://ufcstats.com/event-details/...`).
  - `name: Optional[str]`: Name of the event (e.g., "UFC 300: Pereira vs. Hill").
  - `date: Optional[datetime.date]`: Date of the event.
  - `location: Optional[str]`: Location of the event (e.g., "Las Vegas, Nevada, USA").
  - `fights: List[Fight]`: List of `Fight` objects associated with the event.
- **Key Methods**:
  - `parse_fight_links()`: Extracts fight detail URLs from the event page.
  - `create_fights()`: Populates the `fights` list by fetching and parsing fight pages in parallel.
  - `to_string(scrape_time: Optional[float])`: Formats event details for display.
- **Role**: Aggregates all fights for a specific event, serving as a container for `Fight` objects.

### Fight
The `Fight` class represents a single UFC fight between two fighters.

- **Purpose**: Stores fight metadata, fighter details, and per-round statistics, parsing data from a fight details page.
- **Attributes**:
  - `link: str`: URL of the fight details page (e.g., `http://ufcstats.com/fight-details/...`).
  - `gender: str`: Gender of the fight ("M" for men, "F" for women).
  - `title_fight: bool`: Indicates if the fight is for a championship title.
  - `fighter_a: Optional[Fighter]`: First fighter in the fight.
  - `fighter_b: Optional[Fighter]`: Second fighter in the fight.
  - `winner: Optional[str]`: Outcome of the fight ("A", "B", "Draw", or "NC" for no contest).
  - `weight_class: Optional[int]`: Weight class in pounds (e.g., 155 for lightweight, 0 for catchweight).
  - `method_of_victory: Optional[str]`: Method of fight conclusion (e.g., "KO", "Submission").
  - `round_of_victory: Optional[int]`: Round in which the fight ended (1-5).
  - `time_of_victory_sec: Optional[int]`: Time of fight conclusion in seconds.
  - `time_format: Optional[int]`: Scheduled number of rounds (3 or 5).
  - `referee: Optional[str]`: Name of the referee.
  - `rounds: List[Round]`: List of `Round` objects for the fight.
- **Key Methods**:
  - `create_fight(fight_page_soup)`: Populates fight attributes by parsing the fight page.
  - `parse_fighters()`: Creates `Fighter` objects for both fighters.
  - `create_rounds()`: Populates the `rounds` list with `Round` objects.
  - `to_string()`: Formats fight details for display.
- **Role**: Links fighters to their performance in a fight, containing round-by-round statistics via `Round` objects.

### Fighter
The `Fighter` class represents an individual UFC fighter.

- **Purpose**: Stores fighter metadata, parsed from their fighter details page, with caching to avoid redundant fetches.
- **Attributes**:
  - `link: str`: URL of the fighter details page (e.g., `http://ufcstats.com/fighter-details/...`).
  - `name: Optional[str]`: Fighter's full name.
  - `height_in: Optional[int]`: Height in inches.
  - `reach_in: Optional[int]`: Reach in inches.
  - `dob: Optional[date]`: Date of birth.
- **Key Methods**:
  - `create_fighter(fighter_page_soup)`: Populates fighter attributes from HTML.
  - `to_string()`: Formats fighter details for display.
- **Role**: Provides personal details for fighters involved in a `Fight`, cached in `FIGHTER_CACHE` for efficiency.

### Round
The `Round` class represents a single round in a UFC fight.

- **Purpose**: Stores per-round statistics for both fighters, linking them to their respective `Fight`.
- **Attributes**:
  - `round_number: int`: The round number (1-5).
  - `fighter_a_roundstats: Optional[RoundStats]`: Statistics for fighter A in this round.
  - `fighter_b_roundstats: Optional[RoundStats]`: Statistics for fighter B in this round.
- **Key Methods**:
  - `create_round()`: Populates round statistics by parsing fight page HTML and assigning `RoundStats` objects.
- **Role**: Organizes per-fighter statistics for a specific round, contained within a `Fight`.

### RoundStats
The `RoundStats` class represents per-fighter statistics for a single round.

- **Purpose**: Stores detailed performance metrics for a fighter in a specific round, parsed from fight page tables.
- **Attributes**:
  - `totals_tr: Optional[BeautifulSoup]`: HTML table row for total statistics.
  - `sig_strikes_tr: Optional[BeautifulSoup]`: HTML table row for significant strikes.
  - `position: Optional[int]`: Fighter position in the table (0 or 1).
  - `fighter_link: Optional[str]`: URL of the fighter's details page.
  - `knockdowns: Optional[int]`: Number of knockdowns scored.
  - `non_sig_strikes_landed/attempted: Optional[int]`: Non-significant strikes landed/attempted.
  - `takedowns_landed/attempted: Optional[int]`: Takedowns landed/attempted.
  - `submission_attempts: Optional[int]`: Number of submission attempts.
  - `reversals: Optional[int]`: Number of reversals performed.
  - `control_time_seconds: Optional[int]`: Control time in seconds.
  - `head_strikes_landed/attempted: Optional[int]`: Significant head strikes landed/attempted.
  - `body_strikes_landed/attempted: Optional[int]`: Significant body strikes landed/attempted.
  - `leg_strikes_landed/attempted: Optional[int]`: Significant leg strikes landed/attempted.
  - `distance_strikes_landed/attempted: Optional[int]`: Significant distance strikes landed/attempted.
  - `clinch_strikes_landed/attempted: Optional[int]`: Significant clinch strikes landed/attempted.
  - `ground_strikes_landed/attempted: Optional[int]`: Significant ground strikes landed/attempted.
- **Key Methods**:
  - `create_roundstats()`: Populates statistics by parsing totals and significant strikes tables.
  - `to_string()`: Formats round statistics for display.
- **Role**: Provides granular performance data for a fighter in a single round, used by `Round`.

### Relationships Between Data Structures
The data structures form a hierarchical relationship, reflecting the structure of UFC events:
- **Events → Event**: The `Events` class manages a list of `Event` objects, each representing a single UFC event.
- **Event → Fight**: Each `Event` contains a list of `Fight` objects, representing all fights in that event.
- **Fight → Fighter**: Each `Fight` references two `Fighter` objects (`fighter_a` and `fighter_b`) for the competing fighters.
- **Fight → Round**: Each `Fight` contains a list of `Round` objects, one for each round in the fight (up to `round_of_victory`).
- **Round → RoundStats**: Each `Round` contains two `RoundStats` objects (`fighter_a_roundstats` and `fighter_b_roundstats`), representing per-fighter statistics for that round.
- **Fighter → RoundStats**: The `fighter_link` in `RoundStats` ties statistics back to a specific `Fighter`, ensuring accurate mapping of performance data.

This hierarchy allows the scraper to capture the full context of UFC events, from high-level event details to granular per-round fighter statistics.

## Setup
1. **Install Python**: Ensure Python 3.8+ is installed.
2. **Install Dependencies**: Install required Python packages using pip:
   ```bash
   pip install -r requirements.txt
