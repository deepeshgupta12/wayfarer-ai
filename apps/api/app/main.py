from fastapi import FastAPI

from app.api.routes.embeddings import router as embeddings_router
from app.api.routes.health import router as health_router
from app.api.routes.persona import router as persona_router
from app.api.routes.persona_embeddings import router as persona_embeddings_router
from app.api.routes.providers import router as providers_router
from app.api.routes.review_intelligence import router as review_intelligence_router
from app.core.config import get_settings
from app.db.session import create_db_tables

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_tables()


app.include_router(health_router)
app.include_router(providers_router)
app.include_router(embeddings_router)
app.include_router(persona_router)
app.include_router(persona_embeddings_router)
app.include_router(review_intelligence_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.app_env,
    }