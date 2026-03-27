from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db.session import get_db_session
from app.schemas.live_runtime import (
    AgentGraphEventListResponse,
    AgentGraphRunResponse,
    LiveActionWriteRequest,
    LiveActionWriteResponse,
    LiveRuntimeOrchestrateRequest,
    LiveRuntimeOrchestrateResponse,
    LiveTripContextResponse,
    LiveTripContextUpsertRequest,
)
from app.services.live_runtime_service import (
    get_graph_run,
    get_live_trip_context,
    list_graph_events,
    orchestrate_live_runtime,
    stream_live_runtime,
    upsert_live_trip_context,
    write_live_action_to_memory,
)

router = APIRouter(prefix="/live-runtime", tags=["live-runtime"])


@router.post("/context", response_model=LiveTripContextResponse)
def upsert_context(
    payload: LiveTripContextUpsertRequest,
) -> LiveTripContextResponse:
    db = get_db_session()
    try:
        try:
            return upsert_live_trip_context(db, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/context/{trip_id}", response_model=LiveTripContextResponse)
def get_context(
    trip_id: str,
) -> LiveTripContextResponse:
    db = get_db_session()
    try:
        try:
            return get_live_trip_context(db, trip_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/actions", response_model=LiveActionWriteResponse)
def write_live_action(
    payload: LiveActionWriteRequest,
) -> LiveActionWriteResponse:
    db = get_db_session()
    try:
        try:
            return write_live_action_to_memory(db, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/orchestrate", response_model=LiveRuntimeOrchestrateResponse)
def orchestrate_live(
    payload: LiveRuntimeOrchestrateRequest,
) -> LiveRuntimeOrchestrateResponse:
    db = get_db_session()
    try:
        try:
            return orchestrate_live_runtime(db, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/orchestrate/stream")
def orchestrate_live_stream(
    payload: LiveRuntimeOrchestrateRequest,
) -> StreamingResponse:
    db = get_db_session()
    return StreamingResponse(
        stream_live_runtime(db, payload),
        media_type="application/x-ndjson",
        background=None,
    )


@router.get("/runs/{run_id}", response_model=AgentGraphRunResponse)
def get_run(
    run_id: str,
) -> AgentGraphRunResponse:
    db = get_db_session()
    try:
        try:
            return get_graph_run(db, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/runs/{run_id}/events", response_model=AgentGraphEventListResponse)
def get_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=500),
) -> AgentGraphEventListResponse:
    db = get_db_session()
    try:
        try:
            return list_graph_events(db, run_id=run_id, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()