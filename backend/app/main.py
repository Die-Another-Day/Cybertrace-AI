from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.db.postgres import init_db
from app.db.neo4j import init_graph_schema, close_neo4j_driver
from app.api.routes.auth import router as auth_router
from app.api.routes.complaints import router as complaints_router
from app.api.routes.intelligence import (
    dashboard_router, graph_router, intel_router,
    evidence_router, audit_router
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CyberTrace AI backend...")
    await init_db()
    await init_graph_schema()
    logger.info("Databases initialized.")
    yield
    await close_neo4j_driver()
    logger.info("CyberTrace AI backend stopped.")


app = FastAPI(
    title="CyberTrace AI",
    description="AI-Powered Cyber Crime Investigation & Threat Correlation Platform",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration}ms"
    response.headers["X-Powered-By"] = "CyberTrace AI"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please contact the administrator."},
    )


# ── Routers ────────────────────────────────────────────────────────────────
PREFIX = settings.API_PREFIX

app.include_router(auth_router,       prefix=PREFIX)
app.include_router(complaints_router, prefix=PREFIX)
app.include_router(dashboard_router,  prefix=PREFIX)
app.include_router(graph_router,      prefix=PREFIX)
app.include_router(intel_router,      prefix=PREFIX)
app.include_router(evidence_router,   prefix=PREFIX)
app.include_router(audit_router,      prefix=PREFIX)


# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "operational",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "CyberTrace AI — Cyber Crime Investigation Platform",
        "docs": "/api/docs",
        "version": settings.APP_VERSION,
    }
