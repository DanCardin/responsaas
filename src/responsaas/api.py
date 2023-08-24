from __future__ import annotations

import base64
import contextlib
import logging
import pickle
from dataclasses import dataclass
from functools import partialmethod
from re import Pattern
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import requests
from responses import matchers

log = logging.getLogger(__name__)


URLPatternType = Union[Pattern, str]


@dataclass
class ResponsaasClient:
    server_url: str

    timeout: int = 10

    def _make_call(self, endpoint, *, json={}, namespace_id: Optional[str] = None):
        if namespace_id:
            json = {**json, "namespace_id": namespace_id}

        url = f"{self.server_url}/__responsaas__/{endpoint}"
        response = requests.post(url, json=json, timeout=self.timeout)
        try:
            response.raise_for_status()
        except Exception:  # pragma: no cover
            log.error(response.text, exc_info=True)
            raise
        return response


@dataclass
class ResponsaasServer(ResponsaasClient):
    @contextlib.contextmanager
    def activate(self):
        response = self._make_call("enter").json()
        namespace_id = response["namespace_id"]
        try:
            yield Responsaas(
                self.server_url,
                namespace_id=namespace_id,
                timeout=self.timeout,
            )
        finally:
            self._make_call("exit", namespace_id=namespace_id).json()


@dataclass
class Responsaas(ResponsaasClient):
    namespace_id: str = ""

    DELETE: Literal["DELETE"] = "DELETE"
    GET: Literal["GET"] = "GET"
    HEAD: Literal["HEAD"] = "HEAD"
    OPTIONS: Literal["OPTIONS"] = "OPTIONS"
    PATCH: Literal["PATCH"] = "PATCH"
    POST: Literal["POST"] = "POST"
    PUT: Literal["PUT"] = "PUT"

    @property
    def base_url(self) -> str:
        return f"{self.server_url}/{self.namespace_id}"

    def reset(self) -> None:
        self._make_call("reset", namespace_id=self.namespace_id)

    def add(self, *args: Any, **kwargs: Any):
        """Add a new response.

        The semantic behavior should closely match that of `responses`.

        The primary exception is the `match` argument. Where `responses` accepts
        a list of closures over some input (i.e. `query_string_matcher({'foo': 'bar'})`),
        with `responsaas`, you must instead supply a tuple of the function and its
        arguments separately (i.e. `(query_string_matcher, [{'foo': 'bar'}])`).

        This is necessary because, in order to utilize arbitrary `match` function
        inputs, the function is pickled and sent over the wire. Thus, the `match`
        function itself must be pickleable.
        """
        return self._execute("add", *args, **kwargs)

    def replace(self, *args: Any, **kwargs: Any):
        """Replace a response previously added using ``add()``.

        The signature is identical to ``add()``. The response is identified using ``method``
        and ``url``, and the first matching response is replaced.
        """
        return self._execute("replace", *args, **kwargs)

    def upsert(self, *args: Any, **kwargs: Any):
        """Replace a response previously added using ``add()``, or adds the response.

        If no response exists.  Responses are matched using ``method``and ``url``.
        The first matching response is replaced.
        """
        try:
            return self.replace(*args, **kwargs)
        except ValueError:
            return self.add(*args, **kwargs)

    def remove(self, *args: Any, **kwargs: Any):
        """Remove all matching responses previously added using ``add()``."""
        return self._execute("remove", *args, **kwargs)

    def calls(self) -> list:
        response = self._make_call("calls", namespace_id=self.namespace_id).json()
        pickled_calls = response["calls"]
        return pickle.loads(base64.b64decode(pickled_calls))  # noqa: S301

    def call_count(self, url: str) -> int:
        response = self._make_call(
            "call_count", json={"url": url}, namespace_id=self.namespace_id
        ).json()
        return response["call_count"]

    def assert_call_count(self, url: str, count: int):
        call_count = self.call_count(url)
        assert call_count == count

    delete = partialmethod(add, DELETE)
    get = partialmethod(add, GET)
    head = partialmethod(add, HEAD)
    options = partialmethod(add, OPTIONS)
    patch = partialmethod(add, PATCH)
    post = partialmethod(add, POST)
    put = partialmethod(add, PUT)

    def _execute(
        self,
        action: str,
        method: str,
        url: Optional[URLPatternType],
        content_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        json: Optional[Any] = None,
        status: Optional[int] = None,
        match: Optional[List[Tuple[str, Any]]] = None,
    ):
        matchers = None
        if match:
            matchers = [
                (base64.b64encode(pickle.dumps(match)).decode(), match_args)
                for match, match_args in match
            ]

        pattern = None
        if isinstance(url, Pattern):
            pattern = base64.b64encode(pickle.dumps(url)).decode()
            url = None

        return self._make_call(
            action,
            json={
                "method": method,
                "url": url,
                "pattern": pattern,
                "content_type": content_type,
                "headers": headers,
                "body": body,
                "json": json,
                "status": status,
                "match": matchers,
            },
            namespace_id=self.namespace_id,
        )


__all__ = [
    "matchers",
    "ResponsaasServer",
    "Responsaas",
]
