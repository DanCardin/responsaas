from __future__ import annotations

import base64
import logging
import pickle
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from responsaas.main import app, state

log = logging.getLogger(__name__)


class NamespaceId(BaseModel):
    namespace_id: str


class Route(NamespaceId):
    url: Optional[str] = None
    pattern: Optional[str] = None
    method: Optional[str] = "GET"
    content_type: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    json_body: Optional[Any] = Field(None, alias="json")
    status: Optional[int] = Field(None)
    match: Optional[List[Tuple[str, Any]]] = None


class CallCount(NamespaceId):
    url: str


def collect_responses_kwargs(payload: Route):
    if payload.pattern:
        url = pickle.loads(  # noqa: S301
            base64.b64decode(payload.pattern.encode("utf-8"))
        )
    else:
        url = payload.url

    kwargs: Dict[str, Any] = {
        "method": payload.method,
        "url": url,
    }

    # responses uses kwargs dynamically to determine sent fields. We cannot
    # "just" send None for these.

    if payload.body is not None:
        kwargs["body"] = payload.body

    if payload.json_body is not None:
        kwargs["json"] = payload.json_body

    if payload.status is not None:
        kwargs["status"] = payload.status

    if payload.headers is not None:
        kwargs["headers"] = payload.headers

    if payload.content_type is not None:
        kwargs["content_type"] = payload.content_type

    if payload.match is not None:
        kwargs["match"] = []

        for matcher, *match_args in payload.match:
            matcher_fn = pickle.loads(  # noqa: S301
                base64.b64decode(matcher.encode("utf-8"))
            )
            kwargs["match"].append(matcher_fn(*match_args))

    return kwargs


@app.post("/__responsaas__/add")
async def add(payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    kwargs = collect_responses_kwargs(payload)
    namespace.responses.add(**kwargs)


@app.post("/__responsaas__/replace")
async def replace(payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    kwargs = collect_responses_kwargs(payload)
    namespace.responses.replace(**kwargs)


@app.post("/__responsaas__/remove")
async def remove(payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    kwargs = collect_responses_kwargs(payload)
    namespace.responses.remove(**kwargs)


@app.post("/__responsaas__/upsert")
async def upsert(payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    kwargs = collect_responses_kwargs(payload)
    namespace.responses.upsert(**kwargs)


@app.post("/__responsaas__/reset")
async def reset(payload: NamespaceId):
    namespace = state.get_namespace(payload.namespace_id)
    namespace.responses.reset()


@app.post("/__responsaas__/calls")
async def calls(payload: NamespaceId):
    namespace = state.get_namespace(payload.namespace_id)

    calls = namespace.responses.calls
    pickled_calls = base64.b64encode(pickle.dumps(calls)).decode("utf-8")
    return {"calls": pickled_calls}


@app.post("/__responsaas__/call_count")
async def call_count(payload: CallCount):
    namespace = state.get_namespace(payload.namespace_id)

    calls = namespace.responses.calls
    call_count = len([1 for call in calls if call.request.url == payload.url])
    return {"call_count": call_count}
