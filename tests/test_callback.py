from __future__ import annotations

import json
import sys

import pytest
import requests as req_lib
from responses import RequestsMock

from responsaas.admin.loader import (
    AdminRoutePayload,
    _resolve_callback,
    apply_admin_route,
)

# ---------------------------------------------------------------------------
# _resolve_callback unit tests
# ---------------------------------------------------------------------------


def test_pure_function_produces_callback_source():
    def my_handler(request):
        return (200, {}, "{}")

    result = _resolve_callback(my_handler)
    assert set(result) == {"callback_source"}
    assert "callback = my_handler" in result["callback_source"]


def test_function_named_callback_needs_no_alias():
    def callback(request):
        return (200, {}, "{}")

    result = _resolve_callback(callback)
    assert "callback = callback" not in result["callback_source"]


def test_lambda_raises():
    with pytest.raises(ValueError, match="Lambda"):
        _resolve_callback(lambda req: (200, {}, "{}"))


def test_closure_without_cloudpickle_raises():
    def make():
        count = 0

        def callback(request):
            nonlocal count
            count += 1
            return (200, {}, "{}")

        return callback

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "cloudpickle", None)
        with pytest.raises(ValueError, match="cloudpickle"):
            _resolve_callback(make())


def test_closure_with_cloudpickle_produces_callback_pickle():
    pytest.importorskip("cloudpickle")

    def make():
        count = 0

        def callback(request):
            nonlocal count
            count += 1
            return (200, {}, "{}")

        return callback

    result = _resolve_callback(make())
    assert set(result) == {"callback_pickle"}


# ---------------------------------------------------------------------------
# apply_admin_route integration
# ---------------------------------------------------------------------------


def test_pure_callback_end_to_end():
    def my_handler(request):
        return (200, {}, json.dumps({"ok": True}))

    mock = RequestsMock()
    payload = AdminRoutePayload(
        method="GET",
        url="http://test.local/ping",
        **_resolve_callback(my_handler),
    )
    apply_admin_route(mock, payload)

    with mock:
        r = req_lib.get("http://test.local/ping", timeout=1)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_closure_callback_is_stateful():
    pytest.importorskip("cloudpickle")

    def make_counter():
        count = 0

        def callback(request):
            nonlocal count
            count += 1
            return (200, {}, json.dumps({"n": count}))

        return callback

    mock = RequestsMock()
    payload = AdminRoutePayload(
        method="GET",
        url="http://test.local/counter",
        **_resolve_callback(make_counter()),
    )
    apply_admin_route(mock, payload)

    with mock:
        r1 = req_lib.get("http://test.local/counter", timeout=1)
        r2 = req_lib.get("http://test.local/counter", timeout=1)
        r3 = req_lib.get("http://test.local/counter", timeout=1)

    assert r1.json() == {"n": 1}
    assert r2.json() == {"n": 2}
    assert r3.json() == {"n": 3}


def test_cloudpickle_captures_external_data():
    # The cloudpickle-only case: a closure captures an external Python object
    # that is baked in at closure-creation time.  callback_source= is exec'd in
    # isolation and has no way to reference live objects from the caller's scope.
    #
    # Here a pre-defined list of canned responses is captured and replayed in
    # sequence — a rotating-response pattern that requires the external list to
    # exist as a Python object.  Note that cloudpickle serialises the list *by
    # value* at pickle time; mutations to the original after registration have no
    # effect on the callback.
    pytest.importorskip("cloudpickle")

    canned = [
        {"status": "ok"},
        {"status": "degraded"},
        {"status": "error"},
    ]

    def make_rotating(responses: list) -> object:
        state = {"idx": 0}

        def callback(request):
            resp = responses[state["idx"] % len(responses)]
            state["idx"] += 1
            return (200, {}, json.dumps(resp))

        return callback

    mock = RequestsMock()
    payload = AdminRoutePayload(
        method="GET",
        url="http://test.local/status",
        **_resolve_callback(make_rotating(canned)),
    )
    apply_admin_route(mock, payload)

    with mock:
        r1 = req_lib.get("http://test.local/status", timeout=1)
        r2 = req_lib.get("http://test.local/status", timeout=1)
        r3 = req_lib.get("http://test.local/status", timeout=1)
        r4 = req_lib.get("http://test.local/status", timeout=1)

    assert r1.json() == {"status": "ok"}
    assert r2.json() == {"status": "degraded"}
    assert r3.json() == {"status": "error"}
    assert r4.json() == {"status": "ok"}  # wraps around


def test_source_callback_is_stateful():
    """callback_source= with global state — the documented pattern for closures without cloudpickle."""
    mock = RequestsMock()
    payload = AdminRoutePayload(
        method="GET",
        url="http://test.local/counter",
        callback_source="""
count = 0

def callback(request):
    global count
    count += 1
    return (200, {}, __import__('json').dumps({"n": count}))
""",
    )
    apply_admin_route(mock, payload)

    with mock:
        r1 = req_lib.get("http://test.local/counter", timeout=1)
        r2 = req_lib.get("http://test.local/counter", timeout=1)

    assert r1.json() == {"n": 1}
    assert r2.json() == {"n": 2}
