# Import the get_all_state_data function from countyscraper.py
from countyscraper import get_all_state_data

# Call the function to get all state data
final_df = get_all_state_data()


print(final_df)
p
# Optionally, save the final dataset to a CSV file
final_df.to_csv("all_state_gas_prices.csv", index=False)
