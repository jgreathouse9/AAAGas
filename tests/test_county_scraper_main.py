"""county_scraper_main.py: run the scrape and save the day's file."""

import runpy
import sys
import types
from datetime import datetime
from pathlib import Path

import pandas as pd

MAIN = str(Path(__file__).resolve().parents[1] / "RealCounty" / "county_scraper_main.py")
ROWS = pd.DataFrame([{"state": "Alabama", "abbreviation": "AL", "name": "Autauga", "price": "$3.10", "date": "2026-10-21"}])


def run_main(monkeypatch, tmp_path, process_gas_prices):
    """Run the script in tmp_path with countyutils replaced by a stub; return the CSVs it left behind."""
    stub = types.ModuleType("countyutils")
    stub.get_state_abbreviations = lambda: {"Alabama": "AL"}
    stub.process_gas_prices = process_gas_prices
    monkeypatch.setitem(sys.modules, "countyutils", stub)
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MAIN)
    return sorted((tmp_path / "RealCounty" / "Data").glob("*.csv"))


# Smoke


def test_saves_the_scraped_rows_without_an_index_column(monkeypatch, tmp_path):
    files = run_main(monkeypatch, tmp_path, lambda states: ROWS)

    assert len(files) == 1
    pd.testing.assert_frame_equal(pd.read_csv(files[0]), ROWS)


# Unit


def test_names_the_file_after_the_day_it_was_scraped(monkeypatch, tmp_path):
    before = datetime.now().strftime("%Y-%m-%d")
    files = run_main(monkeypatch, tmp_path, lambda states: ROWS)
    after = datetime.now().strftime("%Y-%m-%d")

    assert [f.name for f in files] in ([f"CountyGas{before}.csv"], [f"CountyGas{after}.csv"])


def test_scrapes_the_states_from_the_state_list(monkeypatch, tmp_path):
    seen = []

    def record(states):
        seen.append(states)
        return ROWS

    run_main(monkeypatch, tmp_path, record)

    assert seen == [{"Alabama": "AL"}]


# Edge


def test_keeps_earlier_days_files(monkeypatch, tmp_path):
    data = tmp_path / "RealCounty" / "Data"
    data.mkdir(parents=True)
    (data / "CountyGas2026-10-20.csv").write_text("yesterday")

    files = run_main(monkeypatch, tmp_path, lambda states: ROWS)

    assert len(files) == 2
    assert (data / "CountyGas2026-10-20.csv").read_text() == "yesterday"


# Failure


def test_does_not_write_a_csv_when_nothing_was_scraped(monkeypatch, tmp_path, caplog):
    files = run_main(monkeypatch, tmp_path, lambda states: pd.DataFrame())

    assert files == []
    assert "No gas price data was fetched for any state" in caplog.text


def test_logs_errors_instead_of_crashing(monkeypatch, tmp_path, caplog):
    def broken(states):
        raise RuntimeError("AAA changed its page layout")

    files = run_main(monkeypatch, tmp_path, broken)

    assert files == []
    assert "AAA changed its page layout" in caplog.text
