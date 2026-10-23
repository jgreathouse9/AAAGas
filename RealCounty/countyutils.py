import logging
import requests
import re
import time
import pandas as pd
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("gas_prices.log"),  # Log to a file
        logging.StreamHandler()  # Also print to the console
    ]
)

# Statuses worth retrying: AAA answers bursts of requests with 429 Too Many Requests
RETRY_STATUSES = {429, 500, 502, 503, 504}

# Function to fetch state abbreviations
def get_state_abbreviations(
        url="https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"):
    logging.info("Fetching state abbreviations.")
    # keep_default_na=False: otherwise a name like "NA" or "NULL" is read as a missing value
    states_df = pd.read_csv(url, keep_default_na=False)
    logging.info("State abbreviations successfully fetched.")
    return dict(zip(states_df['State'], states_df['Abbreviation']))

# GET a URL, waiting and retrying when the server says to slow down
def fetch(session, url, params=None, retries=5, backoff=10, max_wait=60):
    if retries < 1:
        raise ValueError(f"retries must be at least 1, got {retries}")
    for attempt in range(1, retries + 1):  # pragma: no branch - the last attempt always returns or raises
        response = session.get(url, params=params, timeout=30)
        if response.status_code not in RETRY_STATUSES or attempt == retries:
            response.raise_for_status()
            return response

        # Honor Retry-After when given in seconds, otherwise back off exponentially. Each wait is
        # capped so a long Retry-After can't push the run past GitHub's 6-hour job limit.
        retry_after = response.headers.get('Retry-After', '')
        wait = int(retry_after) if retry_after.isdigit() else backoff * 2 ** (attempt - 1)
        wait = min(wait, max_wait)
        logging.warning(f"{response.status_code} for {response.url}; retrying in {wait}s (attempt {attempt}/{retries}).")
        time.sleep(wait)

# Function to process gas prices
def process_gas_prices(state_abbreviations, base_url='https://gasprices.aaa.com/', headers=None, delay=2):
    today = datetime.now().strftime('%Y-%m-%d')

    if headers is None:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

    session = requests.Session()
    session.headers.update(headers)

    state_data = []
    missing_states = []

    logging.info("Starting to process states for gas prices.")
    for state, abbreviation in state_abbreviations.items():
        rows_before = len(state_data)
        try:
            # Fetch map_id for the state
            response = fetch(session, base_url, params={'state': abbreviation})
            map_id_match = re.search(r'map_id=(\d+)', response.text)
            map_id = map_id_match.group(1) if map_id_match else None

            if not map_id:
                logging.warning(f"No map_id found for {state}. Skipping.")
                continue

            # Pause between requests so AAA doesn't rate limit the run
            time.sleep(delay)

            # Fetch gas price data for the map_id
            response = fetch(session, f"{base_url}index.php", params={
                'premiumhtml5map_js_data': 'true', 'map_id': map_id, 'r': 64141, 'ver': '6.6.1'})
            map_data_match = re.search(r'map_data\s*:\s*({.*?})\s*,\s*groups', response.text, re.DOTALL)

            if not map_data_match:
                logging.warning(f"No map_data found for {state}. Skipping.")
                continue

            # Parse map_data
            map_data = json.loads(map_data_match.group(1))
            for item in map_data.values():
                state_data.append({
                    'state': state,
                    'abbreviation': abbreviation,
                    'name': item.get('name'),
                    'price': item.get('comment'),
                    'date': today
                })

        except requests.RequestException as e:
            logging.error(f"Request error for {state}: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error for {state}: {e}")
        finally:
            if len(state_data) == rows_before:
                missing_states.append(state)
            time.sleep(delay)

    if missing_states:
        logging.warning(f"No data for {len(missing_states)} of {len(state_abbreviations)} states: {', '.join(missing_states)}")
    logging.info("Finished processing all states.")
    return pd.DataFrame(state_data)
