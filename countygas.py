from countyscraper import get_all_state_data, plot_city_gas_prices, update_master_file
import os
import pandas as pd
import matplotlib.pyplot as plt
# Get all county-level gas price data (already sorted)
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
output_file = "CountyPrices/GasPrices.png"
plot_city_gas_prices(master_df, cities_to_plot, output_file)
