import requests
import re
import pandas as pd
import json
from datetime import datetime

# 1. Fetch state abbreviations
def get_state_abbreviations(
        url="https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"):
    """
    Fetches state names and their abbreviations from a CSV file.

    Args:
        url (str): URL to the CSV containing state names and abbreviations.

    Returns:
        dict: A dictionary mapping state names to their abbreviations.
    """
    states_df = pd.read_csv(url)
    return dict(zip(states_df['State'], states_df['Abbreviation']))

# 2. Fetch gas price data for a single state
def fetch_state_data(state, abbreviation, base_url, headers, today):
    """
    Fetch gas price data for a single state.

    Args:
        state (str): Full state name.
        abbreviation (str): State abbreviation.
        base_url (str): Base URL for fetching map_id.
        headers (dict): HTTP headers for requests.
        today (str): Current date.

    Returns:
        list: Simplified gas price data for the state.
    """
    state_data = []
    try:
        # Fetch map_id for the state
        response = requests.get(base_url, params={'state': abbreviation}, headers=headers)
        response.raise_for_status()
        map_id_match = re.search(r'map_id=(\d+)', response.text)
        map_id = map_id_match.group(1) if map_id_match else None

        if not map_id:
            print(f"No map_id found for {state}. Skipping...")
            return state_data

        # Fetch gas prices using the map_id
        data_url = f"https://gasprices.aaa.com/index.php?premiumhtml5map_js_data=true&map_id={map_id}"
        response = requests.get(data_url, headers=headers)
        response.raise_for_status()

        # Extract map_data
        map_data_match = re.search(r'map_data\s*:\s*({.*?})\s*,\s*groups', response.text, re.DOTALL)
        if not map_data_match:
            print(f"No 'map_data' section found for {state}.")
            return state_data

        map_data = json.loads(map_data_match.group(1))

        # Simplify and collect data
        state_data = [
            {
                'state': state,
                'abbreviation': abbreviation,
                'name': item.get('name'),
                'price': item.get('comment'),
                'date': today
            }
            for item in map_data.values()
        ]

    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error processing {state}: {e}")

    return state_data

# 3. Fetch gas prices for all states using mapping
def fetch_all_states(state_abbreviations, base_url, headers):
    """
    Fetch gas price data for all states using the mapping approach.

    Args:
        state_abbreviations (dict): Mapping of state names to abbreviations.
        base_url (str): Base URL for fetching map_ids and gas prices.
        headers (dict): HTTP headers for requests.

    Returns:
        list: Flattened list of all state gas price data.
    """
    today = datetime.now().strftime('%Y-%m-%d')

    # Use map to process each state
    state_data = list(
        map(
            lambda state_info: fetch_state_data(
                state=state_info[0],
                abbreviation=state_info[1],
                base_url=base_url,
                headers=headers,
                today=today
            ),
            state_abbreviations.items()
        )
    )

    # Flatten the list of lists
    return [item for sublist in state_data for item in sublist]

# 4. Convert state data into a DataFrame
def get_gas_prices(state_abbreviations, base_url='https://gasprices.aaa.com/', headers=None):
    """
    Fetches gas prices for all states and returns the data as a DataFrame.

    Args:
        state_abbreviations (dict): Mapping of state names to abbreviations.
        base_url (str): Base URL for fetching data.
        headers (dict): HTTP headers for requests.

    Returns:
        DataFrame: A pandas DataFrame containing gas price data for all states.
    """
    if headers is None:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

    # Fetch gas price data for all states
    state_data = fetch_all_states(state_abbreviations, base_url, headers)

    # Convert data into a pandas DataFrame
    return pd.DataFrame(state_data)
