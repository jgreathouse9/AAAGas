from scraper import scrape_gas_prices
from datetime import datetime
import os

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

# Save the DataFrame to a CSV file in the 'Prices' folder
output_file = os.path.join(output_dir, f"gas_prices_{today_date}.csv")
gas_prices_df.to_csv(output_file, index=False)
