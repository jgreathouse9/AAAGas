import requests
from bs4 import BeautifulSoup
import pandas as pd
from dateutil.relativedelta import relativedelta

def fetch_gas_prices(state_abbreviations):
    """Fetch and process gas prices for all states."""
    # Define headers
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    # Initialize an empty list to hold all data
    all_data = []

    # Time mapping for relative deltas using relativedelta
    today = pd.Timestamp.today()
    time_mapping = {
        "Current Avg.": lambda: today,
        "Yesterday Avg.": lambda: today - pd.Timedelta(days=1),
        "Week Ago Avg.": lambda: today - pd.Timedelta(weeks=1),
        "Month Ago Avg.": lambda: today - relativedelta(months=1),
        "Year Ago Avg.": lambda: today - relativedelta(years=1),
    }

    # Iterate over each state abbreviation
    for state, abbreviation in state_abbreviations.items():
        params = {'state': abbreviation}
        response = requests.get('https://gasprices.aaa.com/', params=params, headers=headers)

        if response.status_code != 200:
            print(f"Error fetching data for {state}. Status code: {response.status_code}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract city sections
        cities = soup.select('.accordion-prices.metros-js > h3[data-title]')
        
        # Extract data using list comprehensions
        for city in cities:
            city_name = city.get_text(strip=True)
            rows = city.find_next('table').select('tbody tr')

            for row in rows:
                cells = row.find_all('td')
                date_text = cells[0].get_text(strip=True)
                date = time_mapping.get(date_text, lambda: today)().strftime('%Y-%d-%m')
                prices = [cell.get_text(strip=True).replace('$', '') for cell in cells[1:]]
                
                all_data.append([date, state, city_name] + prices)

    # Convert list of data into DataFrame
    all_data_df = pd.DataFrame(all_data, columns=['Date', 'State', 'City', 'Regular', 'Mid-Grade', 'Premium', 'Diesel'])

    # Convert 'Date' to datetime
    all_data_df['Date'] = pd.to_datetime(all_data_df['Date'], format='%Y-%d-%m')

    # Sort by 'State', 'City', and 'Date'
    all_data_df = all_data_df.sort_values(by=['State', 'City', 'Date']).reset_index(drop=True)

    return all_data_df
