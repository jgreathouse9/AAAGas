from scraper import scrape_gas_prices

# Example usage
url = "https://gasprices.aaa.com/state-gas-price-averages/"
css_selector = "#sortable"  # The CSS selector for the table
gas_prices_df = scrape_gas_prices(url, css_selector)

# Save the DataFrame to a CSV
output_file = "gas_prices.csv"
gas_prices_df.to_csv(output_file, index=False)
print(f"Data saved to {output_file}")
