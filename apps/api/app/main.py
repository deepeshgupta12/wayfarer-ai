from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.destinations import router as destinations_router
from app.api.routes.embeddings import router as embeddings_router
from app.api.routes.health import router as health_router
from app.api.routes.persona import router as persona_router
from app.api.routes.persona_embeddings import router as persona_embeddings_router
from app.api.routes.providers import router as providers_router
from app.api.routes.review_intelligence import router as review_intelligence_router
from app.api.routes.traveller_memory import router as traveller_memory_router
from app.api.routes.trip_plan import router as trip_plan_router
from app.api.routes.trips import router as trips_router
from app.core.config import get_settings
from app.db.session import create_db_tables

settings = get_settings()


def _resolve_frontend_cors_origins() -> list[str]:
    configured = getattr(settings, "frontend_cors_origins", None)
    if configured:
        return configured

    raw = getattr(
        settings,
        "frontend_cors_origins_raw",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_frontend_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(providers_router)
app.include_router(embeddings_router)
app.include_router(persona_router)
app.include_router(persona_embeddings_router)
app.include_router(review_intelligence_router)
app.include_router(destinations_router)
app.include_router(traveller_memory_router)
app.include_router(trip_plan_router)
app.include_router(trips_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.app_env,
        "version": "0.1.0",
    }