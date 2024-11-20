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
    old_df = pd.read_csv(output_file)

    print(f"Historical data sample:\n{historical_df[['Date']].head()}")
    print(f"Old data sample:\n{old_df[['Date']].head()}")
    print(f"Live data sample:\n{master_df[['Date']].head()}")

    combined_df = pd.concat([historical_df, old_df, master_df]).drop_duplicates().reset_index(drop=True)

    # Inspect rows around invalid entries before conversion
    print("Sample rows near invalid entries before conversion:")
    print(combined_df.iloc[395280:395300][['City', 'State', 'Date']])

    # Inspect unique date values before conversion
    print("Unique 'Date' values before conversion:")
    print(combined_df['Date'].unique())

    # Ensure all entries in the 'Date' column are valid datetime objects
    combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')

    # Check for any invalid dates (NaT values)
    if combined_df['Date'].isna().any():
        # Print rows with invalid dates for diagnosis
        invalid_dates = combined_df[combined_df['Date'].isna()]
        print(f"Sample of invalid dates found:\n{invalid_dates[['City', 'State', 'Date']].head(10)}")
        raise ValueError("Invalid dates detected in the 'Date' column. Process halted.")

    # Save the combined DataFrame
    output_file = os.path.join(output_dir, "HistoricalGasData.csv")
    combined_df.to_csv(output_file, index=False)
    print(f"Data saved successfully to: {output_file}")
else:
    # Save the live data as the historical file if no historical file exists
    master_df.to_csv(historical_file, index=False)
    print(f"No historical data found. Saved new data to: {historical_file}")
