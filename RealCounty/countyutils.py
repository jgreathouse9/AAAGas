import requests
import re
import pandas as pd
import json
from datetime import datetime


# Function to fetch state abbreviations
def get_state_abbreviations(url="https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"):
    states_df = pd.read_csv(url)
    return dict(zip(states_df['State'], states_df['Abbreviation']))


# Function to fetch gas prices for all states and return as a DataFrame
def get_gas_prices(state_abbreviations, base_url='https://gasprices.aaa.com/', headers=None):
    today = datetime.now().strftime('%Y-%m-%d')

    # Default headers
    if headers is None:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

    state_data = []

    # Process each state
    for state, abbreviation in state_abbreviations.items():
        try:
            # Fetch map_id for the state
            response = requests.get(base_url, params={'state': abbreviation}, headers=headers)
            response.raise_for_status()
            map_id_match = re.search(r'map_id=(\d+)', response.text)
            map_id = map_id_match.group(1) if map_id_match else None

            if not map_id:
                print(f"No map_id found for {state}. Skipping...")
                continue

            # Fetch gas prices using the map_id
            data_url = f"https://gasprices.aaa.com/index.php?premiumhtml5map_js_data=true&map_id={map_id}"
            response = requests.get(data_url, headers=headers)
            response.raise_for_status()

            # Extract map_data
            map_data_match = re.search(r'map_data\s*:\s*({.*?})\s*,\s*groups', response.text, re.DOTALL)
            if not map_data_match:
                print(f"No 'map_data' section found for {state}.")
                continue

            map_data = json.loads(map_data_match.group(1))

            # Simplify and collect data using map
            state_data.extend(
                map(
                    lambda item: {
                        'state': state,
                        'abbreviation': abbreviation,
                        'name': item.get('name'),
                        'price': item.get('comment'),
                        'date': today
                    },
                    map_data.values()
                )
            )

        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error processing {state}: {e}")

    # Convert data to a DataFrame
    return pd.DataFrame(state_data)
