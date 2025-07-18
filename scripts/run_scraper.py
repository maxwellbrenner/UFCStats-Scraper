#scripts/run_scraper.py

"""
Main script for running the UFC Stats Scraper.

This module defines the `main()` function, which orchestrates the scraping of UFC event data from ufcstats.com, processes fight details, 
and stores the results in a MySQL database and CSV file. It integrates with the `Events` class and database utilities to manage the scraping workflow.

Key components:
- `main()`: The primary function that initializes the scraper, creates the database if it doesn't exist, fetches new events, processes fight details, and handles data storage.
- Uses environment variables for database configuration via a `.env` file.
- Integrates with `Events` class for event scraping and `database` module for MySQL connectivity.
- Handles errors gracefully and ensures data is saved to CSV even on failure.

The script is designed to be executed as the entry point for the UFC Stats Scraper application.
"""

import os
import time
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
from src.scraper.events_manager import Events
from src.scraper.database import connect_to_mysql, get_latest_event_date

def create_database_if_not_exists(db_config):
    """
    Checks if the UFCStats database exists and creates it by executing create_database.sql if it doesn't.

    Args:
        db_config (dict): Database configuration with host, user, password, database, and auth_plugin.

    Returns:
        None

    Raises:
        mysql.connector.Error: If database connection or creation fails.
        FileNotFoundError: If create_database.sql is not found.
        Exception: For other unexpected errors during SQL execution.
    """
    try:
        # Attempt to connect without specifying the database to check if UFCStats exists
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        
        # Check if UFCStats database exists
        cursor.execute("SHOW DATABASES LIKE %s", (db_config['database'],))
        if cursor.fetchone():
            print(f"Database {db_config['database']} already exists.")
            cursor.close()
            conn.close()
            return

        print(f"Database {db_config['database']} does not exist. Creating it...")
        
        # Execute create_database.sql
        with open('scripts/create_database.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Execute multi-statement SQL
        for result in cursor.execute(sql_script, multi=True):
            pass  # Iterate through all statements to execute them
        
        conn.commit()
        print(f"Database {db_config['database']} created successfully.")
        
    except mysql.connector.Error as e:
        print(f"Database creation error: {e}")
        raise
    except FileNotFoundError:
        print("Error: scripts/create_database.sql not found.")
        raise
    except Exception as e:
        print(f"Error executing create_database.sql: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main() -> None:
    """
    Runs the UFCStats scraper, creating the database if it doesn't exist, fetching new events, processing fight details, and storing results in a MySQL database and CSV file.

    Functionality:
        - Loads environment variables for database configuration from a .env file.
        - Checks and creates the UFCStats database if it doesn't exist.
        - Initializes an Events manager and retrieves the latest event date from the database.
        - Scrapes new UFC events after the latest date, including fight and round statistics.
        - Stores scraped data in a MySQL database and exports it to a CSV file ('UFCStats.csv').
        - Handles database and general errors gracefully, ensuring data is saved to CSV even on failure.

    Raises:
        ValueError: If required database credentials (user or password) are missing in the .env file.
        mysql.connector.Error: If a database operation fails.
        Exception: For other unexpected errors during execution.

    Returns:
        None
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize events_manager outside try block to avoid UnboundLocalError
    events_manager = Events()

    try:
        # Database connection parameters
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME', 'UFCStats'),
            'auth_plugin': os.getenv('DB_AUTH_PLUGIN', 'mysql_native_password')
        }

        # Validate required credentials
        if not db_config['user'] or not db_config['password']:
            raise ValueError("Database user and password must be set in the .env file")

        # Create database if it doesn't exist
        create_database_if_not_exists(db_config)

        # Connect to MySQL and get latest event date
        conn = connect_to_mysql(**db_config)
        latest_date = get_latest_event_date()  # No parameters needed
        
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
            event.create_fights()
            scrape_time = time.time() - start_time
            # Pass scrape_time to to_string
            print(event.to_string(scrape_time=scrape_time))

        # Insert all events into MySQL
        events_manager.to_sql(**db_config)

    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Execution interrupted: {e}")
    finally:
        # Always write collected data to CSV
        events_manager.to_csv("UFCStats.csv")
        if 'conn' in locals():
            conn.close()
            
if __name__ == "__main__":
    main()
