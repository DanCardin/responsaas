# Responsaas

[![Actions Status](https://github.com/dancardin/responsaas/workflows/test/badge.svg)](https://github.com/dancardin/responsaas/actions)
[![Coverage Status](https://coveralls.io/repos/github/DanCardin/responsaas/badge.svg?branch=main)](https://coveralls.io/github/DanCardin/responsaas?branch=main)
[![Documentation Status](https://readthedocs.org/projects/responsaas/badge/?version=latest)](https://responsaas.readthedocs.io/en/latest/?badge=latest)
[![Docker](https://img.shields.io/docker/cloud/build/dancardin/responsaas?label=Docker&style=flat)](https://hub.docker.com/r/dancardin/responsaas)

Wraps the python [responses](https://github.com/getsentry/responses) library As
A Service.

See the full documentation [here](https://responsaas.readthedocs.io/en/latest/)
(or more specifically
[converting from responses](https://responsaas.readthedocs.io/en/latest/converting)).

## Quickstart

### Automatic (with pytest)

Using
[pytest-mock-resources](https://github.com/schireson/pytest-mock-resources/), we
can use Docker to manage the lifecycle of the server.

`pip install responsaas[pmr]`

```python
from responsaas.pytest import create_responsaas_fixture, create_responsaas_server_fixture

responsaas_server = create_responsaas_server_fixture()
responsaas = create_responsaas_fixture()

def test_foo(responsaas: Responsaas):
    responsaas.add("/foo", json={"bar": True})

    response = requests.get(responsaas.base_url + "/foo")
    assert response.json() == {"bar": True}
```

### Manual

The manual examples assume you have some external way of standing up the server

`pip install responsaas`

```python
import requests
from responsaas import ResponsaasServer, Responsaas

# With pytest
from responsaas.pytest import create_responsaas_fixture

responsaas = create_responsaas_fixture("http://localhost:7564")

def test_foo(responsaas: Responsaas):
    responsaas.add("/foo", json={"bar": True})

    response = requests.get(responsaas.base_url + "/foo")
    assert response.json() == {"bar": True}


# Or completely manually.
def test_foo():
    responsaas_server = ResponsaasServer("http://localhost:7564")
    with responsaas_server.activate() as responsaas:
        responsaas.add("/foo", json={"bar": True})

        response = requests.get(responsaas.base_url + "/foo")
        assert response.json() == {"bar": True}
```

## Why?!?

Under the hood, `repsonses` is `patch`ing the network calls being made and
replacing their result with the result you specify. It's very fast, convenient,
and (by default) disallows you from making **actual** network calls.

**However** the same (`patch`) strategy that makes it useful has some issues.

- This can run afoul of other libraries which perform `patch` operations. The
  issue history of responses has many instances (frequently with `moto`), where
  patches get clobbered in one way or another.

  - `responsaas` does not use `patch` at all. It is a real standalone service
    responding to real requests.

- Either through `patch` issues, or through programmer error, `responses` can be
  **so** non-invasive that API calls accidentally get made through to the
  original destination URL.

  - `responsaas` forces you to change (or really, make configurable) the URL
    you're hitting for tests, which should make it impossible to hit the
    original destination url in tests on accident.

- `responses` allows you to return arbitrary python objects (like exceptions)
  which wouldn't be possible for a request to actually return.

  - `responsaas` (once again), is a literal service responding to requests. The
    requesting client code is receiving bytes over the wire, and parsing it
    normally.

- `responses` is(?) limited to mocking the `requests` library. Which doesn't
  cover cases like `httpx`, `aiohttp`, etc.

  - `responsaas` is client agnostic, given that it's a real service.

- `responses` needs an additional mechanism to allow "passthru" requests

  - `responsaas` (once again), is a literal service responding to requests, so
    it can only return.

## How?

What's going on internally is:

- Each test registers a new "namespace" against the `responsaas` server
- Each new namespace corresponds to one `responses.RequestsMock`.
- As incoming requests are received by the server, they're mapped to the request
  shape expected by `responses`, and routed directly through its request
  matching and responds logic.
