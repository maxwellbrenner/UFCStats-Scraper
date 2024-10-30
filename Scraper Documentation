# UFCStats Web Scraper

## Function Descriptions (Ordered by Execution in `main()`)

### 1. `get_page_content(url)`
- **Description**: This function retrieves and parses the HTML content from the given URL using the `requests` library. It returns a BeautifulSoup object if the request is successful, otherwise, it prints an error message and returns `None`.

### 2. `extract_event_info(event_element)`
- **Description**: Extracts basic information for an event, including the event name, link, date, and location. Returns an event dictionary and the parsed content (soup) of the event page.

### 3. `extract_fight_info(fight_row)`
- **Description**: Extracts information about a specific fight from a table row, including fight link, winner, method of victory, and fighter details (names and links).

### 4. `get_fight_link_and_winner(fight_row)`
- **Description**: Extracts the fight link, winner, and method of victory based on the table row information. If no fight link is available, it defaults to `'N/A'`, and if no winner is determined, it defaults to `'N/A'`. It returns the fight link, winner, and method of victory.

### 5. `extract_fighter_info(fighter_row)`
- **Description**: Extracts basic information about two fighters (names and links) from a table row. It returns two dictionaries representing fighter A and fighter B, along with empty lists for rounds information.

### 6. `scrape_fight_info(fight_info)`
- **Description**: Scrapes detailed fight information from the fight page, including rounds and results. Updates the `fight_info` dictionary with this data, including weight class, title fight status, gender, and round-specific information for both fighters.

### 7. `extract_victory_and_round_data(fight_soup, fight_info)`
- **Description**: Extracts the method of victory, round of victory, time of victory, time format, and referee data from the fight page and updates the `fight_info` dictionary.

### 8. `extract_round_data(row_fighter_data, row_strikes_data, fighter_a_name, fighter_b_name, fight_info)`
- **Description**: Extracts round-by-round data for both fighters, including fighter stats and strike data, and updates the `fight_info` dictionary with this information.

### 9. `extract_fighter_data(row, index)`
- **Description**: Extracts detailed fight statistics for a fighter, such as knockdowns, significant strikes, total strikes, takedowns, submission attempts, reversals, and control time. It returns this data in a dictionary for a specified fighter (index 0 for fighter A, 1 for fighter B).

### 10. `extract_strikes_data(row, index)`
- **Description**: Extracts detailed strike data for a fighter from a table row. It includes head, body, leg, distance, clinch, and ground strikes for a specified fighter (index 0 for fighter A, 1 for fighter B). It returns a dictionary containing these details.

### 11. `scrape_fighter_info(fighter_info)`
- **Description**: Scrapes individual fighter details from the fighter’s page, including height, reach, and date of birth, and updates the `fighter_info` dictionary with these attributes.

### 12. `convert_to_inches(height_info)`
- **Description**: Converts a height string from the format "feet'inches"" into inches (e.g., "6'0"" to 72 inches). If the conversion fails, it returns `'N/A'` for both the original format and inches.

### 13. `convert_to_numerical_date(date_str)`
- **Description**: Converts a date string in the format `'%b %d, %Y'` (e.g., `'Jan 01, 2020'`) into a numerical date in the format `'%m-%d-%Y'`. Returns `'N/A'` if the conversion fails.

### 14. `parse_date(date_str)`
- **Description**: This function converts a date string into the format `'MM-DD-YYYY'`. If the input is `'N/A'`, it returns `'N/A'`. If the conversion fails, it catches the error and returns `'N/A'`.
  
### 15. `write_to_csv(events_list)`
- **Description**: Writes the collected event and fight data, including detailed round-by-round statistics, to a CSV file. Each row in the CSV represents a fight, and columns include event details, fighter statistics, and round information.


---

## Overview of the `main()` Function

The `main()` function orchestrates the web scraping process by following these steps:

1. **Fetch the Main Page**: It retrieves the main page that lists all completed UFC events using the `get_page_content()` function.

2. **Parse Events**: It loops through the event elements (links to individual events) on the main page. For each event:
   - The `extract_event_info()` function is called to gather the event's basic details (name, date, location) and to parse the event page.
   
3. **Parse Fights**: For each event, it retrieves the list of fights:
   - The `extract_fight_info()` function extracts basic fight data such as fight link, winner, and fighter details from the event's fight table.
   - This information is added to the `fights` list in the event's dictionary.

4. **Scrape Detailed Fight and Fighter Information**: Once basic fight details are collected:
   - The `scrape_fight_info()` function is called to scrape detailed fight data, such as round-by-round stats, methods of victory, and more.
   - The `scrape_fighter_info()` function scrapes additional details for each fighter, including height, reach, and date of birth.

5. **Store Events**: The completed event (with detailed fight data) is added to the `events_list`.

6. **Write to CSV**: After processing all events and fights, the `write_to_csv()` function is called to save the results into a CSV file.

7. **Error Handling**: The function includes basic error handling to ensure that if an error occurs, the data collected so far is still written to the CSV.

By the end of the `main()` function, a detailed list of events and fight data is collected and written to a CSV file.

```python
def main():
    """
    Main function to orchestrate the web scraping process, including retrieving event data,
    scraping fight details and individual fighter stats, and finally writing all data to a CSV file.
    
    Returns:
    - list: List of dictionaries with detailed event and fight information (used for writing to CSV).
    """
    try:
        # URL of the main page listing all completed events
        url = 'http://www.ufcstats.com/statistics/events/completed?page=all'
        soup = get_page_content(url)

        # Check if the main page content was successfully retrieved
        if soup:
            event_elements = soup.find_all('a', class_='b-link b-link_style_black')
            events_list = []

            # Iterate over each event link found on the main page
            for event_element in event_elements:
                event_info, event_soup = extract_event_info(event_element)

                # Check if the event page content was successfully retrieved
                if event_soup:
                    fight_rows = event_soup.find_all('tr', class_='b-fight-details__table-row')[1:]  # Skip the header row which contains a future event

                    # Iterate over fight rows and extract fight information
                    for fight_row in fight_rows:
                        fight_info = extract_fight_info(fight_row)
                        event_info['fights'].append(fight_info)

                    events_list.append(event_info)

            # Process each event and associated fights to scrape detailed information
            for event_info in events_list:
                print(f"\nEvent: {event_info['name']}")
                print(f"Date: {event_info['date']}")
                print(f"Location: {event_info['location']}")

                for fight_info in event_info['fights']:
                    scrape_fight_info(fight_info)
                    scrape_fighter_info(fight_info['fighter_a'])
                    scrape_fighter_info(fight_info['fighter_b'])

        # Return the populated event list, useful for unit testing or further processing
        return events_list

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Always attempt to save data to CSV, even if an error occurs
        if events_list:
            print("Saving data to CSV due to an error or normal completion.")
            write_to_csv(events_list)
```


---

# UFCStats Web Scraper

This program scrapes data from the UFCStats website to extract detailed event, fight, and fighter statistics. It collects data such as fight results, significant strikes, fighter attributes, and outputs it into a CSV file for easy analysis.

## Starting Point of the Program

The program begins by executing the `main()` function. This function handles the overall flow, retrieving the main event page, scraping fight data for each event, and writing the output to a CSV file. Below is a step-by-step breakdown of the process:

### 1. Fetching the Main UFC Events Page

The program starts by requesting and parsing the UFCStats homepage for completed events. This is done by calling `get_page_content(url)`, where `url` points to the main UFC stats events page (`http://www.ufcstats.com/statistics/events/completed?page=all`).

![Homepage](images%20(UFCStats.com)/UFCStats%20-%20Homepage.png)
    
- The homepage contains a list of events, each represented by a hyperlink. The events are marked with their names, locations, and dates.
- Each event link is scraped and stored for further processing.

## Example of Scraped Data
### Event: UFC Fight Night: Cannonier vs. Borralho
- **Name**: UFC Fight Night: Cannonier vs. Borralho
- **Event Link**: http://www.ufcstats.com/event-details/be8ad887e4d674b0
- **Date**: 08-24-2024
- **Location**: Las Vegas, Nevada, USA
    

## Code References
- `get_page_content(url)`: Fetches the HTML page for completed UFC events.

```python
# Define headers for the HTTP request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
}

def get_page_content(url):
    """
    Retrieve and parse HTML content from a specified URL using a user-defined number of retries.
    Returns a BeautifulSoup object if successful, otherwise None.

    Parameters:
    - url (str): The URL from which to fetch content.

    Returns:
    - BeautifulSoup: Parsed HTML of the page, or None if the request fails after retries.
    """

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

    print("All attempts failed. Returning None.")
    return None
```
#
- `extract_event_info(event_element)`: Extracts information about each event (name, link, date, and location).

```python
def extract_event_info(event_element):
    """
    Extracts basic information for a given event element including name, link, date, and location.
    
    Parameters:
    - event_element (bs4.element.Tag): The BeautifulSoup tag for the event.

    Returns:
    - dict: A dictionary containing event name, link, formatted date, location, and an empty list for fights.
    """
    event_name = event_element.text.strip()
    event_link = event_element['href']
    
    # Extract date and location information
    event_date_str = event_element.find_next('span', class_='b-statistics__date').text.strip()
    event_location_str = event_element.find_next('td', class_='b-statistics__table-col b-statistics__table-col_style_big-top-padding').text.strip()
    
    # Format the date
    formatted_date = parse_date(event_date_str)
    
    # Create the event info dictionary
    event_info = {
        'name': event_name,
        'link': event_link,
        'date': formatted_date,
        'location': event_location_str,
        'fights': []  # Empty list to store fight information
    }
    
    # Retrieve event page content
    event_soup = get_page_content(event_info['link'])
    
    return event_info, event_soup
```


### 2. Extracting Event Details

Once the main event page has been parsed, the program moves on to individual event pages, which list all the fights for that event.

![Event Page](images%20(UFCStats.com)/UFCStats%20-%20Event%20Page.png)
    
- Each event contains fight data for all matchups on that card.
- The `extract_fight_info(fight_row)` function is responsible for extracting each fight’s basic information, such as fighter names, links, and method of victory.

## Example of Scraped Data
- **Fight Link**: [http://www.ufcstats.com/fight-details/15805ae1eea3343e](http://www.ufcstats.com/fight-details/15805ae1eea3343e)
- **Winner**: Caio Borralho  
- **Method of Victory**: Decision - Unanimous
- **fighter_a**: Caio Borralho 
- **fighter_b**: Jared Cannonier

## Code References    
- `extract_fight_info(fight_row)`: Extracts individual fight information like fighter names, method of victory, and fight link.

```python
def extract_fight_info(fight_row):
    """
    Extracts information about a specific fight, including fighter details, fight link, winner, and method of victory.
    
    Parameters:
    - fight_row (bs4.element.Tag): The BeautifulSoup tag containing the row with fight details.

    Returns:
    - dict: A dictionary containing the fight link, winner, method of victory, and fighter details.
    """
    # Extract fighter information
    fighter_a, fighter_b = extract_fighter_info(fight_row)
    
    # Check for fight link and winner determination
    fight_link, winner, method_of_victory = get_fight_link_and_winner(fight_row)
    
    return {
        'fight_link': fight_link,
        'winner': winner,
        'method_of_victory': method_of_victory,
        'fighter_a': fighter_a,
        'fighter_b': fighter_b
    }
```


### 3. Scraping Fight-Specific Data

The program navigates to the fight-specific page for each individual fight in an event.

![Fight Page](images%20(UFCStats.com)/UFCStats%20-%20Fight%20Page.png)
    
- On this page, detailed information about the fight is available, such as the weight class, fight result (method of victory), referee, and round-specific statistics (significant strikes, knockdowns, etc.).
- The `scrape_fight_info(fight_info)` function handles gathering these details from the fight page and updates the `fight_info` dictionary.

## Example of Scraped Data
- **Round of Victory**: 5  
- **Time of Victory**: 5:00  
- **Time Format**: 5 Rnd (5-5-5-5-5)  
- **Weight Class**: Middleweight Bout  
- **Referee**: Dan Miragliotta  
- **Title Fight**: False  
- **Gender**: Men

## Code References
- `scrape_fight_info(fight_info)`: Scrapes detailed fight data, including rounds, weight class, and method of victory.

```python
def scrape_fight_info(fight_info):
    """
    Retrieves detailed fight information including rounds and results from the fight page, 
    then updates the fight_info dictionary.

    Parameters:
    - fight_info (dict): Dictionary containing basic information about the fight and links.
    """
    fight_url = fight_info['fight_link']
    fight_soup = get_page_content(fight_url)

    if not fight_soup:
        print(f"Failed to retrieve the fight page for {fight_info['fighter_a']['name']} vs {fight_info['fighter_b']['name']}. Skipping...")
        return

    weight_class_element = fight_soup.find('i', class_='b-fight-details__fight-title')
    weight_class = weight_class_element.text.strip() if weight_class_element else 'N/A'

    # Updating fight_info with the obtained data
    fight_info.update({
        'weight_class': weight_class,
        'title_fight': 'title' in weight_class.lower(),
        'gender': 'women' if 'women' in weight_class.lower() else 'men',
        'method_of_victory': fight_info.get('method_of_victory', 'N/A'),
        'round_of_victory': 'N/A',
        'time_in_ROV': 'N/A',
        'time_format': 'N/A',
        'referee': 'N/A'
    })

    if fight_info['method_of_victory'] != 'NC':  # Only update if not a 'No Contest'
        extract_victory_and_round_data(fight_soup, fight_info)

    # Parsing round information and strikes data
    rows_fighter_data = fight_soup.select('.b-fight-details__section.js-fight-section')[2].find('table', class_='b-fight-details__table').select('tbody > tr.b-fight-details__table-row')
    rows_strikes_data = fight_soup.select('.b-fight-details__section.js-fight-section')[4].find('table', class_='b-fight-details__table').select('tbody > tr.b-fight-details__table-row')

    for i, (row_fighter_data, row_strikes_data) in enumerate(zip(rows_fighter_data, rows_strikes_data), start=1):
        extract_round_data(row_fighter_data, row_strikes_data, fight_info['fighter_a']['name'], fight_info['fighter_b']['name'], fight_info)

    print(f"\nFight Summary for {fight_info['fighter_a']['name']} vs {fight_info['fighter_b']['name']}:")
    print(f"Winner: {fight_info['winner']}")
    print(f"Method of Victory: {fight_info['method_of_victory']}")
    print(f"Round of Victory: {fight_info['round_of_victory']}")
    print(f"Time of Victory: {fight_info['time_in_ROV']}")
    print(f"Time Format: {fight_info['time_format']}")
    print(f"Weight Class: {fight_info['weight_class']}")
    print(f"Referee: {fight_info['referee']}")
    print(f"Title Fight: {fight_info['title_fight']}")
    print(f"Gender: {fight_info['gender']}")
    print(f"Fight Link: {fight_info['fight_link']}")

    # Print rounds information for both fighters
    print("\nRounds Information:")
    for i, round_data in enumerate(fight_info['fighter_a']['rounds_a'], start=1):
        print(f"\nRound {i}:")
        print(f"Fighter A: {round_data}")
        print(f"\nFighter B: {fight_info['fighter_b']['rounds_b'][i-1]}")
```


### 4. Extracting Round-by-Round Data

For each fight, detailed round-by-round statistics are extracted, including the number of significant strikes, body strikes, leg strikes, and more. This is handled by two helper functions:

- **General Fight Data:** The `extract_fighter_data()` function extracts other round-based data, such as knockdowns, submission attempts, takedowns, and control time.
    
![Round Statistics (General)](images%20(UFCStats.com)/UFCStats%20-%20Round%20Statistics%20(General).png)

## Code References
- `extract_fighter_data(row, index)`: Extracts fighter-specific statistics (e.g., knockdowns, takedowns, submission attempts) for each round.
  
```python
def extract_fighter_data(row, index):
    """
    Extracts and returns detailed statistics of a fighter from a specific row in the table.

    Parameters:
    - row (bs4.element.Tag): The row from which to extract data.
    - index (int): Index to specify the fighter (0 for the first, 1 for the second).

    Returns:
    - dict: Dictionary containing various statistics for the fighter.
    """
    # Fighter Name
    fighter_name_element = row.select('.b-fight-details__table-col.l-page_align_left a')
    fighter_name = fighter_name_element[index].text.strip() if fighter_name_element else 'N/A'

    # Knockdowns
    knockdowns_element = row.select(f'.b-fight-details__table-col:nth-of-type(2) p')
    knockdowns = knockdowns_element[index].text.strip() if knockdowns_element else 'N/A'

    # Sig. Strikes
    sig_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(3) p')
    sig_strikes = sig_strikes_element[index].text.strip() if sig_strikes_element else 'N/A'

    # Total Strikes
    total_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(5) p')
    total_strikes = total_strikes_element[index].text.strip() if total_strikes_element else 'N/A'

    # Takedowns
    takedowns_element = row.select(f'.b-fight-details__table-col:nth-of-type(6) p')
    takedowns = takedowns_element[index].text.strip() if takedowns_element else 'N/A'

    # Sub. Attempts
    sub_attempts_element = row.select(f'.b-fight-details__table-col:nth-of-type(8) p')
    sub_attempts = sub_attempts_element[index].text.strip() if sub_attempts_element else 'N/A'

    # Reversals
    reversals_element = row.select(f'.b-fight-details__table-col:nth-of-type(9) p')
    reversals = reversals_element[index].text.strip() if reversals_element else 'N/A'

    # Control Time
    control_time_element = row.select(f'.b-fight-details__table-col:nth-of-type(10) p')
    control_time = control_time_element[index].text.strip() if control_time_element else 'N/A'

    return {
        'name': fighter_name,
        'knockdowns': knockdowns,
        'sig_strikes': sig_strikes,
        'total_strikes': total_strikes,
        'takedowns': takedowns,
        'sub_attempts': sub_attempts,
        'reversals': reversals,
        'control_time': control_time,
    }
```

- **Significant Strikes:** The `extract_strikes_data()` function collects data about strikes such as strikes to the head, body, legs, and distance strikes.

![Round Statistics (Strikes)](images%20(UFCStats.com)/UFCStats%20-%20Round%20Statistics%20(Strikes).png)

## Code References
- `extract_strikes_data(row, index)`: Extracts round-based strike information.

```python
def extract_strikes_data(row, index):
    """
    Extracts detailed strikes data for a fighter from a specified row of the table.

    Parameters:
    - row (bs4.element.Tag): The BeautifulSoup tag of the row from which to extract data.
    - index (int): The index indicating which fighter's data to extract (0 for fighter_a, 1 for fighter_b).

    Returns:
    - dict: Dictionary containing various types of strikes information.
    """
    # Head Strikes
    head_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(4) p')
    head_strikes = head_strikes_element[index].text.strip() if head_strikes_element else 'N/A'

    # Body Strikes
    body_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(5) p')
    body_strikes = body_strikes_element[index].text.strip() if body_strikes_element else 'N/A'

    # Leg Strikes
    leg_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(6) p')
    leg_strikes = leg_strikes_element[index].text.strip() if leg_strikes_element else 'N/A'

    # Distance Strikes
    distance_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(7) p')
    distance_strikes = distance_strikes_element[index].text.strip() if distance_strikes_element else 'N/A'

    # Clinch Strikes
    clinch_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(8) p')
    clinch_strikes = clinch_strikes_element[index].text.strip() if clinch_strikes_element else 'N/A'

    # Ground Strikes
    ground_strikes_element = row.select(f'.b-fight-details__table-col:nth-of-type(9) p')
    ground_strikes = ground_strikes_element[index].text.strip() if ground_strikes_element else 'N/A'

    return {
        'head_strikes': head_strikes,
        'body_strikes': body_strikes,
        'leg_strikes': leg_strikes,
        'distance_strikes': distance_strikes,
        'clinch_strikes': clinch_strikes,
        'ground_strikes': ground_strikes,
    }
```

## Example of Scraped Data
#### Round 1:
- **Fighter A (Caio Borralho)**:  
  - Knockdowns: 0  
  - Significant Strikes: 15 of 32  
  - Total Strikes: 15 of 32  
  - Takedowns: 0 of 0  
  - Submission Attempts: 0  
  - Reversals: 0  
  - Control Time: 0:00  
  - Head Strikes: 7 of 22  
  - Body Strikes: 4 of 6  
  - Leg Strikes: 4 of 4  
  - Distance Strikes: 15 of 32  
  - Clinch Strikes: 0 of 0  
  - Ground Strikes: 0 of 0  

- **Fighter B (Jared Cannonier)**:  
  - Knockdowns: 0  
  - Significant Strikes: 12 of 34  
  - Total Strikes: 12 of 34  
  - Takedowns: 0 of 0  
  - Submission Attempts: 0  
  - Reversals: 0  
  - Control Time: 0:00  
  - Head Strikes: 4 of 23  
  - Body Strikes: 2 of 2  
  - Leg Strikes: 6 of 9  
  - Distance Strikes: 12 of 34  
  - Clinch Strikes: 0 of 0  
  - Ground Strikes: 0 of 0
 

### 5. Scraping Fighter Information

The program also scrapes individual fighter pages to gather more specific details such as height, reach, and date of birth. This is useful for contextualizing the statistics.
    
![Fighter Info](images%20(UFCStats.com)/UFCStats%20-%20Fighter%20Info.png)
    
- The `scrape_fighter_info(fighter_info)` function handles this task, retrieving attributes like height and reach from the fighter's profile page.

## Example of Scraped Data
### Fighter Info for **Caio Borralho**:
- **Name**: Caio Borralho
- **Height**: 6' 1"  
- **Reach**: 75"  
- **Date of Birth**: 01-16-1993  
- **Fighter Link**: [http://www.ufcstats.com/fighter-details/4126a78111c0855a](http://www.ufcstats.com/fighter-details/4126a78111c0855a)

## Code References
- `scrape_fighter_info(fighter_info)`: Gathers personal statistics for each fighter, such as height and reach.

```python
def scrape_fighter_info(fighter_info):
    """
    Scrapes and stores individual fighter details such as height, reach, and date of birth from the fighter's page.

    Parameters:
    - fighter_info (dict): Dictionary containing the fighter's name and link.
    """
    fighter_url = fighter_info['link']
    fighter_soup = get_page_content(fighter_url)

    if not fighter_soup:
        print(f"Failed to retrieve the fighter page for {fighter_info['name']}. Skipping...")
        return

    details_list = fighter_soup.find('ul', class_='b-list__box-list')
    details_items = details_list.find_all('li', class_='b-list__box-list-item')

    height_info = None
    reach_info = None
    dob_info = None

    for item in details_items:
        title = item.find('i', class_='b-list__box-item-title')
        if title:
            if 'Height' in title.text:
                height_info = item.contents[-1].strip()
            elif 'Reach' in title.text:
                reach_info = item.contents[-1].strip()
            elif 'DOB' in title.text:
                dob_info = item.contents[-1].strip()

    if height_info:
        fighter_info['height'] = {'feet_inches': height_info, 'inches': convert_to_inches(height_info)['inches']}
    else:
        fighter_info['height'] = {'feet_inches': 'N/A', 'inches': 'N/A'}

    if reach_info:
        fighter_info['reach'] = reach_info
    else:
        fighter_info['reach'] = 'N/A'

    if dob_info:
        dob_data = convert_to_numerical_date(dob_info)
        fighter_info['dob'] = dob_data['numerical_dob']
    else:
        fighter_info['dob'] = 'N/A'

    print(f"\nFighter Info for {fighter_info['name']}:")
    print(f"Height: {fighter_info['height']['feet_inches']}")
    print(f"Reach: {fighter_info['reach']}")
    print(f"Date of Birth: {fighter_info['dob']}")
    print(f"Fighter Link: {fighter_info['link']}")
```


### 6. Writing the Data to CSV

Once all event, fight, and fighter data has been collected, the program writes the results into a CSV file using the `write_to_csv(events_list)` function.

- The headers of the CSV include event name, event date, location, winner, fighter statistics, and round-by-round details.
- For each fight, it includes a row with detailed information about the event, fighter, and round statistics.

## Code References
- `write_to_csv(events_list)`: Writes all collected fight and fighter data to a CSV file for analysis.

```python
def write_to_csv(events_list):
    """
    Writes collected event data to a CSV file, including detailed round statistics for each fight.

    Parameters:
    - events_list (list): List of dictionaries, each representing an event and its associated fight data.
    """
    headers = [
        "event_name", "event_date", "event_location", "winner",
        "fighter_a_name", "fighter_b_name", "weightclass", "method_of_victory",
        "round_of_victory", "time_of_victory", "time_format", "referee",
        "title_fight", "gender", "fight_link", "fighter_a_height", "fighter_a_reach", "fighter_a_dob",
        "fighter_b_height", "fighter_b_reach", "fighter_b_dob"
    ]
    
    # Extend headers with round details for both fighters across five rounds
    rounds = 5
    for round_num in range(1, rounds + 1):
        for side in ['a', 'b']:
            prefix = f'rnd_{round_num}_{side}'
            headers.extend([
                f"{prefix}_knockdowns", f"{prefix}_sig_strikes", f"{prefix}_total_strikes",
                f"{prefix}_takedowns", f"{prefix}_sub_attemps", f"{prefix}_reversals",
                f"{prefix}_control_time", f"{prefix}_head_strikes", f"{prefix}_body_strikes",
                f"{prefix}_leg_strikes", f"{prefix}_distance_strikes", f"{prefix}_clinch_strikes",
                f"{prefix}_ground_strikes"
            ])

    with open('event_masterlist.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for event in events_list:
            for fight in event['fights']:
                row = [
                    event['name'], event['date'], event['location'], fight['winner'],
                    fight['fighter_a']['name'], fight['fighter_b']['name'],
                    fight['weight_class'], fight['method_of_victory'],
                    fight['round_of_victory'], fight['time_in_ROV'], fight['time_format'],
                    fight['referee'], fight['title_fight'], fight['gender'],
                    fight['fight_link'], fight['fighter_a'].get('height', {}).get('inches', 'NaN'),
                    fight['fighter_a'].get('reach', 'NaN'), fight['fighter_a'].get('dob', 'NaN'),
                    fight['fighter_b'].get('height', {}).get('inches', 'NaN'),
                    fight['fighter_b'].get('reach', 'NaN'),
                    fight['fighter_b'].get('dob', 'NaN')
                ]
                
                # Adding round details for each fighter
                for round_num in range(1, rounds + 1):
                    for side in ['a', 'b']:
                        round_data = fight.get(f'fighter_{side}').get(f'rounds_{side}', [])
                        if len(round_data) >= round_num:
                            round_stats = round_data[round_num - 1]
                            row.extend([
                                round_stats.get('knockdowns', 'NaN'),
                                round_stats.get('sig_strikes', 'NaN'),
                                round_stats.get('total_strikes', 'NaN'),
                                round_stats.get('takedowns', 'NaN'),
                                round_stats.get('sub_attempts', 'NaN'),
                                round_stats.get('reversals', 'NaN'),
                                round_stats.get('control_time', 'NaN'),
                                round_stats.get('head_strikes', 'NaN'),
                                round_stats.get('body_strikes', 'NaN'),
                                round_stats.get('leg_strikes', 'NaN'),
                                round_stats.get('distance_strikes', 'NaN'),
                                round_stats.get('clinch_strikes', 'NaN'),
                                round_stats.get('ground_strikes', 'NaN')
                            ])
                        else:
                            row.extend(['NaN'] * 13)  # Add NaN for all round stats if round data is missing

                writer.writerow(row)
```


## Final Data Columns

The following list represents the column headers for the CSV output of the UFCStats web scraper. The scraper collects fight data from UFC events, including both event-level and round-by-round statistics for two fighters. The data includes details such as significant strikes, total strikes, takedowns, control time, and other key fight metrics.

#### Column Structure

The data is structured to capture the following information:
- **Event Information**: General details about the UFC event, such as the event name, date, location, and link.
- **Fight Summary**: Information about the fight, including the winner, method of victory, and fighter details.
- **Round-by-Round Statistics**: Detailed statistics for each round, covering both fighters' performance metrics (e.g., knockdowns, significant strikes, takedowns, control time, etc.).

If a fight does not go the full 5 rounds, `NaN` values will be recorded for any rounds not reached.

#### Fighters and Rounds Explanation

The round-by-round data is structured for up to **5 rounds** of a fight, and statistics are collected for **both fighters (A and B)**.

To avoid redundancy, the columns follow this naming convention:
- **Round Data for Fighter A**: Prefixes like `rnd_one_a`, `rnd_two_a`, etc., represent statistics for Fighter A in each round.
- **Round Data for Fighter B**: Prefixes like `rnd_one_b`, `rnd_two_b`, etc., represent statistics for Fighter B in each round.

For example, `rnd_one_a_sig_strikes` refers to the number of significant strikes landed by Fighter A in Round 1, while `rnd_one_b_sig_strikes` refers to the same metric for Fighter B in Round 1.

#### Key Column Groups

1. **Event Information**:
   - `event_name`, `event_date`, `event_location`, `event_link`
   
2. **Fight Information**:
   - `winner`, `fighter_a_name`, `fighter_b_name`, `weightclass`, `method_of_victory`, `round_of_victory`, `time_of_victory`, `referee`, `title_fight`, `gender`, `fight_link`

3. **Fighter Details**:
   - `fighter_a_height`, `fighter_b_height`, `fighter_a_reach`, `fighter_b_reach`, `fighter_a_dob`, `fighter_b_dob`
   
4. **Round-by-Round Metrics (for each round, and for both fighters)**:
   - `knockdowns`
   - `sig_strikes`
   - `total_strikes`
   - `takedowns`
   - `sub_attemps`
   - `reversals`
   - `control_time`
   - `head_strikes`
   - `body_strikes`
   - `leg_strikes`
   - `distance_strikes`
   - `clinch_strikes`
   - `ground_strikes`

The full set of columns is dynamically generated for each round (up to 5 rounds) and each fighter (A and B), following this structure.

The final dataset will contain 151 columns, which includes all event information, fight details, fighter attributes, and round-by-round metrics for each fighter across up to five rounds. 
