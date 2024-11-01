# UFC Stats Scraper

![README Banner](images%20(UFCStats.com)/UFCStats%20-%20README%20Banner.png)

## Project Functionality

This project provides software to scrape detailed UFC event, fight, and fighter statistics from the [UFC Stats](http://www.ufcstats.com/) archive. It compiles this information into a well-structured CSV file.

The script is structured to perform multiple levels of scraping, starting from event details down to fight- and fighter-specific statistics. This hierarchy enables detailed analysis and insight into each event, each fight, and each competitor’s performance.

### 1. Event Information

The program begins by scraping the main [completed events page](http://www.ufcstats.com/statistics/events/completed?page=all), gathering the list of recent UFC events. It extracts:
- **Event Name**: (e.g., "UFC Fight Night: Cannonier vs. Borralho")
- **Event Link**: (URL to the event details page)
- **Event Date**: (parsed as a `datetime` object)
- **Event Location**: (e.g., "Las Vegas, Nevada, USA")

Each event’s individual page is then accessed to retrieve additional fight-level details.

### 2. Fight Details

For each event, the script extracts detailed information on each fight, iterating over all fight entries in the event. The fight details include:
- **Fighter Names and Links**: (URLs to each fighter’s profile page)
- **Winner**: (if determined; otherwise, it indicates a `Draw` or `No Contest`)
- **Method of Victory**: (e.g., KO/TKO, Decision, Submission)
- **Round and Time of Victory**: (if available)
- **Weight Class**: (e.g., "Featherweight Bout")
- **Title Fight**: (boolean indicating whether it was a title fight)
- **Gender**: (men or women's fight)
- **Fight Link**: (URL to the fight details page)
- **Detailed Round Information**: (number of knockdowns, significant strikes, total strikes, takedowns, control time, strikes breakdown by body region, and more)

### 3. Fighter Statistics

For each fighter involved in the event’s fights, the script accesses their profile page to obtain specific biographical and physical data:
- **Height**: (converted to both feet/inches and total inches)
- **Reach**: (in inches)
- **Date of Birth**: (converted to `datetime` format)

These attributes, when combined with fight details, provide a holistic view of each fighter's performance metrics and physical attributes, useful for comparisons or performance analysis.

### 4. Data Storage

After gathering event, fight, and fighter details, the script compiles all the data into a CSV file named `event_masterlist.csv`. This file contains detailed columns for each piece of data, including:
- **Event Information**: (name, date, location)
- **Fight Summary**: (winner, fight link, weight class, title fight, method of victory, etc)
- **Fighter Details**: (name, height, reach, date of birth)
- **Round-by-Round Statistics**: (for up to 5 rounds, including metrics for knockdowns, strikes, takedowns, submissions, control time, ect.)

The CSV structure allows users to easily load the data into data analysis tools (e.g., Python, R, Excel) for further examination.

### Requirements

The script requires the following Python packages:
- `requests`: To make HTTP requests to UFC Stats pages.
- `BeautifulSoup` from `bs4`: To parse and extract HTML content.
- `datetime`: For managing date formats.
- `csv`: To store collected data into a CSV format.

