import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
import re
import matplotlib.pyplot as plt
import matplotlib

# Custom theme for matplotlib
jared_theme = {
    'axes.grid': True,
    'grid.linestyle': '-',
    'legend.framealpha': 1,
    'legend.facecolor': 'white',
    'legend.shadow': True,
    'legend.fontsize': 14,
    'legend.title_fontsize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'axes.labelsize': 16,
    'axes.titlesize': 20,
    'figure.dpi': 100,
    'axes.facecolor': 'white',
    'figure.figsize': (10, 8)
}

# Apply the theme to matplotlib
matplotlib.rcParams.update(jared_theme)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}

TIME_MAPPING = {
    "Current Avg.": datetime.now().date().strftime('%Y-%m-%d'),
    "Yesterday Avg.": (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d'),
    "Week Ago Avg.": (datetime.now().date() - timedelta(weeks=1)).strftime('%Y-%m-%d'),
    "Month Ago Avg.": (datetime.now().date() - relativedelta(months=1)).strftime('%Y-%m-%d'),
    "Year Ago Avg.": (datetime.now().date() - relativedelta(years=1)).strftime('%Y-%m-%d'),
}


def deduplicate_and_sort(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["State", "City", "Date"])
    return df.sort_values(by=["Date", "State", "City"], ascending=[True, True, True])


def update_master_file(new_data: pd.DataFrame, file_path: str) -> pd.DataFrame:
    """
    Concatenate new data with existing data in the specified file,
    and remove duplicates based on 'State', 'City', and 'Date'.
    """
    if os.path.exists(file_path):
        # Load existing data
        existing_data = pd.read_csv(file_path)
    else:
        # If no existing file, just use the new data
        existing_data = pd.DataFrame()

    # Concatenate new data with existing data
    combined_data = pd.concat([existing_data, new_data], ignore_index=True)

    # Deduplicate and sort the data
    return deduplicate_and_sort(combined_data)


def scrape_state_urls() -> list:
    url = "https://gasprices.aaa.com/state-gas-price-averages/"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    table = BeautifulSoup(response.text, "html.parser").select_one("#sortable")
    return [a["href"] for a in table.find_all("a", href=True)]


def get_state_name_from_html(html: str) -> str:
    match = re.search(r"AAA\s(.*?)\sAvg", html)
    return match.group(1) if match else None

def parse_accordion_table(soup: BeautifulSoup, state_name: str) -> pd.DataFrame:
    accordion = soup.select(".accordion-prices > h3, .accordion-prices > div")
    data, current_city = [], None

    for element in accordion:
        if element.name == "h3":
            current_city = element.get_text(strip=True)
        elif element.name == "div":
            table = element.select_one("table.table-mob tbody")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    category = cells[0].get_text(strip=True)
                    # Get the date from TIME_MAPPING which will now be in 'YYYY-MM-DD' format
                    date = TIME_MAPPING.get(category, category)

                    # Append raw row data
                    row_data = [state_name, current_city, date] + [
                        cells[i].get_text(strip=True) if i < len(cells) else None
                        for i in range(1, 5)
                    ]
                    data.append(row_data)

    # Create DataFrame
    df = pd.DataFrame(data, columns=["State", "City", "Date", "Regular", "Mid", "Premium", "Diesel"])

    return df



def get_accordion_table(url: str) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    state_name = get_state_name_from_html(str(soup))
    return parse_accordion_table(soup, state_name)


def remove_dollar_signs(df):
    # Identify the last four columns
    last_four_cols = df.columns[-4:]

    # Remove dollar signs and convert to numeric
    df[last_four_cols] = df[last_four_cols].replace({r'\$': ''}, regex=True).apply(pd.to_numeric)

    return df


def get_all_state_data() -> pd.DataFrame:
    state_urls = scrape_state_urls()
    all_data = [get_accordion_table(url) for url in state_urls if url]
    combined_df = deduplicate_and_sort(pd.concat(all_data, ignore_index=True))

    # Remove dollar signs from the price columns
    return remove_dollar_signs(combined_df)


def plot_city_gas_prices(master_df: pd.DataFrame, cities: list, output_file: str):
    master_df["Date"] = pd.to_datetime(master_df["Date"])

    city_styles = {
        "Atlanta": {"color": "#C8102E"},
        "Metro Detroit": {"color": "#0076B6"},
    }

    plt.figure(figsize=(10, 6))

    for city, style in city_styles.items():
        if city in cities:
            city_data = master_df[master_df["City"] == city]
            plt.plot(
                city_data["Date"],
                city_data["Regular"],
                label=city,
                color=style["color"],
            )

    plt.title("Gas Prices for Detroit and Atlanta", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Price (USD)", fontsize=14)
    plt.legend(title="Cities", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()