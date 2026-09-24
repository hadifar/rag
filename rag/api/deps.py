from typing import Annotated

from fastapi import Depends, Request

from rag.container import Container


def get_container(request: Request) -> Container:
    """FastAPI dependency: reads the Container the lifespan stashed on app.state."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Container not initialized — app lifespan hasn't started")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
