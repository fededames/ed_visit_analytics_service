from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.domain.errors import InvalidAnalyticsRequest

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.exception_handler(InvalidAnalyticsRequest)
async def invalid_analytics_request_handler(_: Request, exc: InvalidAnalyticsRequest) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "http_request_completed",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "http_request_failed",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
