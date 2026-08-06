"""CLE FastAPI application entrypoint.

    uvicorn src.cle.api.app:app

Registers the Phase 1 router and maps `cle.errors.CLEError` (plus
`FiniteCategory`'s plain `ValueError` on a malformed composition table) to
HTTP responses. This is the only place in the API layer that interprets a
domain error, and it does so by re-labelling, never by recomputing anything.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cle.api.router import router
from cle.errors import CLEError, NoStrategyConfigured
from cle.version import __version__

app = FastAPI(title="Categorical Lift Engine", version=__version__)
app.include_router(router)


@app.exception_handler(NoStrategyConfigured)
async def _no_strategy_configured_handler(
    request: Request, exc: NoStrategyConfigured
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(CLEError)
async def _cle_error_handler(request: Request, exc: CLEError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


__all__ = ["app"]
