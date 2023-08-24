from __future__ import annotations

import logging

from fastapi import FastAPI

from responsaas.state import State

logging.basicConfig(level=logging.DEBUG)

state = State()
app = FastAPI(debug=True)

from responsaas import routes  # noqa: F401, E402
