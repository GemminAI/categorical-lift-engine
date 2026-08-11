"""CLE FastAPI application entrypoint.

    uvicorn src.cle.api.app:app

Registers the Phase 1 router and maps `cle.errors.CLEError` (plus
`FiniteCategory`'s plain `ValueError` on a malformed composition table) to
HTTP responses. This is the only place in the API layer that interprets a
domain error, and it does so by re-labelling, never by recomputing anything.

The module-level `app` below has no `recovery_engine`/`hekb_store` wired in
(see `cle.api.router.get_engine`) — it is the default/dev/test entrypoint,
and `/recover` on it fails loudly with a 503 by design. A real deployment
that has a configured `ThreeViewRecoveryLike` (or `hekb_store`) to offer
calls `create_app()` below instead of importing this module's `app`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cle.api.router import get_engine, router
from cle.errors import CLEError, NoStrategyConfigured
from cle.ports.recovery import ThreeViewRecoveryLike
from cle.runtime.engine import CLEEngine
from cle.version import __version__


def _build_app() -> FastAPI:
    instance = FastAPI(title="Categorical Lift Engine", version=__version__)
    instance.include_router(router)

    @instance.exception_handler(NoStrategyConfigured)
    async def _no_strategy_configured_handler(
        request: Request, exc: NoStrategyConfigured
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @instance.exception_handler(CLEError)
    async def _cle_error_handler(request: Request, exc: CLEError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @instance.exception_handler(ValueError)
    async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return instance


app = _build_app()


def create_app(
    *,
    recovery_engine: ThreeViewRecoveryLike | None = None,
    hekb_store: Any | None = None,
) -> FastAPI:
    """Composition-root entrypoint: a CLE app backed by a configured `CLEEngine`.

    `cle` imports no NVS-Kernel or HEKB code (`docs/BOUNDARIES.md`) — it has
    no way to construct a real `ThreeViewRecoveryLike`/HEKB client itself.
    Whatever process pairs CLE with a real one calls this instead of
    importing the bare `app` above, e.g.:

        from cle.api.app import create_app
        app = create_app(recovery_engine=my_configured_three_view_recovery)
        # uvicorn this `app`, not `cle.api.app:app`

    With no arguments this is equivalent to the module-level `app`: `/recover`
    still fails loudly with a 503 until a `recovery_engine` is passed in.
    """
    instance = _build_app()
    engine = CLEEngine(recovery_engine=recovery_engine, hekb_store=hekb_store)
    instance.dependency_overrides[get_engine] = lambda: engine
    return instance


__all__ = ["app", "create_app"]
