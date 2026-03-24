from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.persona import router as persona_router
from app.api.routes.providers import router as providers_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(providers_router)
app.include_router(persona_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.app_env,
    }