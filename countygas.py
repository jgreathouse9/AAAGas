from countyscraper import get_all_state_data, plot_city_gas_prices
import os
import pandas as pd

# Get live gas price data
master_df = get_all_state_data()

# Ensure the 'CountyPrices' directory exists
output_dir = "./CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# Load historical data and combine it with the live data
historical_file = os.path.join(output_dir, "HistoricalGasData.csv")
output_file = os.path.join(output_dir, "LiveScrape.csv")

if os.path.exists(historical_file):
    historical_df = pd.read_csv(historical_file)
    if os.path.exists(output_file):
        old_df = pd.read_csv(output_file)
    else:
        old_df = pd.DataFrame()

    combined_df = pd.concat([historical_df, old_df, master_df]).drop_duplicates().reset_index(drop=True)
else:
    combined_df = master_df

# Ensure all entries in the 'Date' column are valid datetime objects
combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')

# Check for any invalid dates (NaT values)
if combined_df['Date'].isna().any():
    # Print the rows with invalid dates for diagnosis
    invalid_dates = combined_df[combined_df['Date'].isna()]
    print(f"Invalid dates found:\n{invalid_dates}")
    raise ValueError("Invalid dates detected in the 'Date' column. Process halted.")

# If all dates are valid, proceed to save
combined_df.to_csv(historical_file, index=False)
print(f"Data saved successfully to: {historical_file}")
