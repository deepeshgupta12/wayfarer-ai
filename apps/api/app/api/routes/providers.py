from fastapi import APIRouter

from app.services.provider_service import get_provider_status

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/status")
def provider_status() -> dict:
    return get_provider_status()