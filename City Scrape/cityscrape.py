import pandas as pd
from datetime import datetime
from cityutils import fetch_gas_prices
import os

# We just need the state abbreviations since
# AAA indexes their states by the abbreviation.

url = "https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"

# We read the csv into a df
states_df = pd.read_csv(url)

# And now we just map the full name to the abbreviation
state_abbreviations = dict(zip(states_df["State"], states_df["Abbreviation"]))

# Here is the main function that does the scrape.
df = fetch_gas_prices(state_abbreviations)

# Format the date for the filename
date_str = datetime.now().strftime("%Y-%m-%d")

# Ensure the output directory exists
output_dir = "./City Scrape/Data"
os.makedirs(output_dir, exist_ok=True)

# Save the DataFrame as "/City Scrape/Data/City_{date}.csv"
output_path = f"{output_dir}/City_{date_str}.csv"
df.to_csv(output_path, index=False)
