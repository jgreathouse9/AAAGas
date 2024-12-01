from countyutils import get_state_abbreviations, get_gas_prices
import os
import pandas as pd
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")

df = get_gas_prices(get_state_abbreviations())

directory = "./RealCounty/Data"
if not os.path.exists(directory):
    os.makedirs(directory)

filename = f"{directory}/CountyGas{today}.csv"
df.to_csv(filename, index=False)
