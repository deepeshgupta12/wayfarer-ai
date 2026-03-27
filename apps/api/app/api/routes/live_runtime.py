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

@router.post("/monitor/inspect", response_model=ProactiveMonitorInspectResponse)
def inspect_trip_proactively(
    payload: ProactiveMonitorInspectRequest,
) -> ProactiveMonitorInspectResponse:
    db = get_db_session()
    try:
        try:
            return inspect_active_trip_alerts(db, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/alerts/{trip_id}", response_model=ProactiveAlertListResponse)
def get_proactive_alerts(
    trip_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
) -> ProactiveAlertListResponse:
    db = get_db_session()
    try:
        try:
            return list_proactive_alerts(db, trip_id=trip_id, status=status, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/alerts/{alert_id}/resolve", response_model=ProactiveAlertResponse)
def resolve_alert(
    alert_id: str,
    payload: ProactiveAlertResolutionRequest,
) -> ProactiveAlertResponse:
    db = get_db_session()
    try:
        try:
            return resolve_proactive_alert(db, alert_id=alert_id, payload=payload)
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