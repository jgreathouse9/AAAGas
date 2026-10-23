"""Fakes shared by the county scraper tests. Nothing here talks to the network."""

import json
import logging
from contextlib import contextmanager

import requests


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
    """The map data script for a state; ``counties`` is a list of (name, price) pairs."""
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

    ``pages`` maps a state abbreviation to the responses for its state page, served
    in order with the last one repeating. ``map_data`` maps a map_id to the body of
    its map data script.
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


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@contextmanager
def captured_logs():
    """Collect log messages without caplog, which hypothesis cannot share between examples."""
    handler = _ListHandler()
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield handler.messages
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
