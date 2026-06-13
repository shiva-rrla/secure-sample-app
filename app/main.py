"""
Secure Sample Application
A minimal FastAPI service demonstrating production-grade DevSecOps practices.
"""

import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Logging configuration (structured, no PII)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful shutdown handler
# ---------------------------------------------------------------------------
shutdown_event = False


def _handle_sigterm(signum, frame):
    global shutdown_event
    logger.info("Received SIGTERM, initiating graceful shutdown...")
    shutdown_event = True


signal.signal(signal.SIGTERM, _handle_sigterm)


# ---------------------------------------------------------------------------
# Lifespan context (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Secure Sample App",
    version="1.0.0",
    docs_url=None,  # Disable docs in production (or restrict via ingress)
    redoc_url=None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz():
    """Kubernetes liveness/readiness probe endpoint."""
    return {"status": "healthy"}


@app.get("/readyz", status_code=status.HTTP_200_OK)
async def readyz():
    """Kubernetes readiness probe endpoint."""
    if shutdown_event:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready"},
        )
    return {"status": "ready"}


@app.get("/api/v1/info", status_code=status.HTTP_200_OK)
async def info():
    """Return non-sensitive application metadata."""
    return {
        "app": "secure-sample-app",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run as non-root inside container (uid 65532)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        log_level="info",
        access_log=False,  # Disable default access log; rely on ingress logs
    )
