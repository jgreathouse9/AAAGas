from countyscraper import get_all_state_data, plot_city_gas_prices
import os

# Get all metro-level gas price data
master_df = get_all_state_data()

# Creating the relevant directory
output_dir = "CountyPrices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Dropping duplicates
master_df = master_df.drop_duplicates(subset=['State', 'City', 'Date'])
master_file = os.path.join(output_dir, "MasterGas.csv")

#!! Saving the combined df sans duplicates
master_df.to_csv(master_file, index=False)

# Generate plot for ATL
plot_path = os.path.join(output_dir, "GasPrices_Atlanta.png")
plot_city_gas_prices(master_df, "Atlanta", plot_path)
