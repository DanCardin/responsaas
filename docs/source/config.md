# Seed / Config Files

Beyond configuring routes per-test via the API, `responsaas` supports loading a
**Python config file** at server startup that seeds named namespaces with
pre-defined routes. This is useful for standing up a long-lived mock server
(e.g. in Docker) with a stable, version-controlled set of responses.

## Defining a config file

A config file is a plain Python script that imports `namespace` from
`responsaas` and uses it as a context manager:

```python
from responsaas import namespace

with namespace("payments") as ns:
    ns.get("/health", json={"status": "ok"})
    ns.post("/charge", status=201, json={"id": "ch_123"})

with namespace("identity") as ns:
    ns.get("/me", json={"user_id": 42})
```

`namespace(name)` yields a `NamespaceProxy` with HTTP-method helpers:

| Method | Description |
|---|---|
| `ns.get(url, **kwargs)` | Register a GET route |
| `ns.post(url, **kwargs)` | Register a POST route |
| `ns.put(url, **kwargs)` | Register a PUT route |
| `ns.patch(url, **kwargs)` | Register a PATCH route |
| `ns.delete(url, **kwargs)` | Register a DELETE route |
| `ns.head(url, **kwargs)` | Register a HEAD route |
| `ns.options(url, **kwargs)` | Register an OPTIONS route |
| `ns.add(method, url, **kwargs)` | Register any method explicitly |

All kwargs are forwarded to `responses` (e.g. `json=`, `body=`, `status=`,
`headers=`, `content_type=`, `match=`).

## Loading at startup

### CLI

```bash
responsaas --config path/to/config.py
```

The `--config` flag sets `RESPONSAAS_CONFIG` before the server starts.

Additional CLI options:

```
--host HOST      Bind address (default: 0.0.0.0, env: RESPONSAAS_HOST)
--port PORT      Port (default: 7564, env: RESPONSAAS_PORT)
--reload         Enable uvicorn auto-reload (useful during development)
```

### Environment variable

```bash
RESPONSAAS_CONFIG=path/to/config.py responsaas
```

### Docker

```dockerfile
ENV RESPONSAAS_CONFIG=/app/config.py
COPY config.py /app/config.py
```

## URL pattern matching

Use `url_pattern=` to match a regex instead of an exact URL:

```python
import re

with namespace("api") as ns:
    ns.get(url_pattern=r"/users/\d+", json={"id": 1, "name": "Alice"})
```

## Request matchers (`match_source=`)

`match_source` accepts a list of source-code strings, each defining a
`matcher` variable (a callable compatible with `responses.matchers`):

```python
with namespace("api") as ns:
    ns.post(
        "/search",
        json={"results": []},
        match_source=[
            'matcher = matchers.json_params_matcher({"q": "hello"})',
        ],
    )
```

The `matchers` name is pre-injected — no import needed inside the source
string. `re` is also available.

## Callback responses

For dynamic responses, use `callback=` with a plain named function:

```python
def my_handler(request):
    return (200, {}, '{"echo": true}')

with namespace("api") as ns:
    ns.get("/echo", callback=my_handler)
```

### Closures (cloudpickle)

If the callback captures outer variables, install `cloudpickle`:

```bash
pip install cloudpickle
```

```python
responses_to_return = [{"id": 1}, {"id": 2}]

def next_response(request):
    return (200, {}, json.dumps(responses_to_return.pop(0)))

with namespace("api") as ns:
    ns.get("/items", callback=next_response)
```

`responsaas` serializes the closure automatically via `cloudpickle`.

### `callback_source=` (stateful without cloudpickle)

For stateful callbacks that need `global` — or when `cloudpickle` is
unavailable — pass the function body as a source string. The string must
define a function named `callback`:

```python
with namespace("api") as ns:
    ns.get(
        "/counter",
        callback_source="""
count = 0

def callback(request):
    global count
    count += 1
    return (200, {}, f'{{"n": {count}}}')
""",
    )
```

`json` is pre-injected in the execution namespace.

## Exporting from the Admin UI

The Admin UI (`/__responsaas__/admin/`) has an **Export** button that generates
a config file from the currently registered routes of any namespace. The output
is ready to drop into a config file and commit.
