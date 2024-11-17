import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re


def get_state_name_from_html(html):
    """
    Scrapes the state name (e.g., "Alaska") from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The state name extracted from the HTML.
    """
    match = re.search(r"AAA\s(.*?)\sAvg", html)
    if match:
        return match.group(1)
    return None


def scrape_stateurls():
    """
    Scrapes state-specific URLs from the #sortable table on the AAA gas prices page.

    Returns:
        list: A list of href URLs for state-specific gas prices.
    """
    url = "https://gasprices.aaa.com/state-gas-price-averages/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }

    # Fetch the HTML content
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    # Locate the table and extract URLs
    table = BeautifulSoup(response.text, 'html.parser').select_one("#sortable")
    return [a['href'] for a in table.find_all('a', href=True)]


def get_accordion_table(url):
    """
    Scrapes accordion table data from the given URL and returns a DataFrame.

    Args:
        url (str): The URL of the webpage to scrape.

    Returns:
        pd.DataFrame: DataFrame containing city-specific average gas prices and dates.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    html_content = str(soup)  # Convert soup object to string to apply regex
    state_name = get_state_name_from_html(html_content)

    accordion = soup.select(".accordion-prices > h3, .accordion-prices > div")

    data = []
    current_city = None
    today = datetime.now().date()  # This will set today to the current date dynamically

    # Mapping for time-based averages to actual dates
    time_mapping = {
        "Current Avg.": today,
        "Yesterday Avg.": today - timedelta(days=1),
        "Week Ago Avg.": today - timedelta(weeks=1),
        "Month Ago Avg.": today - timedelta(days=30),
        "Year Ago Avg.": today - timedelta(days=365)
    }

    for element in accordion:
        if element.name == "h3":
            current_city = element.get_text(strip=True)
        elif element.name == "div":
            table = element.select_one("table.table-mob tbody")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    category = cells[0].get_text(strip=True)
                    date = time_mapping.get(category, category)  # Replace category with a date if it exists in the mapping
                    row_data = [state_name, current_city, date] + [td.get_text(strip=True) for td in cells[1:]]
                    data.append(row_data)

    # Define column names
    columns = ["State", "City", "Date", "Regular", "Mid", "Premium", "Diesel"]
    return pd.DataFrame(data, columns=columns)


def get_all_state_data():
    # Get the list of state URLs
    state_urls = scrape_stateurls()

    # Initialize an empty list to store DataFrames
    all_data = []

    # Loop through the state URLs and collect the data inside the function
    for url in state_urls:
        try:
            df = get_accordion_table(url)  # get_accordion_table now handles each URL
            all_data.append(df)
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

    # Concatenate all the DataFrames into a single one
    final_df = pd.concat(all_data, ignore_index=True)

    return final_df