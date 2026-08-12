from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from requests.adapters import HTTPAdapter
from responses import RequestsMock


@dataclass
class Namespace:
    id: str
    responses: RequestsMock
    route_history: list[Any] = field(default_factory=list)


@dataclass
class State:
    namespaces: dict[str, Namespace] = field(default_factory=dict)
    http_adapter: HTTPAdapter = field(default_factory=HTTPAdapter)

    def reset(self):
        self.namespaces = {}
        self.http_adapter = HTTPAdapter()

    def create_namespace(
        self,
        namespace_id: str | None = None,
        assert_all_requests_are_fired: bool = False,
    ) -> str:
        namespace_id = namespace_id or str(uuid.uuid4())
        self.namespaces[namespace_id] = Namespace(
            namespace_id,
            RequestsMock(assert_all_requests_are_fired=assert_all_requests_are_fired),
        )
        return namespace_id

    def get_namespace(self, namespace_id: str):
        try:
            return self.namespaces[namespace_id]
        except Exception:
            raise HTTPException(
                status_code=400, detail=f"Invalid namespace_id: {namespace_id}"
            )


def get_state(request: Request) -> State:
    return request.app.state.state


StateDep = Annotated[State, Depends(get_state)]
