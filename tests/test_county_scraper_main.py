import runpy
import sys
import types
from pathlib import Path

import pandas as pd

MAIN = str(Path(__file__).resolve().parents[1] / "RealCounty" / "county_scraper_main.py")


def run_main(monkeypatch, tmp_path, process_gas_prices):
    """Run the county scraper script in tmp_path with countyutils replaced by a stub."""
    stub = types.ModuleType("countyutils")
    stub.get_state_abbreviations = lambda: {"Alabama": "AL"}
    stub.process_gas_prices = process_gas_prices
    monkeypatch.setitem(sys.modules, "countyutils", stub)
    monkeypatch.chdir(tmp_path)
    runpy.run_path(MAIN)
    return sorted((tmp_path / "RealCounty" / "Data").glob("CountyGas*.csv"))


def test_writes_the_days_prices_to_csv(monkeypatch, tmp_path):
    rows = pd.DataFrame([{"state": "Alabama", "abbreviation": "AL", "name": "Autauga", "price": "$3.10", "date": "2026-10-21"}])

    files = run_main(monkeypatch, tmp_path, lambda states: rows)

    assert len(files) == 1
    pd.testing.assert_frame_equal(pd.read_csv(files[0]), rows)


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
