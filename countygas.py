from countyscraper import get_all_state_data, plot_city_gas_prices
import os
import pandas as pd

# Get all county-level gas price data (already sorted)
master_df = get_all_state_data()

# Ensure the 'CountyPrices' directory exists
output_dir = "CountyPrices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Path to the master CSV file
master_file = os.path.join(output_dir, "MasterGas.csv")

# If the file exists, load and concatenate with the new data
if os.path.exists(master_file):
    existing_df = pd.read_csv(master_file)
    master_df = pd.concat([existing_df, master_df], ignore_index=True)

# Save the updated master DataFrame
master_df.to_csv(master_file, index=False)

# Plot gas prices for specified cities
cities_to_plot = ["Atlanta", "Metro Detroit"]
output_file = "CountyPrices/GasPrices.png"
plot_city_gas_prices(master_df, cities_to_plot, output_file)
