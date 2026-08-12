from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cappa
import uvicorn


@cappa.command(name="responsaas", help="Run the responsaas mock server")
@dataclass
class Responsaas:
    config: Annotated[
        Path | None,
        cappa.Arg(
            default=cappa.Env("RESPONSAAS_CONFIG"),
            long="--config",
            help="Path to Python config file (sets RESPONSAAS_CONFIG)",
        ),
    ] = None
    host: Annotated[
        str, cappa.Arg(long="--host", default=cappa.Env("RESPONSAAS_HOST"))
    ] = "0.0.0.0"  # noqa: S104
    port: Annotated[
        int, cappa.Arg(long="--port", default=cappa.Env("RESPONSAAS_HOST"))
    ] = 7564
    reload: Annotated[
        bool,
        cappa.Arg(default=False, long="--reload", action=cappa.ArgAction.store_true),
    ] = False

    def __call__(self, output: cappa.Output) -> None:
        if self.config:
            os.environ["RESPONSAAS_CONFIG"] = str(self.config)
            output.output(f"Loading config: {self.config}")

        output.output(f"Admin UI: http://{self.host}:{self.port}/__responsaas__/admin/")

        uvicorn.run(
            "responsaas.main:app",
            host=self.host,
            port=self.port,
            reload=self.reload,
        )
