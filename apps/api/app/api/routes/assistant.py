from collections.abc import Generator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.rate_limiter import limiter
from app.db.session import get_db, get_db_session
from app.schemas.assistant import AssistantOrchestrateRequest, AssistantOrchestrateResponse
from app.services.assistant_service import orchestrate_assistant_request, stream_assistant_request

router = APIRouter(prefix="/assistant", tags=["assistant"])


# Streaming helper cannot use Depends — it's a plain generator, not a FastAPI endpoint.
def _stream_with_db_close(
    payload: AssistantOrchestrateRequest,
) -> Generator[str, None, None]:
    db = get_db_session()
    try:
        yield from stream_assistant_request(db, payload)
    finally:
        db.close()


@router.post("/orchestrate", response_model=AssistantOrchestrateResponse)
@limiter.limit("20/minute")
def orchestrate_assistant(
    request: Request,
    payload: AssistantOrchestrateRequest,
    db: Session = Depends(get_db),
) -> AssistantOrchestrateResponse:
    return orchestrate_assistant_request(db, payload)


@router.post("/orchestrate/stream")
@limiter.limit("20/minute")
def orchestrate_assistant_stream(
    request: Request,
    payload: AssistantOrchestrateRequest,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_with_db_close(payload),
        media_type="application/x-ndjson",
    )
