from cityscraper import scrape_all_counties
import os
import pandas as pd
from datetime import datetime

# Scrape data
df = scrape_all_counties()

# Add today's date
today_date = datetime.now().strftime('%Y-%m-%d')
df['Date'] = today_date

# File path
file_path = "RealCounty/RealCounty.csv"

# Ensure the directory exists
os.makedirs(os.path.dirname(file_path), exist_ok=True)

# Append or create the file
try:
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df.to_csv(file_path, index=False)
    else:
        df.to_csv(file_path, index=False)
except Exception as e:
    print(f"Error writing to {file_path}: {e}")
