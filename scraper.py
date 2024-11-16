import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO

def scrape_gas_prices(url, css_selector):
    """
    Scrapes a table from the given URL using the specified CSS selector
    and returns it as a pandas DataFrame.

    Parameters:
        url (str): The URL of the webpage to scrape.
        css_selector (str): The CSS selector for the table.

    Returns:
        pd.DataFrame: The scraped table as a DataFrame.
    """
    # Custom headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }

    # Fetch the HTML content with headers
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure the request was successful

    # Parse the HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table
    table = soup.select_one(css_selector)

    # Convert the table to a pandas DataFrame
    df = pd.read_html(StringIO(str(table)))[0]  # Wrap in StringIO

    return df
