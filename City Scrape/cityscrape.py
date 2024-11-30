from cityutils import

# URL of the CSV file
url = "https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"

# Read the CSV into a DataFrame
states_df = pd.read_csv(url)

# Create a dictionary mapping state names to abbreviations
state_abbreviations = dict(zip(states_df['State'], states_df['Abbreviation']))

df = fetch_gas_prices(state_abbreviations)
