from countyscraper import get_all_state_data
import os
import pandas as pd

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# File paths
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
output_file = os.path.join(output_dir, "HistoricalGasData.csv")

# Get live gas price data
print("Fetching live gas price data...")
live_df = get_all_state_data()

# If historical data exists, load it; otherwise, just use the live data
if os.path.exists(historical_file):
    print("Loading historical data...")
    historical_df = pd.read_csv(historical_file)
    print("Historical data sample:")
    print(historical_df.head())

    # Combine historical data with live data
    combined_df = pd.concat([historical_df, live_df]).drop_duplicates().reset_index(drop=True)
else:
    print("No historical data found. Using live data only.")
    combined_df = live_df

# Ensure all dates are valid datetime objects
print("Converting 'Date' column to datetime...")
combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')

# Check for invalid dates
if combined_df['Date'].isna().any():
    print("Invalid dates detected. Sample rows with issues:")
    invalid_dates = combined_df[combined_df['Date'].isna()]
    print(invalid_dates.head(10))
    raise ValueError("Invalid dates detected in the 'Date' column. Process halted.")

# Save the combined data back to the historical file
print("Saving combined data...")
combined_df.to_csv(output_file, index=False)
print(f"Data successfully saved to: {output_file}")
