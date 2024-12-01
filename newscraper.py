import requests
from bs4 import BeautifulSoup
import pandas as pd
from dateutil.relativedelta import relativedelta  # For precise relative deltas

# URL of the CSV file
url = "https://raw.githubusercontent.com/jasonong/List-of-US-States/refs/heads/master/states.csv"

# Read the CSV into a DataFrame
states_df = pd.read_csv(url)

# Create a dictionary mapping state names to abbreviations
state_abbreviations = dict(zip(states_df["State"], states_df["Abbreviation"]))


def fetch_gas_prices(state_abbreviations):
    """Fetch and process gas prices for all states."""
    # Define headers
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    # Initialize an empty DataFrame to hold all data
    all_data = pd.DataFrame(
        columns=["Date", "State", "City", "Regular", "Mid-Grade", "Premium", "Diesel"]
    )

    # Time mapping for relative deltas using relativedelta
    today = pd.Timestamp.today()
    time_mapping = {
        "Current Avg.": lambda: today,
        "Yesterday Avg.": lambda: today - pd.Timedelta(days=1),
        "Week Ago Avg.": lambda: today - pd.Timedelta(weeks=1),
        "Month Ago Avg.": lambda: today - relativedelta(months=1),
        "Year Ago Avg.": lambda: today - relativedelta(years=1),
    }

    # Iterate over each state abbreviation
    for state, abbreviation in state_abbreviations.items():
        params = {"state": abbreviation}
        response = requests.get(
            "https://gasprices.aaa.com/", params=params, headers=headers
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract city sections
        cities = soup.select(".accordion-prices.metros-js > h3[data-title]")

        # Extract data using list comprehensions
        data = [
            [
                # Calculate date using time_mapping
                time_mapping.get(
                    row.find_all("td")[0].get_text(strip=True), lambda: today
                )().strftime("%Y-%d-%m"),
                state,
                city.get_text(strip=True),
                *[
                    cell.get_text(strip=True).replace("$", "")
                    for cell in row.find_all("td")[1:]
                ],
            ]
            for city in cities
            for row in city.find_next("table").select("tbody tr")
        ]

        # Create a DataFrame for the current state
        state_df = pd.DataFrame(
            data,
            columns=[
                "Date",
                "State",
                "City",
                "Regular",
                "Mid-Grade",
                "Premium",
                "Diesel",
            ],
        )

        # Append to the all_data DataFrame
        all_data = pd.concat([all_data, state_df], ignore_index=True)

    # Convert 'Date' to datetime
    all_data["Date"] = pd.to_datetime(all_data["Date"], format="%Y-%d-%m")

    # Sort by 'State', 'City', and 'Date'
    all_data = all_data.sort_values(by=["State", "City", "Date"]).reset_index(drop=True)

    return all_data


# Example usage
df = fetch_gas_prices(state_abbreviations)
print(df.head())
