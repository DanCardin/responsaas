import re

import requests
from responsaas.api import Responsaas


def test_get_request(responsaas: Responsaas):
    url = re.compile("/foo/.*")
    responsaas.get(url, json={"hey": "there"})

    response = requests.get(f"{responsaas.base_url}/foo/bar", timeout=1)
    assert response.json() == {"hey": "there"}
    assert response.status_code == 200

    response = requests.get(f"{responsaas.base_url}/foo/baz", timeout=1)
    assert response.json() == {"hey": "there"}
    assert response.status_code == 200
