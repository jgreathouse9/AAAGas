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
    "Current Avg.": datetime.now().date(),
    "Yesterday Avg.": datetime.now().date() - timedelta(days=1),
    "Week Ago Avg.": datetime.now().date() - timedelta(weeks=1),
    "Month Ago Avg.": datetime.now().date() - relativedelta(months=1),
    "Year Ago Avg.": datetime.now().date() - relativedelta(years=1),
}

def deduplicate_and_sort(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["State", "City", "Date"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values(by=["State", "City", "Date"], ascending=[True, True, True])

def update_master_file(new_data: pd.DataFrame, file_path: str) -> pd.DataFrame:
    """
    Concatenate new data with existing data in the specified file,
    and remove duplicates based on 'State', 'City', and 'Date'.
    """
    if os.path.exists(file_path):
        # Load existing data
        existing_data = pd.read_csv(file_path)
        
        # Ensure datetime columns are parsed correctly
        existing_data["Date"] = pd.to_datetime(existing_data["Date"])
    else:
        # If no existing file, just use the new data
        existing_data = pd.DataFrame()

    # Deduplicate new data based on 'State', 'City', and 'Date' before merging
    new_data["Date"] = pd.to_datetime(new_data["Date"])  # Ensure the 'Date' column is in datetime format
    new_data = new_data.drop_duplicates(subset=["State", "City", "Date"])

    # Concatenate new data with existing data
    combined_data = pd.concat([existing_data, new_data], ignore_index=True)

    # Remove duplicates based on 'State', 'City', and 'Date' from the combined data
    deduplicated_data = combined_data.drop_duplicates(subset=["State", "City", "Date"])

    # Sort the DataFrame by 'State', 'City', and 'Date'
    deduplicated_data = deduplicated_data.sort_values(by=["State", "City", "Date"], ascending=[True, True, True])

    return deduplicated_data


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
                    date = TIME_MAPPING.get(category, category)
                    row_data = [state_name, current_city, date] + [td.get_text(strip=True) for td in cells[1:]]
                    data.append(row_data)
    return pd.DataFrame(data, columns=["State", "City", "Date", "Regular", "Mid", "Premium", "Diesel"])

def get_accordion_table(url: str) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    state_name = get_state_name_from_html(str(soup))
    return parse_accordion_table(soup, state_name)

def get_all_state_data() -> pd.DataFrame:
    state_urls = scrape_state_urls()
    all_data = [get_accordion_table(url) for url in state_urls if url]
    return deduplicate_and_sort(pd.concat(all_data, ignore_index=True))


def plot_city_gas_prices(master_df: pd.DataFrame, cities: list, output_file: str):
    master_df["Date"] = pd.to_datetime(master_df["Date"])

    city_styles = {
        "Atlanta": {"color": "#C8102E", "marker": "D", "mfc": "#00f0ff"},
        "Metro Detroit": {"color": "#0076B6", "marker": "D", "mfc": "black"},
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
                marker=style["marker"],
                markersize=5,
                mfc=style["mfc"],
                mec="black",
            )

    plt.title("Gas Prices for Selected Cities", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Price (USD)", fontsize=14)
    plt.legend(title="Cities", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
