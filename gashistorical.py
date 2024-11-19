import os
import pandas as pd
from datetime import datetime, timedelta

def fetch_and_combine_gas_prices(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches daily gas price data from the specified date range, cleans, and combines the data.

    Parameters:
    - start_date (str): Start date in 'YYYY-MM-DD' format.
    - end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
    - pd.DataFrame: Combined and cleaned DataFrame with gas price data.
    """
    # Base URL for the CSV files
    base_url = "https://raw.githubusercontent.com/gueyenono/ScrapeUSGasPrices/refs/heads/master/data/city/"

    # Convert input dates to datetime objects
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # List to hold the DataFrames
    dataframes = []

    # Loop through the date range
    current_date = start
    while current_date <= end:
        # Generate the URL for the current date
        date_str = current_date.strftime("%Y-%m-%d")
        csv_url = f"{base_url}{date_str}-usa_gas_price-city.csv"

        try:
            # Read the CSV directly into a DataFrame
            df = pd.read_csv(csv_url)

            # Remove the first column (usually an index column)
            df = df.iloc[:, 1:]

            # Move the last two columns to the beginning
            columns = df.columns.tolist()
            reordered_columns = columns[-2:] + columns[:-2]
            df = df[reordered_columns]

            # Append to the list
            dataframes.append(df)
            print(f"Successfully fetched and processed data for {date_str}")
        except Exception as e:
            print(f"Failed to fetch data for {date_str}: {e}")

        # Move to the next day
        current_date += timedelta(days=1)

    # Combine all fetched DataFrames
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        # Rename the columns to match the scraper's naming conventions
        combined_df.columns = ["City", "State", "Date", "Regular", "Mid", "Premium", "Diesel"]
        print("Successfully combined and renamed all data")
        return combined_df
    else:
        print("No data was fetched")
        return pd.DataFrame(columns=["City", "State", "Date", "Regular", "Mid", "Premium", "Diesel"])


# Ensure the CountyPrices directory exists
output_dir = "CountyPrices"
os.makedirs(output_dir, exist_ok=True)

# Example usage
start_date = "2021-10-01"
end_date = "2024-04-16"

# Fetch and combine the gas price data
combined_df = fetch_and_combine_gas_prices(start_date, end_date)

# Save to the CountyPrices directory
output_file = os.path.join(output_dir, "HistoricalGasData.csv")
combined_df.to_csv(output_file, index=False)
print(f"Historical gas data saved to: {os.path.abspath(output_file)}")
