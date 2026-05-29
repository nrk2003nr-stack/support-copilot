from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .core.database import engine, Base

# Import models so Alembic/Base can find them
from .auth import models as auth_models       # noqa
from .tickets import models as ticket_models  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (use Alembic in production)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from .auth.router import router as auth_router

app.include_router(auth_router, prefix="/api")

# Tickets and other optional routers may depend on heavy LLM packages.
# Import them lazily and skip if optional dependencies aren't installed so
# the core API (auth) can run during development and tests.
try:
    from .tickets.router import router as ticket_router
    app.include_router(ticket_router, prefix="/api")
except Exception:
    import warnings
    warnings.warn("Optional router 'tickets' not loaded (missing dependencies).")

# Analytics router
try:
    from .analytics import analytics_router
    app.include_router(analytics_router, prefix="/api")
except Exception:
    import warnings as _w
    _w.warn("Optional router 'analytics' not loaded (missing dependencies).")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}