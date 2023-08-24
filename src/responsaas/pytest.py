from typing import (
    Generator,
    Literal,
    Optional,
    Protocol,
    Union,
)

import pytest

from responsaas.api import Responsaas, ResponsaasServer

Scope = Union[
    Literal["session"],
    Literal["package"],
    Literal["module"],
    Literal["class"],
    Literal["function"],
]


class HasBaseUrl(Protocol):
    base_url: str


@pytest.fixture
def responsaas_server():  # pragma: no cover
    return None


def create_responsaas_fixture(
    *, scope: Scope = "function", server_url: Optional[str] = None
):
    @pytest.fixture(scope=scope)
    def responsaas(
        responsaas_server: Union[str, HasBaseUrl, None],
    ) -> Generator[Responsaas, None, None]:
        nonlocal server_url

        if responsaas_server is not None:
            if isinstance(responsaas_server, str):
                server_url = responsaas_server

            else:
                server_url = responsaas_server.base_url

        if server_url is None:
            raise ValueError(
                "Either the `server_url` argument must be supplied, or "
                "the `responsaas_server` fixture must be defined."
            )

        responsaas = ResponsaasServer(server_url)
        with responsaas.activate() as scoped:
            yield scoped

    return responsaas


try:
    from pytest_mock_resources.config import DockerContainerConfig
    from pytest_mock_resources.container.base import ContainerCheckFailed, get_container

    class ResponsaasConfig(DockerContainerConfig):
        """Define the configuration object for moto.

        Args:
            image (str): The docker image:tag specifier to use for postgres containers.
                Defaults to :code:`"postgres:9.6.10-alpine"`.
            host (str): The hostname under which a mounted port will be available.
                Defaults to :code:`"localhost"`.
            port (int): The port to bind the container to.
                Defaults to :code:`5532`.
            ci_port (int): The port to bind the container to when a CI environment is detected.
                Defaults to :code:`5432`.
        """

        name = "responsaas"

        _fields = {"image", "host", "port"}  # noqa: RUF012
        _fields_defaults = {  # noqa: RUF012
            "image": "dancardin/responsaas:latest",
            "port": 7564,
        }

        @property
        def base_url(self):
            return f"http://{self.host}:{self.port}"

        def ports(self):
            return {7564: self.port}

        def check_fn(self):
            import requests

            try:
                requests.post(self.base_url + "/check", timeout=10)
            except requests.exceptions.RequestException:
                raise ContainerCheckFailed(
                    "Unable to connect to a presumed responsaas test container via given config: {}".format(
                        self
                    )
                )

    def create_responsaas_server_fixture(
        config: ResponsaasConfig = ResponsaasConfig(), *, scope: Scope = "session"
    ):
        @pytest.fixture(scope=scope)
        def responsaas_server(pytestconfig):
            for _ in get_container(pytestconfig, config):
                yield config
            # yield from get_container(pytestconfig, config)

        return responsaas_server

except ImportError:  # pragma: no cover
    pass


__all__ = [
    "create_responsaas_fixture",
    "create_responsaas_server_fixture",
    "ResponsaasConfig",
    "Scope",
]
