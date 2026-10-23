"""process_gas_prices(): scrape every state's county prices into one DataFrame."""

from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

import countyutils
from helpers import FakeAAA, captured_logs, make_response, map_data, map_page

TODAY = "2026-10-21"


class FixedDatetime:
    @staticmethod
    def now():
        return datetime(2026, 10, 21, 13, 0)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(countyutils, "datetime", FixedDatetime)


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(countyutils.time, "sleep", calls.append)
    return calls


@pytest.fixture
def use_session(monkeypatch):
    def install(session):
        monkeypatch.setattr(countyutils.requests, "Session", lambda: session)
        return session

    return install


def row(state, abbr, name, price):
    return {"state": state, "abbreviation": abbr, "name": name, "price": price, "date": TODAY}


# Smoke


def test_returns_a_row_per_county(sleeps, use_session):
    use_session(FakeAAA(
        pages={"AL": [make_response(200, map_page(1))], "AK": [make_response(200, map_page(2))]},
        map_data={"1": map_data([("Autauga", "$3.10"), ("Baldwin", "$3.20")]), "2": map_data([("Juneau", "$4.50")])},
    ))

    df = countyutils.process_gas_prices({"Alabama": "AL", "Alaska": "AK"}, delay=0)

    assert df.to_dict("records") == [
        row("Alabama", "AL", "Autauga", "$3.10"),
        row("Alabama", "AL", "Baldwin", "$3.20"),
        row("Alaska", "AK", "Juneau", "$4.50"),
    ]


# Unit


def test_requests_the_map_data_for_the_states_own_map_id(sleeps, use_session):
    session = use_session(FakeAAA(pages={"RI": [make_response(200, map_page(41))]},
                                  map_data={"41": map_data([("Kent", "$3.10")])}))

    countyutils.process_gas_prices({"Rhode Island": "RI"}, delay=0)

    assert session.calls[0]["params"] == {"state": "RI"}
    assert session.calls[1]["url"] == "https://gasprices.aaa.com/index.php"
    assert session.calls[1]["params"]["map_id"] == "41"
    assert session.calls[1]["params"]["premiumhtml5map_js_data"] == "true"


def test_sends_a_browser_user_agent_by_default(sleeps, use_session):
    session = use_session(FakeAAA(pages={"AL": [make_response(403)]}, map_data={}))

    countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)

    assert session.headers["user-agent"].startswith("Mozilla/5.0")


def test_sends_caller_supplied_headers(sleeps, use_session):
    session = use_session(FakeAAA(pages={"AL": [make_response(403)]}, map_data={}))

    countyutils.process_gas_prices({"Alabama": "AL"}, headers={"user-agent": "test-agent"}, delay=0)

    assert session.headers == {"user-agent": "test-agent"}


def test_pauses_after_every_request(sleeps, use_session):
    use_session(FakeAAA(
        pages={"AL": [make_response(200, map_page(1))], "AK": [make_response(200, map_page(2))]},
        map_data={"1": map_data([("Autauga", "$3.10")]), "2": map_data([("Juneau", "$4.50")])},
    ))

    countyutils.process_gas_prices({"Alabama": "AL", "Alaska": "AK"}, delay=1.5)

    assert sleeps == [1.5] * 4


# Each state's outcome on the site, and how many requests it takes to reach it
county = st.tuples(
    st.text(st.characters(whitelist_categories=("Lu", "Ll"), whitelist_characters=" .'-"), min_size=1, max_size=20),
    st.one_of(st.none(), st.decimals(1, 9, places=3).map(lambda d: f"${d}")),
)
outcome = st.one_of(
    st.tuples(st.just("ok"), st.lists(county, min_size=1, max_size=4)),
    st.just(("empty map",)),
    st.just(("no map id",)),
    st.just(("bad json",)),
    st.just(("no map data",)),
    st.tuples(st.just("http error"), st.sampled_from([400, 401, 403, 404, 410])),
)
REQUESTS = {"ok": 2, "empty map": 2, "bad json": 2, "no map data": 2, "no map id": 1, "http error": 1}


def fake_site(outcomes):
    pages, data = {}, {}
    for i, (kind, *detail) in enumerate(outcomes):
        abbr, map_id = f"S{i}", str(i + 1)
        if kind == "no map id":
            pages[abbr] = [make_response(200, "<html>no map on this page</html>")]
        elif kind == "http error":
            pages[abbr] = [make_response(detail[0])]
        else:
            pages[abbr] = [make_response(200, map_page(map_id))]
            data[map_id] = {
                "ok": map_data(detail[0]) if detail else "",
                "empty map": map_data([]),
                "bad json": "map_data: {not json}, groups",
                "no map data": "var unrelated = 1;",
            }[kind]
    return FakeAAA(pages, data)


@given(outcomes=st.lists(outcome, max_size=6))
def test_rows_pauses_and_report_follow_each_states_outcome(outcomes):
    states = {f"State{i}": f"S{i}" for i in range(len(outcomes))}
    session = fake_site(outcomes)
    slept = []
    with pytest.MonkeyPatch.context() as mp, captured_logs() as logs:
        mp.setattr(countyutils, "datetime", FixedDatetime)
        mp.setattr(countyutils.time, "sleep", slept.append)
        mp.setattr(countyutils.requests, "Session", lambda: session)
        df = countyutils.process_gas_prices(states, delay=0.25)

    expected_rows = [row(f"State{i}", f"S{i}", name, price)
                     for i, (kind, *detail) in enumerate(outcomes) if kind == "ok"
                     for name, price in detail[0]]
    assert df.to_dict("records") == expected_rows

    requests_made = sum(REQUESTS[kind] for kind, *_ in outcomes)
    assert len(session.calls) == requests_made
    assert slept == [0.25] * requests_made

    missing = [f"State{i}" for i, (kind, *_) in enumerate(outcomes) if kind != "ok"]
    summaries = [m for m in logs if m.startswith("No data for")]
    if missing:
        assert summaries == [f"No data for {len(missing)} of {len(outcomes)} states: {', '.join(missing)}"]
    else:
        assert summaries == []


@given(rate_limited=st.integers(0, 4))
def test_a_state_rate_limited_fewer_times_than_the_retry_limit_is_still_scraped(rate_limited):
    pages = [make_response(429, headers={"Retry-After": "1"})] * rate_limited + [make_response(200, map_page(1))]
    session = FakeAAA({"AL": pages}, {"1": map_data([("Autauga", "$3.10")])})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(countyutils, "datetime", FixedDatetime)
        mp.setattr(countyutils.time, "sleep", lambda s: None)
        mp.setattr(countyutils.requests, "Session", lambda: session)
        df = countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)

    assert df.to_dict("records") == [row("Alabama", "AL", "Autauga", "$3.10")]


# Edge


def test_no_states_means_no_requests_and_an_empty_frame(sleeps, use_session):
    session = use_session(FakeAAA(pages={}, map_data={}))

    df = countyutils.process_gas_prices({}, delay=0)

    assert df.empty
    assert session.calls == []


def test_a_county_without_a_price_keeps_its_row(sleeps, use_session):
    # AAA leaves about 36 counties unpriced on any given day; they appear with a blank price
    use_session(FakeAAA(pages={"NE": [make_response(200, map_page(1))]},
                        map_data={"1": map_data([("Arthur", None), ("Adams", "$3.10")])}))

    df = countyutils.process_gas_prices({"Nebraska": "NE"}, delay=0)

    assert df.to_dict("records") == [row("Nebraska", "NE", "Arthur", None), row("Nebraska", "NE", "Adams", "$3.10")]


def test_county_names_keep_accents_and_apostrophes(sleeps, use_session):
    names = ["Doña Ana", "Prince George's", "St. Mary's", "Miami-Dade"]
    use_session(FakeAAA(pages={"XX": [make_response(200, map_page(1))]},
                        map_data={"1": map_data([(n, "$3.00") for n in names])}))

    df = countyutils.process_gas_prices({"Mixed": "XX"}, delay=0)

    assert list(df["name"]) == names


def test_the_first_map_id_on_the_page_is_used(sleeps, use_session):
    session = use_session(FakeAAA(pages={"AL": [make_response(200, map_page(7) + map_page(8))]},
                                  map_data={"7": map_data([("Autauga", "$3.10")])}))

    countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)

    assert session.calls[1]["params"]["map_id"] == "7"


# Failure


@pytest.mark.parametrize("outcome,reason", [
    (("no map id",), "No map_id found for State0"),
    (("no map data",), "No map_data found for State0"),
    (("bad json",), "JSON decode error for State0"),
    (("http error", 403), "Request error for State0: 403"),
])
def test_a_failed_state_is_logged_with_its_reason(sleeps, use_session, caplog, outcome, reason):
    use_session(fake_site([outcome]))

    with caplog.at_level("WARNING"):
        df = countyutils.process_gas_prices({"State0": "S0"}, delay=0)

    assert df.empty
    assert reason in caplog.text
    assert "No data for 1 of 1 states: State0" in caplog.text


def test_unexpected_errors_are_not_swallowed(sleeps, use_session):
    class Broken(FakeAAA):
        def get(self, url, params=None, timeout=None):
            raise RuntimeError("AAA changed its page layout")

    use_session(Broken(pages={}, map_data={}))

    with pytest.raises(RuntimeError, match="page layout"):
        countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)
