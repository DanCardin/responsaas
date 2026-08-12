from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from responsaas.state import StateDep

router = APIRouter()


class EnterNamespace(BaseModel):
    assert_all_requests_are_fired: bool | None = False


class NamespaceId(BaseModel):
    namespace_id: str


@router.post("/__responsaas__/check")
async def check():
    """Check server's ability to respond to any request."""
    return {"ok": True}


@router.post("/__responsaas__/enter")
async def enter_namespace(payload: EnterNamespace, request: Request, state: StateDep):
    """Create a namespace against which future requests can be made."""
    if not payload:
        payload = EnterNamespace()

    namespace_id = state.create_namespace(
        assert_all_requests_are_fired=bool(payload.assert_all_requests_are_fired),
    )
    base_url = str(request.url_for("handler", namespace_id=namespace_id, url=""))
    return {
        "namespace_id": namespace_id,
        "base_url": base_url,
    }


@router.post("/__responsaas__/exit")
async def exit_namespace(payload: NamespaceId, state: StateDep):
    """Remove a namespace by id."""
    namespace = state.get_namespace(payload.namespace_id)
    try:
        namespace.responses.stop()
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
