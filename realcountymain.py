import requests
import re
import pandas as pd
import json
from datetime import datetime


# Function to fetch state abbreviations
def get_state_abbreviations(
        url="https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"):
    # Read the CSV into a DataFrame and map state names to abbreviations
    states_df = pd.read_csv(url)
    return dict(zip(states_df['State'], states_df['Abbreviation']))


# Function to fetch gas prices for all states and return as a DataFrame
def get_gas_prices(state_abbreviations, base_url='https://gasprices.aaa.com/', headers=None):
    # Use the current date for indexing
    today = datetime.now().strftime('%Y-%m-%d')

    if headers is None:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

    # Initialize a list to collect state price data
    state_data = []

    # Loop through state abbreviations and update with map_id
    for state, abbreviation in state_abbreviations.items():
        params = {'state': abbreviation}
        response = requests.get(base_url, params=params, headers=headers)
        resptext = response.text

        # Extract unique map_id from the response
        map_id_matches = re.findall(r'map_id=(\d+)', resptext)
        unique_map_ids = list(set(map_id_matches))

        # Update the dictionary with the map_id (use first if multiple found)
        state_abbreviations[state] = {
            'abbreviation': abbreviation,
            'map_id': unique_map_ids[0] if unique_map_ids else None,
            'prices': {}
        }

    # Loop through all states and their map_ids to fetch prices
    for state, info in state_abbreviations.items():
        map_id = info.get('map_id')

        if map_id:
            # Construct the request URL for the state with the current map_id
            request_url = f"https://gasprices.aaa.com/index.php?premiumhtml5map_js_data=true&map_id={map_id}&r=64141&ver=6.6.1"

            # Send the request
            response = requests.get(request_url, headers=headers)
            resptext = response.text

            # Extract the 'map_data' section using regex
            map_data_match = re.search(r'map_data\s*:\s*({.*?})\s*,\s*groups', resptext, re.DOTALL)
            if map_data_match:
                map_data_str = map_data_match.group(1)

                try:
                    # Convert the JSON-like string into a dictionary
                    map_data = json.loads(map_data_str)

                    # Simplify the data to include only name and price (comment)
                    simplified_data = [
                        {'name': data['name'], 'price': data['comment']}
                        for data in map_data.values()
                    ]

                    # Add data to the state data list
                    for entry in simplified_data:
                        state_data.append({
                            'state': state,
                            'abbreviation': info['abbreviation'],
                            'name': entry['name'],
                            'price': entry['price'],
                            'date': today
                        })

                    print(f"Updated state_abbreviations for {state}.")

                except json.JSONDecodeError as e:
                    print(f"Error decoding map_data for {state}: {e}")
            else:
                print(f"Could not find 'map_data' section for {state}.")
        else:
            print(f"No valid map_id found for {state}.")

    # Convert the state data list into a DataFrame
    df = pd.DataFrame(state_data)

    return df


# Fetch gas prices and return as a DataFrame
gas_prices_df = get_gas_prices(get_state_abbreviations())


