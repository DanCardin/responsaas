# Converting from responses

The API tries to be as close to `responses`'s API as possible. There are,
however, some differences necessitated by the fact that it's backed by a real
server making API calls.

## URLs

The potentially most invasive change is that `responsaas` forces your **actual**
code to allow for a configurable base url. Ultimately requests will be made
against a URL that is **not** the real destination service.

Bad:

```python
@dataclass
class GoogleClient:
    def get(self, relative_url):
        return requests.get('https://google.com' + relative_url)
```

Good:

```python
@dataclass
class GoogleClient:
    base_url: str = 'https://google.com'

    def get(self, relative_url):
        return requests.get(self.base_url + relative_url)
```

Doing so, enables your tests to runtime configure your code, so that it **can**
be tested with `responsaas`.

```python
def test_manual(responsaas: Responsaas):
    responsaas.add("/foo", json={"bar": True})

    client = GoogleClient(responsaas.base_url)
    response = client.get('/foo')
    assert response.json() == {"bar": True}

# or with a fixture
@pytest.fixture
def client(responsaas: Responsaas):
    return GoogleClient(responsaas.base_url)


def test_manual(client: GoogleClient, responsaas: Responsaas):
    responsaas.add("/foo", json={"bar": True})

    response = client.get('/foo')
    assert response.json() == {"bar": True}
```

## Activate

The `@responses.activate` decorator cannot work, because something needs to
supply the base URL.

`responsaas` works much more like the `responses.RequestsMock` object, which
must either be used as a context manager (either directly or managed by a pytest
fixture).

```python
import requests
from responsaas import ResponsaasServer, Responsaas

# With pytest
from responsaas.pytest import create_responsaas_fixture

responsaas = create_responsaas_fixture("http://localhost:7564")

def test(responsaas: Responsaas):
    responsaas.add("/foo", json={"bar": True})

    response = requests.get(responsaas.base_url + "/foo")
    assert response.json() == {"bar": True}


# Or completely manually.
def test():
    responsaas_server = ResponsaasServer("http://localhost:7564")
    with responsaas_server.activate() as responsaas:
        responsaas.add("/foo", json={"bar": True})

        response = requests.get(responsaas.base_url + "/foo")
        assert response.json() == {"bar": True}
```

## add/remove/reset/assert_call_count/get/post/etc

Once you are inside the context of a test with a handle on a
`responsaas.Responsaas` object, most of the APIs should feel exactly like using
`responses`.

The largest difference, is that there is no need to specify the hostname in the
URL, because the server itself is the host.

```python
def test(responses: Responses):
    responses.add("/foo", json={})
    responses.get("/foo", json={})
    responses.post("/foo", json={})
    responses.remove("/foo", json={})
    ...
```

### `match=`

The `match` keyword argument is the most significant place where the API needed
to diverge. In responses, you supply a list of closures capable of reacting to
an incoming request.

```python
from responses.matchers import query_param_matcher

responses.add('/foo', match=[query_param_matcher({'foo': 'bar'})])
```

`responsaas` tries to support a similar interface (by pickling the provided
functions and sending them across the wire to the server), but those closures
are not serializable.

```python
from responses.matchers import query_param_matcher

def test(responsaas: Responsaas):
    responsaas.add('/foo', match=[(query_param_matcher, {'foo': 'bar'})])
```

Instead, the function and its arguments are passed as a tuple (which **can** be
serialized).

## calls

`responses.calls` is a `property` that returns all the calls made during the
test.

`Responsaas.calls()` is a method which does the same thing. It is internally
making an API call, so a property became inappropriate.
