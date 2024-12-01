from countyutils import get_state_abbreviations, get_gas_prices
import os
import pandas as pd
from datetime import datetime
import logging

# Configure logging for the main code
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("gas_prices.log"),  # Log to a file
        logging.StreamHandler()  # Also print to the console
    ]
)

try:
    logging.info("Starting gas price data collection.")

    today = datetime.now().strftime('%Y-%m-%d')

    # Fetch gas price data
    df = get_gas_prices(get_state_abbreviations())
    logging.info("Gas price data successfully fetched.")

    # Create directory if it doesn't exist
    directory = './RealCounty/Data'
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Directory {directory} created.")

    # Save the DataFrame to a CSV file
    filename = f"{directory}/CountyGas{today}.csv"
    df.to_csv(filename, index=False)
    logging.info(f"Data successfully saved to {filename}.")

except Exception as e:
    logging.error(f"An error occurred: {e}")
