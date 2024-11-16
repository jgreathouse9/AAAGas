from scraper import scrape_gas_prices
from datetime import datetime
import os
import pandas as pd

# Example usage
url = "https://gasprices.aaa.com/state-gas-price-averages/"
css_selector = "#sortable"  # The CSS selector for the table
gas_prices_df = scrape_gas_prices(url, css_selector)

# Add a column for today's date
today_date = datetime.now().strftime('%Y-%m-%d')  # Format: YYYY-MM-DD
gas_prices_df['Date'] = today_date

# Create 'Prices' folder if it doesn't exist
output_dir = "Prices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Save the new day's CSV file in the 'Prices' folder
new_file = os.path.join(output_dir, f"gas_prices_{today_date}.csv")
gas_prices_df.to_csv(new_file, index=False)

# Check if the 'MasterGas.csv' file exists
master_file = "Prices/MasterGas.csv"

if os.path.exists(master_file):
    # If MasterGas.csv exists, load it and append the new data
    master_df = pd.read_csv(master_file)
    master_df = pd.concat([master_df, gas_prices_df], ignore_index=True)
else:
    # If MasterGas.csv does not exist, create it with the current day's data
    master_df = gas_prices_df

# Save the updated master file
master_df.to_csv(master_file, index=False)
