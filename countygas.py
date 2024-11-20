from countyscraper import get_all_state_data
import os
import pandas as pd

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# File paths for historical, live, and merged data
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
live_file = os.path.join(output_dir, "LiveScrape.csv")
merged_file = os.path.join(output_dir, "MasterMergedGas.csv")

# Get live gas price data
print("Fetching live gas price data...")
live_df = get_all_state_data()

# If historical data exists, load it; otherwise, just use the live data
if os.path.exists(historical_file):
    print("Loading historical data...")
    historical_df = pd.read_csv(historical_file)
    print("Historical data sample:")
    print(historical_df.head())

    # Combine historical data with live data, ensuring no duplicates
    combined_df = pd.concat([historical_df, live_df]).drop_duplicates().reset_index(drop=True)

    # Save the combined data to the MasterMergedGas.csv
    print("Saving combined data to MasterMergedGas.csv...")
    combined_df.to_csv(merged_file, index=False)
    print(f"Data successfully saved to: {merged_file}")

else:
    print("No historical data found. Using live data only.")
    live_df.to_csv(merged_file, index=False)  # If no historical data, save only live data to merged file
    print(f"Live data successfully saved to: {merged_file}")

# Save the live data separately to LiveScrape.csv
print("Saving live data to LiveScrape.csv...")
live_df.to_csv(live_file, index=False)
print(f"Live data successfully saved to: {live_file}")

