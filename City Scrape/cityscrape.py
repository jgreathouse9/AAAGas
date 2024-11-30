import pandas as pd
from datetime import datetime
from cityutils import fetch_gas_prices

# URL of the CSV file
url = "https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"

# Read the CSV into a DataFrame
states_df = pd.read_csv(url)

# Create a dictionary mapping state names to abbreviations
state_abbreviations = dict(zip(states_df['State'], states_df['Abbreviation']))

# Fetch gas prices
df = fetch_gas_prices(state_abbreviations)

# Format the date for the filename
date_str = datetime.now().strftime("%Y-%m-%d")

# Save the DataFrame as "/Data/City_{date}.csv"
output_path = f"./Data/City_{date_str}.csv"
df.to_csv(output_path, index=False)

print(f"Data saved to {output_path}")
