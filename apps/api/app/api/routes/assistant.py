from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db.session import get_db_session
from app.schemas.assistant import AssistantOrchestrateRequest, AssistantOrchestrateResponse
from app.services.assistant_service import orchestrate_assistant_request, stream_assistant_request

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/orchestrate", response_model=AssistantOrchestrateResponse)
def orchestrate_assistant(
    payload: AssistantOrchestrateRequest,
) -> AssistantOrchestrateResponse:
    db = get_db_session()
    try:
        return orchestrate_assistant_request(db, payload)
    finally:
        db.close()


@router.post("/orchestrate/stream")
def orchestrate_assistant_stream(
    payload: AssistantOrchestrateRequest,
) -> StreamingResponse:
    db = get_db_session()
    return StreamingResponse(
        stream_assistant_request(db, payload),
        media_type="application/x-ndjson",
        background=None,
    )