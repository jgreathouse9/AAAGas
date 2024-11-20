from countyscraper import get_all_state_data, plot_city_gas_prices
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

print(datetime.now().date())
p
# Get live gas price data
master_df = get_all_state_data()

# Save data to a CSV file
live_scrape_path = 'CountyPrices/LiveScrape.csv'
master_df.to_csv(live_scrape_path, index=False)

print(f"Live scrape data saved to {live_scrape_path}")
