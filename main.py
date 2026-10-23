"""ORBIT AI Operations Studio — Application Entry Point.

Combines the Four Internship Automation Projects:
1. Lead Intelligence & Revenue Routing
2. Customer Support & Email Intelligence
3. Invoice Intelligence & Financial Operations
4. Enterprise Multi-Agent Business Orchestration

Plus Workflow Studio, Agent Registry, and Approval Center.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.invoices import router as invoices_router
from api.integrations import router as integrations_router
from api.leads import router as leads_router
from api.orchestration import router as orchestration_router
from api.support import router as support_router
from api.workflows import router as workflows_router
from core.config import settings
from core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("orbit.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing ORBIT AI Operations Studio schemas...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("ORBIT AI Operations Studio shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-Grade Autonomous AI Workforce & Business Automation Studio.",
    lifespan=lifespan,
)

# CORS middleware for open web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Module Routers
app.include_router(leads_router)
app.include_router(support_router)
app.include_router(invoices_router)
app.include_router(orchestration_router)
app.include_router(workflows_router)
app.include_router(integrations_router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Verify system health and active configuration mode."""
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "draft_only_mode": settings.DRAFT_ONLY_MODE,
        "environment": settings.ENVIRONMENT,
    }


# Static Files Mount for Web UI
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(parents=True, exist_ok=True)
(static_dir / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the main single page Operations Studio dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "ORBIT AI Operations Studio API is running.",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
