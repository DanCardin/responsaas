from __future__ import annotations

import contextlib
import inspect
import json
import logging
import re
import textwrap
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from responses import CallbackResponse, RequestsMock

from responsaas.routes.route import (
    eval_callback_pickle,
    eval_callback_source,
    eval_matcher_source,
)
from responsaas.state import Namespace, State

log = logging.getLogger(__name__)

staging_state: State = State()


def _resolve_callback(fn: Callable) -> dict[str, str]:
    """Resolve a callable to the appropriate callback kwarg for AdminRoutePayload.

    Three available patterns, depending on the complexity of the callback:

    - **Pure function**: no captured variables

      ```
      def my_handler(request):
          return (200, {}, json.dumps({"ok": True}))

      ns.get("/api", callback=my_handler)
      ```

    - **Self-contained closure**: requires `cloudpickle`

      ```
      def make_counter():
          count = 0
          def callback(request):
              nonlocal count
              count += 1
              return (200, {}, json.dumps({"n": count}))
          return callback

      ns.get("/api/counter", callback=make_counter())
      ```

    - `callback_source`: For situations that cannot be satisfied by cloudpickle

      ```
      ns.get("/api/counter", callback_source='''
      count = 0

      def callback(request):
          global count
          count += 1
          return (200, {}, json.dumps({"n": count}))
      ''')
      ```
    """
    if fn.__name__ == "<lambda>":
        raise ValueError(
            "Lambda callbacks are not supported. Use a named function or pass callback_source= with a source string."
        )
    if fn.__code__.co_freevars:
        try:
            import base64

            import cloudpickle

            return {"callback_pickle": base64.b64encode(cloudpickle.dumps(fn)).decode()}
        except ImportError:
            raise ValueError(
                f"Callback {fn.__name__!r} captures outer variables {fn.__code__.co_freevars!r}. "
                "Install cloudpickle to serialize closure callbacks: pip install cloudpickle"
            ) from None
    src = textwrap.dedent(inspect.getsource(fn))
    if fn.__name__ != "callback":
        src += f"\ncallback = {fn.__name__}"
    return {"callback_source": src}


class NamespaceProxy:
    def __init__(self, ns: Namespace, mock: RequestsMock, name: str) -> None:
        self.ns = ns
        self.mock = mock
        self.name = name

    def add(self, method: str, url: str | None = None, **kwargs: Any) -> None:
        if callable(kwargs.get("callback")):
            kwargs.update(_resolve_callback(kwargs.pop("callback")))
        payload = AdminRoutePayload.model_validate(
            {"method": method, "url": url, **kwargs}
        )
        self.ns.route_history.append(payload)
        apply_admin_route(self.mock, payload)
        log.info(
            "namespace %r: registered %s %s",
            self.name,
            method,
            url or kwargs.get("url_pattern", "(callback)"),
        )

    def get(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("GET", url, **kwargs)

    def post(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("POST", url, **kwargs)

    def put(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("PUT", url, **kwargs)

    def patch(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("PATCH", url, **kwargs)

    def delete(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("DELETE", url, **kwargs)

    def head(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("HEAD", url, **kwargs)

    def options(self, url: str | None = None, **kwargs: Any) -> None:
        self.add("OPTIONS", url, **kwargs)


class AdminRoutePayload(BaseModel):
    """Route definition used by the admin interface (no namespace_id, no pickle fields)."""

    model_config = ConfigDict(populate_by_name=True)

    method: str = "GET"
    url: str | None = None
    url_pattern: str | None = None
    status: int = 200
    json_body: Any | None = Field(None, alias="json")
    body: str | None = None
    content_type: str | None = None
    headers: dict[str, str] | None = None
    match_source: list[str] | None = None
    callback_source: str | None = None
    callback_pickle: str | None = None


def apply_admin_route(mock: RequestsMock, payload: AdminRoutePayload) -> None:
    if payload.callback_pickle or payload.callback_source:
        if payload.callback_pickle:
            fn = eval_callback_pickle(payload.callback_pickle)

        if payload.callback_source:
            fn = eval_callback_source(payload.callback_source)

        url: Any = (
            re.compile(payload.url_pattern) if payload.url_pattern else payload.url
        )
        match_list = [eval_matcher_source(s) for s in (payload.match_source or [])]
        mock.add(
            CallbackResponse(
                method=payload.method,
                url=url,
                callback=fn,
                match=match_list,
            )
        )
        return

    url = re.compile(payload.url_pattern) if payload.url_pattern else payload.url
    kwargs: dict[str, Any] = {
        "method": payload.method,
        "url": url,
        "status": payload.status,
    }

    if payload.json_body is not None:
        kwargs["json"] = payload.json_body
    if payload.body is not None:
        kwargs["body"] = payload.body
    if payload.headers is not None:
        kwargs["headers"] = payload.headers
    if payload.content_type is not None:
        kwargs["content_type"] = payload.content_type

    match_list = [eval_matcher_source(s) for s in (payload.match_source or [])]
    if match_list:
        kwargs["match"] = match_list

    mock.add(**kwargs)


def replay_routes(mock: RequestsMock, routes: list[AdminRoutePayload]) -> None:
    mock.reset()
    for route in routes:
        apply_admin_route(mock, route)


@contextlib.contextmanager
def namespace(name: str, assert_all_requests_are_fired: bool = False):
    log.info("namespace %r: creating", name)
    staging_state.create_namespace(
        namespace_id=name, assert_all_requests_are_fired=assert_all_requests_are_fired
    )
    ns = staging_state.get_namespace(name)
    yield NamespaceProxy(ns, ns.responses, name)
    log.info("namespace %r: done (%d route(s))", name, len(ns.route_history))


def load_python_config(app_state: State, path: Path) -> None:
    log.info("loading config: %s", path)
    source = path.read_text()
    staging_state.reset()
    try:
        exec(source, {})  # noqa: S102
    finally:
        for ns_id, ns in staging_state.namespaces.items():
            app_state.namespaces[ns_id] = ns
        staging_state.reset()
    log.info("config loaded: %s", path)


def export_namespace(namespace_id: str, routes: list[AdminRoutePayload]) -> str:
    lines = [
        "from responsaas import namespace\n",
        f"\nwith namespace({namespace_id!r}) as rs:\n",
    ]
    for route in routes:
        args = [repr(route.method), repr(route.url or route.url_pattern)]
        kwargs_parts: list[str] = []

        if route.status != 200:
            kwargs_parts.append(f"status={route.status!r}")
        if route.json_body is not None:
            kwargs_parts.append(f"json={json.dumps(route.json_body)}")
        if route.body is not None:
            kwargs_parts.append(f"body={route.body!r}")
        if route.headers:
            kwargs_parts.append(f"headers={route.headers!r}")
        if route.content_type:
            kwargs_parts.append(f"content_type={route.content_type!r}")
        if route.url_pattern:
            kwargs_parts.append(f"url_pattern={route.url_pattern!r}")
        if route.match_source:
            kwargs_parts.append(f"match_source={route.match_source!r}")
        if route.callback_source:
            kwargs_parts.append(f"callback_source={route.callback_source!r}")

        call = f"    rs.add({', '.join(args + kwargs_parts)})\n"
        lines.append(call)

    if not routes:
        lines.append("    pass\n")

    return "".join(lines)
