from __future__ import annotations

from importlib.resources import files

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = files("responsaas.admin").joinpath("admin.html").read_text(encoding="utf-8")


@router.get("/__responsaas__/admin/")
@router.get("/__responsaas__/admin")
async def admin_ui():
    return HTMLResponse(_HTML)
