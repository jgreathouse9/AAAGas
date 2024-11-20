from countyscraper import get_all_state_data
import os
import pandas as pd

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# File paths
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
live_file = os.path.join(output_dir, "LiveScrape.csv")
merged_file = os.path.join(output_dir, "MasterMergedGas.csv")

# Fetch today's live gas price data
print("Fetching today's live gas price data...")
today_live_df = get_all_state_data()

# If LiveScrape.csv exists, load it; otherwise, use today's data
if os.path.exists(live_file):
    print("Loading existing live scrape data...")
    existing_live_df = pd.read_csv(live_file)
    print("Existing live data sample:")
    print(existing_live_df.head())

    # Append today's live data, removing duplicates
    all_live_df = pd.concat([existing_live_df, today_live_df]).drop_duplicates().reset_index(drop=True)
else:
    print("No existing live data found. Using today's data only.")
    all_live_df = today_live_df

# Save updated live data back to LiveScrape.csv
print("Saving updated live data to LiveScrape.csv...")
all_live_df.to_csv(live_file, index=False)

# If HistoricalGasData.csv exists, load it; otherwise, just use live data for merged file
if os.path.exists(historical_file):
    print("Loading historical data...")
    historical_df = pd.read_csv(historical_file)
    print("Historical data sample:")
    print(historical_df.head())

    # Merge historical and live data, removing duplicates
    merged_df = pd.concat([historical_df, all_live_df]).drop_duplicates().reset_index(drop=True)
else:
    print("No historical data found. Using live data only for merged file.")
    merged_df = all_live_df

# Ensure 'Date' column is valid
print("Converting 'Date' column to datetime...")
merged_df['Date'] = pd.to_datetime(merged_df['Date'], errors='coerce')

# Check for invalid dates
if merged_df['Date'].isna().any():
    print("Invalid dates detected. Sample rows with issues:")
    invalid_dates = merged_df[merged_df['Date'].isna()]
    print(invalid_dates.head(10))
    raise ValueError("Invalid dates detected in the 'Date' column. Process halted.")

# Save merged data to MasterMergedGas.csv
print("Saving merged data to MasterMergedGas.csv...")
merged_df.to_csv(merged_file, index=False)
print(f"Data successfully saved to: {merged_file}")
