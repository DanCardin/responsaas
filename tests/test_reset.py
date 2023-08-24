import requests
from responsaas import Responsaas


def test_empty(responsaas: Responsaas):
    responsaas.reset()


def test_removes_state(responsaas: Responsaas):
    responsaas.get("/foo", json={"hey": "there"})

    response = requests.get(f"{responsaas.base_url}/foo", timeout=1)
    assert response.json() == {"hey": "there"}
    assert response.status_code == 200
    responsaas.reset()

    response = requests.get(f"{responsaas.base_url}/foo", timeout=1)
    assert response.status_code == 500
