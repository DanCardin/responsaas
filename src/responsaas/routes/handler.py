from __future__ import annotations

import logging
from json import JSONDecodeError

from fastapi import Request, Response
from requests import PreparedRequest
from requests.adapters import HTTPAdapter

from responsaas.main import app, state

log = logging.getLogger(__name__)

# The hostname here is actually not relevant, given that any request here has
# already made it to this service. Using the **actual** host just introduces
# more points of failure.
HOST_PREFIX = "http://_/"


url = "/{namespace_id:str}/{url:path}"


@app.get(url)
@app.post(url)
@app.put(url)
@app.patch(url)
@app.delete(url)
@app.head(url)
@app.options(url)
async def handler(namespace_id: str, request: Request):
    namespace = state.get_namespace(namespace_id)
    adapter: HTTPAdapter = state.http_adapter

    json = None
    body = None
    files = None
    try:
        json = await request.json()
    except JSONDecodeError:
        try:
            # Files
            raise Exception()
        except Exception:
            body = await request.body()

    url = "/" + request.path_params.get("url", "")

    prepared_request = PreparedRequest()

    prepared_request.prepare(
        method=request.method,
        url=HOST_PREFIX,
        headers=request.headers,
        params=request.query_params,
        json=json,
        files=files,
        data=body,
    )

    assert prepared_request.url
    prepared_request.url = url + prepared_request.url.removeprefix(HOST_PREFIX)

    response = namespace.responses._on_request(
        adapter=adapter, request=prepared_request
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response.headers,
    )
