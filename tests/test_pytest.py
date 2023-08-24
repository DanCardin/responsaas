import pytest
import requests.exceptions
from responsaas.pytest import (
    create_responsaas_fixture,
)


def test_no_base_url():
    fixture = create_responsaas_fixture()
    with pytest.raises(ValueError):
        next(fixture.__pytest_wrapped__.obj(None))


def test_with_base_url():
    fixture = create_responsaas_fixture(server_url="http://localhost")

    # This implies it's actually attempting to connect
    with pytest.raises(requests.exceptions.ConnectionError):
        next(fixture.__pytest_wrapped__.obj(None))


def test_with_string_fixture():
    fixture = create_responsaas_fixture()

    # This implies it's actually attempting to connect
    with pytest.raises(requests.exceptions.ConnectionError):
        next(fixture.__pytest_wrapped__.obj("http://localhost"))
