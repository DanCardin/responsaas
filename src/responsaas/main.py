from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from responsaas import admin, routes
from responsaas.admin.loader import load_python_config
from responsaas.state import State

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    state = State()
    app.state.state = state

    config_path = os.environ.get("RESPONSAAS_CONFIG")
    if config_path:
        load_python_config(state, Path(config_path))

    yield


def create_app() -> FastAPI:
    app = FastAPI(debug=True, lifespan=lifespan)
    app.include_router(routes.namespace.router)
    app.include_router(routes.route.router)
    app.include_router(admin.routes.router, prefix="/__responsaas__/admin")
    app.include_router(admin.ui.router)
    app.include_router(routes.handler.router)
    return app


app = create_app()
