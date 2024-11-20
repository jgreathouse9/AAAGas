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
    print("Historical data sample:")
    print(historical_df[['Date']].head())
else:
    historical_df = pd.DataFrame()

if os.path.exists(output_file):
    old_df = pd.read_csv(output_file)
    print("Old data sample:")
    print(old_df[['Date']].head())
else:
    old_df = pd.DataFrame()

print("Live data sample:")
print(master_df[['Date']].head())

# Combine all datasets
combined_df = pd.concat([historical_df, old_df, master_df]).drop_duplicates().reset_index(drop=True)

# Debug: Print raw date values near invalid entries
print("Sample rows near invalid entries before conversion:")
print(combined_df[['City', 'State', 'Date']].iloc[-20:])

# Ensure consistent formatting by stripping time components
combined_df['Date'] = combined_df['Date'].astype(str).str[:10]

# Convert to datetime, coercing errors to identify problematic rows
combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')

# Check for invalid dates (NaT values)
if combined_df['Date'].isna().any():
    invalid_dates = combined_df[combined_df['Date'].isna()]
    print("Sample of invalid dates found:")
    print(invalid_dates[['City', 'State', 'Date']].head(10))
    print("Unique 'Date' values in the dataset before cleanup:")
    print(combined_df['Date'].unique())

    # Optional: Drop rows with invalid dates
    combined_df = combined_df.dropna(subset=['Date'])
    print("Dropped rows with invalid dates.")

    # If needed, replace NaT with a placeholder (uncomment below if desired)
    # combined_df['Date'] = combined_df['Date'].fillna(pd.Timestamp('1900-01-01'))

# Validate the cleanup
print("Final unique 'Date' values:")
print(combined_df['Date'].unique())

# Save the cleaned data
output_file = os.path.join(output_dir, "HistoricalGasData.csv")
combined_df.to_csv(output_file, index=False)
print(f"Data saved successfully to: {output_file}")
