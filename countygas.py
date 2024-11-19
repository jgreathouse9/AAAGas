from countyscraper import get_all_state_data, plot_city_gas_prices, update_master_file
import os
import pandas as pd

# Get all county-level gas price data
master_df = get_all_state_data()

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Update the master file
master_file = os.path.join(output_dir, "MasterGas.csv")
master_df = update_master_file(master_df, master_file)

# Plot gas prices for specified cities
cities_to_plot = ["Atlanta", "Metro Detroit"]
plot_file = os.path.join(output_dir, "GasPrices.png")
plot_city_gas_prices(master_df, cities_to_plot, plot_file)

# Load historical data
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
if os.path.exists(historical_file):
    historical_df = pd.read_csv(historical_file)
else:
    historical_df = pd.DataFrame(columns=master_df.columns)

# Combine historical and live data
full_city_df = pd.concat([historical_df, master_df], ignore_index=True).drop_duplicates()

# Export the combined data to FullCityGas.csv
full_city_file = os.path.join(output_dir, "FullCityGas.csv")
full_city_df.to_csv(full_city_file, index=False)

# Ensure the output directory exists again (redundant but safe)
os.makedirs(output_dir, exist_ok=True)

# Export the master file
master_df.to_csv(master_file, index=False)

print(f"Master file saved to: {master_file}")
print(f"Combined city data saved to: {full_city_file}")
print(f"City gas prices plot saved to: {plot_file}")
