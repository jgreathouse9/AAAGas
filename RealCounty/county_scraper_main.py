from countyutils import get_state_abbreviations, get_gas_prices


# Fetch gas prices and return as a DataFrame
gas_prices_df = get_gas_prices(get_state_abbreviations())
