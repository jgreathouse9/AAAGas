import logging
import requests
import re
import pandas as pd
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("gas_prices.log"),  # Log to a file
        logging.StreamHandler(),  # Also print to the console
    ],
)


# Function to fetch state abbreviations
def get_state_abbreviations(
    url="https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv",
):
    logging.info("Fetching state abbreviations.")
    states_df = pd.read_csv(url)
    logging.info("State abbreviations successfully fetched.")
    return dict(zip(states_df["State"], states_df["Abbreviation"]))


# Function to process gas prices
def process_gas_prices(
    state_abbreviations, base_url="https://gasprices.aaa.com/", headers=None
):
    today = datetime.now().strftime("%Y-%m-%d")

    if headers is None:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

    state_data = []

    logging.info("Starting to process states for gas prices.")
    for state, abbreviation in state_abbreviations.items():
        try:
            # Fetch map_id for the state
            logging.info(f"Processing state: {state} ({abbreviation})")
            response = requests.get(
                base_url, params={"state": abbreviation}, headers=headers
            )
            response.raise_for_status()
            map_id_match = re.search(r"map_id=(\d+)", response.text)
            map_id = map_id_match.group(1) if map_id_match else None

            if not map_id:
                logging.warning(f"No map_id found for {state}. Skipping.")
                continue

            # Fetch gas price data for the map_id
            request_url = f"https://gasprices.aaa.com/index.php?premiumhtml5map_js_data=true&map_id={map_id}&r=64141&ver=6.6.1"
            response = requests.get(request_url, headers=headers)
            response.raise_for_status()
            map_data_match = re.search(
                r"map_data\s*:\s*({.*?})\s*,\s*groups", response.text, re.DOTALL
            )

            if not map_data_match:
                logging.warning(f"No map_data found for {state}. Skipping.")
                continue

            # Parse map_data
            map_data = json.loads(map_data_match.group(1))
            for item in map_data.values():
                state_data.append(
                    {
                        "state": state,
                        "abbreviation": abbreviation,
                        "name": item.get("name"),
                        "price": item.get("comment"),
                        "date": today,
                    }
                )

        except requests.RequestException as e:
            logging.error(f"Request error for {state}: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error for {state}: {e}")

    logging.info("Finished processing all states.")
    return pd.DataFrame(state_data)
