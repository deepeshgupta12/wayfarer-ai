from fastapi import APIRouter

from app.core.config import get_settings
from app.services.infra_service import get_infra_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/health/detailed")
def health_detailed() -> dict[str, object]:
    settings = get_settings()
    infra_status = get_infra_status()
    all_ok = all(infra_status.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "services": infra_status,
    }