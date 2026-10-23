"""get_state_abbreviations(): the state list that decides what gets scraped, and in what order."""

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

import countyutils


def write_states(path, rows, columns=("State", "Abbreviation")):
    pd.DataFrame(rows, columns=list(columns)).to_csv(path, index=False)
    return str(path)


# Smoke


def test_maps_each_state_to_its_abbreviation(tmp_path):
    url = write_states(tmp_path / "states.csv", [("Alabama", "AL"), ("Alaska", "AK")])

    assert countyutils.get_state_abbreviations(url) == {"Alabama": "AL", "Alaska": "AK"}


# Unit

state_name = st.text(st.characters(whitelist_categories=("Lu", "Ll"), whitelist_characters=" "), min_size=1, max_size=20).map(str.strip).filter(bool)
abbreviation = st.text(st.characters(min_codepoint=ord("A"), max_codepoint=ord("Z")), min_size=2, max_size=2)


@pytest.mark.parametrize("name,abbr", [("NULL", "NU"), ("None", "NO"), ("Nevada", "NA"), ("Nowhere", "N/A")])
def test_names_pandas_treats_as_missing_are_kept_as_text(tmp_path, name, abbr):
    url = write_states(tmp_path / "states.csv", [(name, abbr)])

    assert countyutils.get_state_abbreviations(url) == {name: abbr}


@given(pairs=st.lists(st.tuples(state_name, abbreviation), unique_by=lambda p: p[0], max_size=60))
def test_keeps_every_state_in_file_order(pairs, tmp_path_factory):
    url = write_states(tmp_path_factory.mktemp("states") / "states.csv", pairs)

    result = countyutils.get_state_abbreviations(url)

    assert list(result.items()) == pairs


# Failure


def test_a_file_without_the_expected_columns_is_an_error(tmp_path):
    url = write_states(tmp_path / "states.csv", [("Alabama", "AL")], columns=("Name", "Code"))

    with pytest.raises(KeyError):
        countyutils.get_state_abbreviations(url)
