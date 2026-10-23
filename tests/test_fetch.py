"""fetch(): one GET with retries for rate limiting and server errors."""

import pytest
import requests
from hypothesis import given
from hypothesis import strategies as st

import countyutils
from helpers import FakeSession, make_response

URL = "https://gasprices.aaa.com/"
RETRYABLE = sorted(countyutils.RETRY_STATUSES)
CLIENT_ERRORS = [s for s in range(400, 500) if s not in countyutils.RETRY_STATUSES]


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(countyutils.time, "sleep", calls.append)
    return calls


def run_fetch(responses, **kwargs):
    """Call fetch with time.sleep recorded instead of slept; return (result or exception, session, sleeps)."""
    session = FakeSession(responses)
    slept = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(countyutils.time, "sleep", slept.append)
        try:
            result = countyutils.fetch(session, URL, **kwargs)
        except requests.HTTPError as exc:
            result = exc
    return result, session, slept


# Smoke


def test_returns_the_response_when_the_first_request_succeeds(sleeps):
    session = FakeSession([make_response(200, "ok")])

    response = countyutils.fetch(session, URL, params={"state": "AL"})

    assert response.text == "ok"
    assert session.calls == [{"url": URL, "params": {"state": "AL"}, "timeout": 30}]
    assert sleeps == []


# Unit


@pytest.mark.parametrize("status", RETRYABLE)
def test_retries_rate_limits_and_server_errors(sleeps, status):
    session = FakeSession([make_response(status), make_response(200, "ok")])

    assert countyutils.fetch(session, URL).text == "ok"
    assert len(session.calls) == 2


def test_waits_as_long_as_retry_after_says(sleeps):
    session = FakeSession([make_response(429, headers={"Retry-After": "7"}), make_response(200, "ok")])

    countyutils.fetch(session, URL)

    assert sleeps == [7]


def test_backs_off_exponentially_without_retry_after(sleeps):
    session = FakeSession([make_response(503)] * 3 + [make_response(200, "ok")])

    countyutils.fetch(session, URL, backoff=10)

    assert sleeps == [10, 20, 40]


@given(
    retry_afters=st.lists(st.one_of(st.none(), st.integers(0, 10_000)), max_size=4),
    backoff=st.integers(1, 100),
)
def test_each_wait_is_retry_after_or_backoff_capped_at_max_wait(retry_afters, backoff):
    responses = [make_response(429, headers={} if ra is None else {"Retry-After": str(ra)}) for ra in retry_afters]

    result, session, slept = run_fetch(responses + [make_response(200, "ok")], backoff=backoff, max_wait=60)

    assert result.text == "ok"
    assert len(session.calls) == len(retry_afters) + 1
    expected = [min(60, backoff * 2 ** i if ra is None else ra) for i, ra in enumerate(retry_afters)]
    assert slept == expected


@given(statuses=st.lists(st.sampled_from(RETRYABLE), min_size=1, max_size=6))
def test_gives_up_after_the_last_attempt_and_reports_the_status(statuses):
    result, session, slept = run_fetch([make_response(s) for s in statuses], retries=len(statuses), backoff=1)

    assert isinstance(result, requests.HTTPError)
    assert str(statuses[-1]) in str(result)
    assert len(session.calls) == len(statuses)
    assert len(slept) == len(statuses) - 1


@given(status=st.sampled_from(CLIENT_ERRORS))
def test_client_errors_are_reported_without_retrying(status):
    result, session, slept = run_fetch([make_response(status)])

    assert isinstance(result, requests.HTTPError)
    assert len(session.calls) == 1
    assert slept == []


# Edge


def test_a_single_attempt_never_retries(sleeps):
    session = FakeSession([make_response(429)])

    with pytest.raises(requests.HTTPError):
        countyutils.fetch(session, URL, retries=1)

    assert sleeps == []


def test_retry_after_zero_retries_immediately(sleeps):
    session = FakeSession([make_response(429, headers={"Retry-After": "0"}), make_response(200, "ok")])

    countyutils.fetch(session, URL)

    assert sleeps == [0]


@pytest.mark.parametrize("header", ["Wed, 21 Oct 2026 07:28:00 GMT", "soon", "-5", "2.5"])
def test_retry_after_that_is_not_whole_seconds_falls_back_to_backoff(sleeps, header):
    session = FakeSession([make_response(429, headers={"Retry-After": header}), make_response(200, "ok")])

    countyutils.fetch(session, URL, backoff=10)

    assert sleeps == [10]


def test_a_huge_retry_after_is_capped(sleeps):
    # Honoring an hour per retry across 51 states would outlast GitHub's 6-hour job limit and lose every state
    session = FakeSession([make_response(429, headers={"Retry-After": "3600"}), make_response(200, "ok")])

    countyutils.fetch(session, URL)

    assert sleeps == [60]


# Failure


@pytest.mark.parametrize("retries", [0, -1])
def test_fewer_than_one_attempt_is_an_error(sleeps, retries):
    session = FakeSession([make_response(200, "ok")])

    with pytest.raises(ValueError, match="retries"):
        countyutils.fetch(session, URL, retries=retries)

    assert session.calls == []


def test_network_errors_propagate_to_the_caller(sleeps):
    class Unreachable:
        def get(self, url, params=None, timeout=None):
            raise requests.ConnectionError("connection reset")

    with pytest.raises(requests.ConnectionError):
        countyutils.fetch(Unreachable(), URL)
