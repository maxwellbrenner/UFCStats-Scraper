#src/scraper/fetch.py

"""Web fetching utilities for the UFC Stats Scraper.

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

import concurrent.futures
import random
import requests
import time
from bs4 import BeautifulSoup
from threading import Lock
from urllib3.exceptions import NameResolutionError
from typing import Dict, List, Optional

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
