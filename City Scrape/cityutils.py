import requests
from bs4 import BeautifulSoup
import pandas as pd
from dateutil.relativedelta import relativedelta

def fetch_gas_prices(state_abbreviations):
    """Grabs and processes gas prices for
    all counties. This is the parent function."""
    
    # Here we define headers.
    # This is so our scraping will be easier without being blocked. Unlikely in this case,
    # but it's just good practice to have them.
    
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    # AAA consistently maps their prices to these strings.
    # So to facilitate this, we map them to each other.
    
    today = pd.Timestamp.today()
    time_mapping = {
        "Current Avg.": lambda: today,
        "Yesterday Avg.": lambda: today - pd.Timedelta(days=1),
        "Week Ago Avg.": lambda: today - pd.Timedelta(weeks=1),
        "Month Ago Avg.": lambda: today - relativedelta(months=1),
        "Year Ago Avg.": lambda: today - relativedelta(years=1),
    }

    def extract_gas_prices(row, time_mapping, today, state, city_name):
        """Extract and process gas price data from a row Specifically this is the row for the accordion tables found at the bottom
        of the page."""
        
        cells = row.find_all('td')
        date_text = cells[0].get_text(strip=True)
        
        # Get the corresponding date using time_mapping, defaulting to today
        date = time_mapping.get(date_text, lambda: today)().strftime('%Y-%d-%m')
        
        # Extract prices, removing the dollar sign
        prices = [cell.get_text(strip=True).replace('$', '') for cell in cells[1:]]
        
        # Return the processed data
        return [date, state, city_name] + prices

    # Helper function to process each city's data
    def process_city_data(city, time_mapping, today, state):
        """Process the data for a single city and extract gas prices."""
        city_name = city.get_text(strip=True)
        rows = city.find_next('table').select('tbody tr')
        
        # Use list comprehension to process each row and return the results
        return [extract_gas_prices(row, time_mapping, today, state, city_name) for row in rows]

    # Function to process all states
    def process_states(state_abbreviations, headers, time_mapping, today):
        """Process data for all states and return accumulated data."""
        all_data = []
        for state, abbreviation in state_abbreviations.items():
            params = {'state': abbreviation}
            response = requests.get('https://gasprices.aaa.com/', params=params, headers=headers)

            if response.status_code != 200:
                print(f"Error fetching data for {state}. Status code: {response.status_code}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract city sections
            cities = soup.select('.accordion-prices.metros-js > h3[data-title]')
            
            # Use map to process each city and flatten the list of rows
            all_data.extend([row_data for city in cities for row_data in process_city_data(city, time_mapping, today, state)])

        return all_data

    # Process states and get all data
    all_data = process_states(state_abbreviations, headers, time_mapping, today)

    # Convert list of data into DataFrame
    all_data_df = pd.DataFrame(all_data, columns=['Date', 'State', 'City', 'Regular', 'Mid-Grade', 'Premium', 'Diesel'])

    # Convert 'Date' to datetime
    all_data_df['Date'] = pd.to_datetime(all_data_df['Date'], format='%Y-%d-%m')

    # Sort by 'State', 'City', and 'Date'
    all_data_df = all_data_df.sort_values(by=['State', 'City', 'Date']).reset_index(drop=True)

    return all_data_df
