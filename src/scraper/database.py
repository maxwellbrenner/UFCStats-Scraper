#src/scraper/database.py

"""Database utilities for the UFC Stats Scraper.

This module provides functions to interact with the MySQL database used for storing UFC event data. 
It includes utilities for establishing a database connection and retrieving the latest event date.

Key components:
- `connect_to_mysql()`: Establishes a connection to the MySQL database using specified credentials.
- `get_latest_event_date()`: Retrieves the most recent event date from the database.

The module integrates with the MySQL database to support data storage for the scraper.
"""

import mysql.connector
from datetime import date
from typing import Optional
import os

def connect_to_mysql(
    host: str = os.getenv('DB_HOST', 'localhost'),
    user: str = os.getenv('DB_USER'),
    password: str = os.getenv('DB_PASSWORD'),
    database: str = os.getenv('DB_NAME', 'UFCStats'),
    auth_plugin: str = os.getenv('DB_AUTH_PLUGIN', 'mysql_native_password')
) -> mysql.connector.connection.MySQLConnection:
    """
    Connect to a MySQL database with the specified parameters.

    Args:
        host (str): The database host.
        user (str): The database user.
        password (str): The user's password.
        database (str): The database name.
        auth_plugin (str): The authentication plugin to use.

    Returns:
        mysql.connector.connection.MySQLConnection: A MySQL connection object.

    Raises:
        mysql.connector.Error: If the connection fails.
    """
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        auth_plugin=auth_plugin
    )

def get_latest_event_date() -> Optional[date]:
    """
    Retrieve the date of the most recent event from the event table.

    Returns:
        Optional[date]: The latest event date, or None if no events exist.

    Raises:
        mysql.connector.Error: If the database query fails.
    """
    conn = connect_to_mysql()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM event")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row and row[0] else
