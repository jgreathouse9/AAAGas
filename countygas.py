from countyscraper import get_all_state_data, plot_city_gas_prices, update_master_file
import os
import pandas as pd

# Get live gas price data
master_df = get_all_state_data()

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# Update the master file
master_file = os.path.join(output_dir, "MasterGas.csv")
master_df = update_master_file(master_df, master_file)

# Load historical data and combine it with the live data
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
output_file = os.path.join(output_dir, "FullCityGas.csv")

if os.path.exists(historical_file):
    historical_df = pd.read_csv(historical_file)
    combined_df = pd.concat([historical_df, master_df]).drop_duplicates().reset_index(drop=True)

    # Plot the combined data
    cities_to_plot = ["Atlanta", "Metro Detroit"]
    plot_file = os.path.join(output_dir, "CombinedGasPrices.png")
    plot_city_gas_prices(combined_df, cities_to_plot, plot_file)

    # Save the combined dataset
    combined_df.to_csv(output_file, index=False)
    print(f"Combined dataset saved to: {output_file}")
else:
    print(f"Historical file not found. Skipping append step.")
