import requests
from responsaas.api import Responsaas


def test_call_count(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    assert responsaas.call_count("/foo") == 2


def test_assert_call_count(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    responsaas.assert_call_count("/foo", 2)


def test_calls(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    requests.get(f"{responsaas.base_url}/foo", timeout=1)
    requests.get(f"{responsaas.base_url}/foo", timeout=1)

    calls = responsaas.calls()
    assert len(calls) == 2
    assert calls[0].request.url == "/foo"
    assert calls[0].response.json() == {"hey": "there"}
