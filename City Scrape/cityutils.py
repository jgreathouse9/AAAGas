import requests
from bs4 import BeautifulSoup
import pandas as pd
from dateutil.relativedelta import relativedelta  # For precise relative deltas

def fetch_gas_prices(state_abbreviations):
    """Fetch and process gas prices for all states."""
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    today = pd.Timestamp.today()
    time_mapping = {
        "Current Avg.": today,
        "Yesterday Avg.": today - pd.Timedelta(days=1),
        "Week Ago Avg.": today - pd.Timedelta(weeks=1),
        "Month Ago Avg.": today - relativedelta(months=1),
        "Year Ago Avg.": today - relativedelta(years=1),
    }

    def process_state_data(state, abbreviation):
        """Fetch and process gas prices for a specific state."""
        params = {'state': abbreviation}
        response = requests.get('https://gasprices.aaa.com/', params=params, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract city sections and process them
        city_sections = soup.select('.accordion-prices.metros-js > h3[data-title]')
        return list(map(extract_city_data, city_sections))  # Return the processed data for this state

    def extract_city_data(city_section):
        """Extract city data from a city section."""
        city_name = city_section.get_text(strip=True)
        table = city_section.find_next('table')
        rows = table.select('tbody tr')
        return list(map(lambda row: process_row(row, city_name, time_mapping), rows))

    def process_row(row, city_name, time_mapping):
        """Process a single row and return the data."""
        cells = row.find_all('td')
        date_label = cells[0].get_text(strip=True)
        date = time_mapping.get(date_label, today).strftime('%Y-%m-%d')
        prices = [cell.get_text(strip=True).replace('$', '') for cell in cells[1:]]
        return [date, state, city_name, *prices]

    # Use map to process all states concurrently or sequentially (if order matters)
    all_data = list(map(lambda state_item: process_state_data(state_item[0], state_item[1]), state_abbreviations.items()))

    # Flatten the list of lists into a single list of data
    all_data_flat = [item for sublist in all_data for item in sublist]

    # Create a DataFrame from the collected data
    all_data_df = pd.DataFrame(all_data_flat, columns=['Date', 'State', 'City', 'Regular', 'Mid-Grade', 'Premium', 'Diesel'])

    # Convert 'Date' to datetime and sort
    all_data_df['Date'] = pd.to_datetime(all_data_df['Date'], format='%Y-%m-%d')
    all_data_df.sort_values(by=['State', 'City', 'Date'], inplace=True)
    all_data_df.reset_index(drop=True, inplace=True)

    return all_data_df
