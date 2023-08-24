import textwrap

import requests
from responsaas.api import Responsaas, matchers


def test_get_request(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    response = requests.get(f"{responsaas.base_url}/foo", timeout=1)
    assert response.json() == {"hey": "there"}
    assert response.status_code == 200


def test_match(responsaas: Responsaas):
    responsaas.get(
        "/foo", json={"hey": "there"}, match=[(matchers.query_param_matcher, {"q": 4})]
    )

    response = requests.get(f"{responsaas.base_url}/foo?q=4", timeout=1)
    assert response.json() == {"hey": "there"}
    assert response.status_code == 200

    response = requests.get(f"{responsaas.base_url}/foo?q=5", timeout=1)
    assert response.status_code == 500

    text = "Request: \n- GET /foo?q=5\n\nAvailable matches:\n- GET /foo Parameters do not match. {q: 5} doesn't match {q: 4}"
    assert textwrap.dedent(text) in response.text


def test_call_count(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    assert responsaas.call_count("/foo") == 2


def test_calls(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    requests.get(f"{responsaas.base_url}/foo", timeout=1)

    calls = responsaas.calls()
    assert len(calls) == 2
    assert calls[0].request.url == "/foo"
    assert calls[0].response.json() == {"hey": "there"}
