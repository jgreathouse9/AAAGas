import json
from datetime import datetime

import pytest
import requests

import countyutils


def make_response(status, text="", url="https://gasprices.aaa.com/", headers=None):
    response = requests.Response()
    response.status_code = status
    response._content = text.encode()
    response.url = url
    response.headers.update(headers or {})
    return response


def map_page(map_id):
    return f'<script src="/wp-content/plugins/map.js?map_id={map_id}&amp;r=1"></script>'


def map_data(counties):
    data = {f"st{i}": {"name": name, "comment": price} for i, (name, price) in enumerate(counties)}
    return f"var map_cfg = {{map_data: {json.dumps(data)}, groups: {{}}}};"


class FakeSession:
    """Stands in for requests.Session, replaying canned responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


class FakeAAA:
    """Stands in for requests.Session, answering like gasprices.aaa.com.

    pages maps a state abbreviation to a list of responses for its state page (the
    last one repeats); map_data maps a map_id to the body of its map data script.
    """

    def __init__(self, pages, map_data):
        self.pages = {abbr: list(responses) for abbr, responses in pages.items()}
        self.map_data = map_data
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if url.endswith("index.php"):
            return make_response(200, self.map_data[params["map_id"]], url=url)
        responses = self.pages[params["state"]]
        return responses.pop(0) if len(responses) > 1 else responses[0]


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


# fetch


def test_fetch_returns_successful_response(sleeps):
    session = FakeSession([make_response(200, "ok")])

    response = countyutils.fetch(session, "https://gasprices.aaa.com/", params={"state": "AL"})

    assert response.text == "ok"
    assert session.calls == [{"url": "https://gasprices.aaa.com/", "params": {"state": "AL"}, "timeout": 30}]
    assert sleeps == []


def test_fetch_waits_for_retry_after_on_429(sleeps):
    session = FakeSession([make_response(429, headers={"Retry-After": "7"}), make_response(200, "ok")])

    response = countyutils.fetch(session, "https://gasprices.aaa.com/")

    assert response.text == "ok"
    assert len(session.calls) == 2
    assert sleeps == [7]


def test_fetch_backs_off_exponentially_without_retry_after(sleeps):
    session = FakeSession([make_response(503)] * 3 + [make_response(200, "ok")])

    response = countyutils.fetch(session, "https://gasprices.aaa.com/", backoff=10)

    assert response.text == "ok"
    assert sleeps == [10, 20, 40]


def test_fetch_ignores_non_numeric_retry_after(sleeps):
    date_header = {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    session = FakeSession([make_response(429, headers=date_header), make_response(200, "ok")])

    countyutils.fetch(session, "https://gasprices.aaa.com/", backoff=10)

    assert sleeps == [10]


def test_fetch_raises_after_last_attempt(sleeps):
    session = FakeSession([make_response(429)] * 3)

    with pytest.raises(requests.HTTPError, match="429"):
        countyutils.fetch(session, "https://gasprices.aaa.com/", retries=3, backoff=1)

    assert len(session.calls) == 3
    assert sleeps == [1, 2]


@pytest.mark.parametrize("status", [403, 404])
def test_fetch_does_not_retry_client_errors(sleeps, status):
    session = FakeSession([make_response(status)])

    with pytest.raises(requests.HTTPError):
        countyutils.fetch(session, "https://gasprices.aaa.com/")

    assert len(session.calls) == 1
    assert sleeps == []


# process_gas_prices


def test_process_gas_prices_returns_a_row_per_county(sleeps, use_session):
    use_session(FakeAAA(
        pages={"AL": [make_response(200, map_page(1))], "AK": [make_response(200, map_page(2))]},
        map_data={"1": map_data([("Autauga", "$3.10"), ("Baldwin", "$3.20")]), "2": map_data([("Juneau", "$4.50")])},
    ))

    df = countyutils.process_gas_prices({"Alabama": "AL", "Alaska": "AK"}, delay=0)

    today = datetime.now().strftime("%Y-%m-%d")
    assert df.to_dict("records") == [
        {"state": "Alabama", "abbreviation": "AL", "name": "Autauga", "price": "$3.10", "date": today},
        {"state": "Alabama", "abbreviation": "AL", "name": "Baldwin", "price": "$3.20", "date": today},
        {"state": "Alaska", "abbreviation": "AK", "name": "Juneau", "price": "$4.50", "date": today},
    ]


def test_process_gas_prices_requests_the_map_data_for_the_states_map_id(sleeps, use_session):
    session = use_session(FakeAAA(
        pages={"AL": [make_response(200, map_page(41))]},
        map_data={"41": map_data([("Autauga", "$3.10")])},
    ))

    countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)

    assert session.calls[0]["params"] == {"state": "AL"}
    assert session.calls[1]["url"] == "https://gasprices.aaa.com/index.php"
    assert session.calls[1]["params"]["map_id"] == "41"
    assert session.calls[1]["params"]["premiumhtml5map_js_data"] == "true"


def test_process_gas_prices_pauses_between_requests(sleeps, use_session):
    use_session(FakeAAA(
        pages={"AL": [make_response(200, map_page(1))], "AK": [make_response(200, map_page(2))]},
        map_data={"1": map_data([("Autauga", "$3.10")]), "2": map_data([("Juneau", "$4.50")])},
    ))

    countyutils.process_gas_prices({"Alabama": "AL", "Alaska": "AK"}, delay=1.5)

    # two requests per state, each followed by a pause
    assert sleeps == [1.5] * 4


def test_process_gas_prices_recovers_from_rate_limiting(sleeps, use_session):
    use_session(FakeAAA(
        pages={"AL": [make_response(429, headers={"Retry-After": "5"}), make_response(200, map_page(1))]},
        map_data={"1": map_data([("Autauga", "$3.10")])},
    ))

    df = countyutils.process_gas_prices({"Alabama": "AL"}, delay=0)

    assert list(df["name"]) == ["Autauga"]
    assert 5 in sleeps


def test_process_gas_prices_skips_failed_states_and_reports_them(sleeps, use_session, caplog):
    use_session(FakeAAA(
        pages={
            "AL": [make_response(200, map_page(1))],
            "DC": [make_response(200, "<html>no map on this page</html>")],
            "NE": [make_response(403)],
            "WY": [make_response(200, map_page(2))],
        },
        map_data={"1": map_data([("Autauga", "$3.10")]), "2": "map_data: {not json}, groups"},
    ))
    states = {"Alabama": "AL", "District of Columbia": "DC", "Nebraska": "NE", "Wyoming": "WY"}

    with caplog.at_level("WARNING"):
        df = countyutils.process_gas_prices(states, delay=0)

    assert list(df["state"]) == ["Alabama"]
    assert "No data for 3 of 4 states: District of Columbia, Nebraska, Wyoming" in caplog.text
    assert "Request error for Nebraska" in caplog.text
    assert "JSON decode error for Wyoming" in caplog.text


def test_process_gas_prices_returns_empty_frame_when_every_state_fails(sleeps, use_session):
    use_session(FakeAAA(pages={"AL": [make_response(403)], "AK": [make_response(403)]}, map_data={}))

    df = countyutils.process_gas_prices({"Alabama": "AL", "Alaska": "AK"}, delay=0)

    assert df.empty
