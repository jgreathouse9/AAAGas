# THESE ARE THE REAL COUNTY VALUES, the other ones are are the city.

from cityscraper import scrape_all_counties


all_gas_prices = scrape_all_counties()


# Convert the list of dictionaries to a pandas DataFrame
df = pd.DataFrame(all_prices)

# Ensure the directory exists
directory = "/RealCounty"
if not os.path.exists(directory):
    os.makedirs(directory)

# Save the DataFrame to a CSV file in the specified directory
csv_file_path = os.path.join(directory, "RealCounty.csv")
df.to_csv(csv_file_path, index=False)
