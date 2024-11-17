import os
from countyscraper import get_all_state_data
import pandas as pd
from datetime import datetime

# Call the function to get all state data
final_df = get_all_state_data()
# Create 'CountyPrices' folder if it does not yet exist
output_dir = "CountyPrices"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Save the final dataset to a CSV file in the 'CountyPrices' folder
today_date = datetime.now().strftime('%Y-%m-%d')  # Format: YYYY-MM-DD
final_file = os.path.join(output_dir, f"county_gas_prices_{today_date}.csv")
final_df.to_csv(final_file, index=False)

# Append the new day's data to the MasterGas file
master_file = "CountyPrices/MasterGas.csv"

if os.path.exists(master_file):
    master_df = pd.read_csv(master_file)
    master_df = pd.concat([master_df, final_df], ignore_index=True)
else:
    master_df = final_df

master_df.to_csv(master_file, index=False)

