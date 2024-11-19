from countyscraper import get_all_state_data, plot_city_gas_prices, update_master_file
import os
import pandas as pd
import matplotlib.pyplot as plt

# Get all county-level gas price data
master_df = get_all_state_data()

# Ensure the 'CountyPrices' directory exists
output_dir = "CountyPrices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Update the master file
master_file = os.path.join(output_dir, "MasterGas.csv")
master_df = update_master_file(master_df, master_file)

# Plot gas prices for specified cities
cities_to_plot = ["Atlanta", "Metro Detroit"]
plot_file = os.path.join(output_dir, "GasPrices.png")
plot_city_gas_prices(master_df, cities_to_plot, plot_file)

# Ensure the output directory exists again (redundant but safe)
os.makedirs(output_dir, exist_ok=True)

# Export the MasterGas.csv file
output_file = os.path.join(output_dir, "MasterGas.csv")
master_df = master_df.drop_duplicates(subset=["State", "City", "Date"], keep="first")
master_df.to_csv(output_file, index=False)
