from __future__ import annotations

import contextlib
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from responsaas.admin.loader import (
    AdminRoutePayload,
    apply_admin_route,
    export_namespace,
    load_python_config,
    replay_routes,
)
from responsaas.state import StateDep

router = APIRouter()


class CreateNamespace(BaseModel):
    name: str


class LoadConfig(BaseModel):
    path: str


@router.get("/namespaces")
async def list_namespaces(state: StateDep):
    return [
        {"name": ns_id, "route_count": len(ns.route_history)}
        for ns_id, ns in state.namespaces.items()
    ]


@router.post("/namespaces", status_code=201)
async def create_namespace(payload: CreateNamespace, state: StateDep):
    if payload.name in state.namespaces:
        raise HTTPException(
            status_code=409, detail=f"Namespace {payload.name!r} already exists"
        )
    state.create_namespace(namespace_id=payload.name)
    return {"name": payload.name}


@router.delete("/namespaces/{name}", status_code=204)
async def delete_namespace(name: str, state: StateDep):
    ns = state.get_namespace(name)
    with contextlib.suppress(Exception):
        ns.responses.stop()
    del state.namespaces[name]


@router.get("/namespaces/{name}/routes")
async def list_routes(name: str, state: StateDep):
    ns = state.get_namespace(name)
    return [r.model_dump(by_alias=True) for r in ns.route_history]


@router.post("/namespaces/{name}/routes", status_code=201)
async def add_route(name: str, payload: AdminRoutePayload, state: StateDep):
    ns = state.get_namespace(name)
    apply_admin_route(ns.responses, payload)
    ns.route_history.append(payload)
    return {"index": len(ns.route_history) - 1}


@router.put("/namespaces/{name}/routes/{index}")
async def update_route(
    name: str, index: int, payload: AdminRoutePayload, state: StateDep
):
    ns = state.get_namespace(name)
    if index < 0 or index >= len(ns.route_history):
        raise HTTPException(status_code=404, detail=f"Route index {index} out of range")
    ns.route_history[index] = payload
    replay_routes(ns.responses, ns.route_history)
    return {"index": index}


@router.delete("/namespaces/{name}/routes/{index}", status_code=204)
async def delete_route(name: str, index: int, state: StateDep):
    ns = state.get_namespace(name)
    if index < 0 or index >= len(ns.route_history):
        raise HTTPException(status_code=404, detail=f"Route index {index} out of range")
    ns.route_history.pop(index)
    replay_routes(ns.responses, ns.route_history)


@router.post("/load")
async def load_config(payload: LoadConfig, state: StateDep):
    load_python_config(state, Path(payload.path))
    return {"ok": True}


@router.get("/export/{name}")
async def export(name: str, state: StateDep):
    ns = state.get_namespace(name)
    source = export_namespace(name, ns.route_history)
    return PlainTextResponse(
        source,
        headers={"Content-Disposition": f'attachment; filename="{name}.py"'},
    )
