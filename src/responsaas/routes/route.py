from __future__ import annotations

import base64
import json
import pickle
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from responses import CallbackResponse, matchers

from responsaas.state import StateDep

router = APIRouter()


class NamespaceId(BaseModel):
    namespace_id: str


class Route(NamespaceId):
    url: str | None = None
    pattern: str | None = None
    url_pattern: str | None = None
    method: str | None = "GET"
    content_type: str | None = None
    headers: dict[str, str] | None = None
    body: bytes | None = None
    json_body: Any | None = Field(None, alias="json")
    status: int | None = Field(None)
    match: list[tuple[str, Any]] | None = None
    match_source: list[str] | None = None
    callback_source: str | None = None
    callback_pickle: str | None = None


class CallCount(NamespaceId):
    url: str


def eval_matcher_source(source: str) -> Any:
    local: dict[str, Any] = {}
    exec(source, {"matchers": matchers, "re": re}, local)  # noqa: S102
    return local["matcher"]


def eval_callback_source(source: str) -> Any:
    # Single dict for globals+locals so `global count` style state survives across calls.
    ns: dict[str, Any] = {"json": json, "__builtins__": __builtins__}
    exec(source, ns)  # noqa: S102
    return ns["callback"]


def eval_callback_pickle(b64: str) -> Any:
    import cloudpickle

    return cloudpickle.loads(base64.b64decode(b64.encode()))


def collect_responses_kwargs(payload: Route) -> dict[str, Any]:
    if payload.url_pattern:
        url: Any = re.compile(payload.url_pattern)
    elif payload.pattern:
        url = pickle.loads(  # noqa: S301
            base64.b64decode(payload.pattern.encode("utf-8"))
        )
    else:
        url = payload.url

    kwargs: dict[str, Any] = {
        "method": payload.method,
        "url": url,
    }

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

    match_list: list[Any] = []

    if payload.match is not None:
        for matcher, *match_args in payload.match:
            matcher_fn = pickle.loads(  # noqa: S301
                base64.b64decode(matcher.encode("utf-8"))
            )
            match_list.append(matcher_fn(*match_args))

    if payload.match_source:
        for src in payload.match_source:
            match_list.append(eval_matcher_source(src))

    if match_list:
        kwargs["match"] = match_list

    return kwargs


def _apply_route(mock: Any, action: str, payload: Route) -> None:
    if payload.callback_source:
        fn = eval_callback_source(payload.callback_source)
        if payload.url_pattern:
            url: Any = re.compile(payload.url_pattern)
        else:
            url = payload.url
        match_list = [eval_matcher_source(s) for s in (payload.match_source or [])]
        cb = CallbackResponse(
            method=payload.method or "GET",
            url=url,
            callback=fn,
            match=match_list,
        )
        getattr(mock, action)(cb)
    else:
        kwargs = collect_responses_kwargs(payload)
        getattr(mock, action)(**kwargs)


@router.post("/__responsaas__/add")
async def add(state: StateDep, payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    _apply_route(namespace.responses, "add", payload)


@router.post("/__responsaas__/replace")
async def replace(state: StateDep, payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    _apply_route(namespace.responses, "replace", payload)


@router.post("/__responsaas__/remove")
async def remove(state: StateDep, payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    kwargs = collect_responses_kwargs(payload)
    namespace.responses.remove(**kwargs)


@router.post("/__responsaas__/upsert")
async def upsert(state: StateDep, payload: Route):
    namespace = state.get_namespace(payload.namespace_id)
    _apply_route(namespace.responses, "upsert", payload)


@router.post("/__responsaas__/reset")
async def reset(state: StateDep, payload: NamespaceId):
    namespace = state.get_namespace(payload.namespace_id)
    namespace.responses.reset()


@router.post("/__responsaas__/calls")
async def calls(state: StateDep, payload: NamespaceId):
    namespace = state.get_namespace(payload.namespace_id)

    calls = namespace.responses.calls
    pickled_calls = base64.b64encode(pickle.dumps(calls)).decode("utf-8")
    return {"calls": pickled_calls}


@router.post("/__responsaas__/call_count")
async def call_count(state: StateDep, payload: CallCount):
    namespace = state.get_namespace(payload.namespace_id)

    calls = namespace.responses.calls
    call_count = len([1 for call in calls if call.request.url == payload.url])
    return {"call_count": call_count}
