from scraper import scrape_gas_prices
from datetime import datetime

# Example usage
url = "https://gasprices.aaa.com/state-gas-price-averages/"
css_selector = "#sortable"  # The CSS selector for the table
gas_prices_df = scrape_gas_prices(url, css_selector)

# Add a column for today's date
today_date = datetime.now().strftime('%Y-%m-%d')  # Format: YYYY-MM-DD
gas_prices_df['Date'] = today_date

# Save the DataFrame to CSV
output_file = f"gas_prices_{today_date}.csv"
gas_prices_df.to_csv(output_file, index=False)

# Display the DataFrame for debugging
print(gas_prices_df)
