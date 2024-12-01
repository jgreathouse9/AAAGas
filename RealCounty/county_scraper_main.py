from countyutils import get_state_abbreviations, get_gas_prices
import os
import pandas as pd
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')


# Fetch gas prices and return as a DataFrame
df = get_gas_prices(get_state_abbreviations())

# Ensure the directory exists, create it if it doesn't
directory = './Data'

if not os.path.exists(directory):
    os.makedirs(directory)

# Save the DataFrame to CSV in the specified directory
filename = f"{directory}/CountyGas{today}.csv"
df.to_csv(filename, index=False)
print(f"Saved data to {filename}")
