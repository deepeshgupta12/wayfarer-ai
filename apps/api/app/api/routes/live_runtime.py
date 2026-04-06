from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.rate_limiter import limiter
from app.db.session import get_db, get_db_session
from app.schemas.live_runtime import (
    AgentGraphEventListResponse,
    AgentGraphRunResponse,
    LiveActionWriteRequest,
    LiveActionWriteResponse,
    LiveRuntimeOrchestrateRequest,
    LiveRuntimeOrchestrateResponse,
    LiveTripContextResponse,
    LiveTripContextUpsertRequest,
    ProactiveAlertListResponse,
    ProactiveAlertResolutionRequest,
    ProactiveAlertResponse,
    ProactiveMonitorInspectRequest,
    ProactiveMonitorInspectResponse,
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
from app.services.proactive_notification_service import (
    inspect_active_trip_alerts,
    list_proactive_alerts,
    resolve_proactive_alert,
)

router = APIRouter(prefix="/live-runtime", tags=["live-runtime"])


# Streaming helper cannot use Depends — it's a plain generator, not a FastAPI endpoint.
def _stream_live_runtime_with_db_close(
    payload: LiveRuntimeOrchestrateRequest,
) -> Generator[str, None, None]:
    db = get_db_session()
    try:
        yield from stream_live_runtime(db, payload)
    finally:
        db.close()


@router.post("/context", response_model=LiveTripContextResponse)
def upsert_context(
    payload: LiveTripContextUpsertRequest,
    db: Session = Depends(get_db),
) -> LiveTripContextResponse:
    try:
        return upsert_live_trip_context(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/context/{trip_id}", response_model=LiveTripContextResponse)
def get_context(
    trip_id: str,
    db: Session = Depends(get_db),
) -> LiveTripContextResponse:
    try:
        return get_live_trip_context(db, trip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/actions", response_model=LiveActionWriteResponse)
def write_live_action(
    payload: LiveActionWriteRequest,
    db: Session = Depends(get_db),
) -> LiveActionWriteResponse:
    try:
        return write_live_action_to_memory(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/monitor/inspect", response_model=ProactiveMonitorInspectResponse)
@limiter.limit("10/minute")
def inspect_trip_proactively(
    request: Request,
    payload: ProactiveMonitorInspectRequest,
    db: Session = Depends(get_db),
) -> ProactiveMonitorInspectResponse:
    try:
        return inspect_active_trip_alerts(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/alerts/{trip_id}", response_model=ProactiveAlertListResponse)
def get_proactive_alerts(
    trip_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> ProactiveAlertListResponse:
    try:
        return list_proactive_alerts(db, trip_id=trip_id, status=status, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/alerts/{alert_id}/resolve", response_model=ProactiveAlertResponse)
def resolve_alert(
    alert_id: str,
    payload: ProactiveAlertResolutionRequest,
    db: Session = Depends(get_db),
) -> ProactiveAlertResponse:
    try:
        return resolve_proactive_alert(db, alert_id=alert_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orchestrate", response_model=LiveRuntimeOrchestrateResponse)
@limiter.limit("15/minute")
def orchestrate_live(
    request: Request,
    payload: LiveRuntimeOrchestrateRequest,
    db: Session = Depends(get_db),
) -> LiveRuntimeOrchestrateResponse:
    try:
        return orchestrate_live_runtime(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orchestrate/stream")
@limiter.limit("15/minute")
def orchestrate_live_stream(
    request: Request,
    payload: LiveRuntimeOrchestrateRequest,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_live_runtime_with_db_close(payload),
        media_type="application/x-ndjson",
    )


@router.get("/runs/{run_id}", response_model=AgentGraphRunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> AgentGraphRunResponse:
    try:
        return get_graph_run(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/events", response_model=AgentGraphEventListResponse)
def get_run_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> AgentGraphEventListResponse:
    try:
        return list_graph_events(db, run_id=run_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
