from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict

from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from responses import RequestsMock


@dataclass
class Namespace:
    id: str
    responses: RequestsMock


@dataclass
class State:
    namespaces: Dict[str, Namespace] = field(default_factory=dict)
    http_adapter: HTTPAdapter = field(default_factory=HTTPAdapter)

    def reset(self):
        self.namespaces = {}
        self.http_adapter = HTTPAdapter()

    def create_namespace(self, responses: RequestsMock):
        namespace_id = str(uuid.uuid4())
        self.namespaces[namespace_id] = Namespace(namespace_id, responses)
        return namespace_id

    def get_namespace(self, namespace_id: str):
        try:
            return self.namespaces[namespace_id]
        except Exception:
            raise HTTPException(
                status_code=400, detail=f"Invalid namespace_id: {namespace_id}"
            )
