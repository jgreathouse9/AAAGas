import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from datetime import datetime, timedelta
import matplotlib
from dateutil.relativedelta import relativedelta


# Custom theme for matplotlib
jared_theme = {
    'axes.grid': True,
    'grid.linestyle': '-',
    'legend.framealpha': 1,
    'legend.facecolor': 'white',
    'legend.shadow': True,
    'legend.fontsize': 14,
    'legend.title_fontsize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'axes.labelsize': 16,
    'axes.titlesize': 20,
    'figure.dpi': 100,
    'axes.facecolor': 'white',
    'figure.figsize': (10, 8)
}

# Apply the theme to matplotlib
matplotlib.rcParams.update(jared_theme)


# Function to get state name from HTML (used for scraping)
def get_state_name_from_html(html):
    match = re.search(r"AAA\s(.*?)\sAvg", html)
    if match:
        return match.group(1)
    return None


def get_all_state_data():
    """
    Scrapes all state-level gas price data and returns it as a sorted DataFrame.
    """

    # Scraping logic to get the state URLs (same as before)
    def scrape_stateurls():
        url = "https://gasprices.aaa.com/state-gas-price-averages/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        table = BeautifulSoup(response.text, 'html.parser').select_one("#sortable")
        return [a['href'] for a in table.find_all('a', href=True)]

    # Function to scrape accordion table for each state
    def get_accordion_table(url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        html_content = str(soup)
        state_name = get_state_name_from_html(html_content)

        accordion = soup.select(".accordion-prices > h3, .accordion-prices > div")

        data = []
        current_city = None
        today = datetime.now().date()
        time_mapping = {
            "Current Avg.": today,
            "Yesterday Avg.": today - timedelta(days=1),
            "Week Ago Avg.": today - timedelta(weeks=1),
            "Month Ago Avg.": today - relativedelta(months=1),
            "Year Ago Avg.": today - relativedelta(years=1)
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
                        date = time_mapping.get(category, category)
                        row_data = [state_name, current_city, date] + [td.get_text(strip=True) for td in cells[1:]]
                        data.append(row_data)

        columns = ["State", "City", "Date", "Regular", "Mid", "Premium", "Diesel"]
        return pd.DataFrame(data, columns=columns)

    # Get all state URLs
    state_urls = scrape_stateurls()

    # Loop through URLs and scrape data
    all_data = []
    for url in state_urls:
        try:
            df = get_accordion_table(url)
            all_data.append(df)
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

    # Concatenate all the DataFrames and sort
    master_df = pd.concat(all_data, ignore_index=True)

    # Remove duplicate rows based on 'State', 'City', and 'Date' columns
    master_df = master_df.drop_duplicates(subset=['State', 'City', 'Date'], keep='first')

    # Optionally, reset the index after removing duplicates
    master_df = master_df.reset_index(drop=True)


    # Sort the DataFrame by State, City, and Date
    master_df = master_df.sort_values(by=['State', 'City', 'Date'])

    return master_df


# Function to plot gas prices for a specific city
import matplotlib.pyplot as plt


def plot_city_gas_prices(master_df, cities, output_file):
    # Ensure the 'Date' column is in datetime format
    master_df['Date'] = pd.to_datetime(master_df['Date'])

    # Set the plot size and style (optional)
    plt.figure(figsize=(10, 6))

    # Plot each city's gas prices with specific styling
    for city in cities:
        city_data = master_df[master_df['City'] == city]

        # Custom styling for the lines and markers
        if city == "Atlanta":
            color = "#C8102E"  # Electric blue for Atlanta
            marker = 'D'  # Diamond marker
            mfc = '#00f0ff'  # Marker face color (sky blue)
        elif city == "Metro Detroit":
            color = "#0076B6"  # Dark blue for Detroit
            marker = 'D'  # Diamond marker
            mfc = 'black'  # Marker face color (black)

        plt.plot(
            city_data['Date'],
            city_data['Regular'],
            color=color,  # Line color
            marker=marker,  # Diamond marker
            markersize=5,  # Adjust marker size
            mfc=mfc,  # Marker face color
            mec='black',  # Marker edge color (black outline)
            label=city
        )

    # Add title and labels
    plt.title("Gas Prices for Detroit and Atlanta", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Price (USD)", fontsize=14)

    # Add a legend to differentiate the cities
    plt.legend(title="Cities", fontsize=12)

    # Make the plot look nice
    plt.tight_layout()

    # Save the plot to the output file
    plt.savefig(output_file)

    plt.close()
