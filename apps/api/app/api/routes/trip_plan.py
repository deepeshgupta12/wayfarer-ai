from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db, get_db_session
from app.schemas.trip_plan import (
    TripBriefParseRequest,
    TripPlanEnrichResponse,
    TripPlanFromComparisonRequest,
    TripPlanResponse,
    TripPlanSummaryResponse,
    TripPlanUpdateRequest,
    TripSlotReplacementRequest,
)
from app.services.trip_plan_service import (
    enrich_trip_plan,
    get_trip_plan_summary,
    parse_and_save_trip_brief,
    parse_and_save_trip_from_comparison,
    replace_trip_plan_slot,
    stream_enrich_trip_plan,
    update_trip_plan,
)

router = APIRouter(prefix="/trip-plans", tags=["trip-plans"])


# Streaming helper cannot use Depends — it's a plain generator, not a FastAPI endpoint.
def _stream_enrich_with_db_close(
    planning_session_id: str,
) -> Generator[str, None, None]:
    db = get_db_session()
    try:
        yield from stream_enrich_trip_plan(db, planning_session_id)
    finally:
        db.close()


@router.post("/parse-and-save", response_model=TripPlanResponse)
def parse_trip_brief_and_create_plan(
    payload: TripBriefParseRequest,
    db: Session = Depends(get_db),
) -> TripPlanResponse:
    return parse_and_save_trip_brief(db, payload)


@router.post("/from-comparison", response_model=TripPlanResponse)
def create_plan_from_comparison(
    payload: TripPlanFromComparisonRequest,
    db: Session = Depends(get_db),
) -> TripPlanResponse:
    try:
        return parse_and_save_trip_from_comparison(db, payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{planning_session_id}", response_model=TripPlanSummaryResponse)
def update_saved_trip_plan(
    planning_session_id: str,
    payload: TripPlanUpdateRequest,
    db: Session = Depends(get_db),
) -> TripPlanSummaryResponse:
    try:
        return update_trip_plan(db, planning_session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{planning_session_id}/replace-slot", response_model=TripPlanSummaryResponse)
def replace_saved_trip_plan_slot(
    planning_session_id: str,
    payload: TripSlotReplacementRequest,
    db: Session = Depends(get_db),
) -> TripPlanSummaryResponse:
    try:
        return replace_trip_plan_slot(db, planning_session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{planning_session_id}/enrich", response_model=TripPlanEnrichResponse)
def enrich_saved_trip_plan(
    planning_session_id: str,
    db: Session = Depends(get_db),
) -> TripPlanEnrichResponse:
    try:
        return enrich_trip_plan(db, planning_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{planning_session_id}/enrich/stream")
def enrich_saved_trip_plan_stream(
    planning_session_id: str,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_enrich_with_db_close(planning_session_id),
        media_type="application/x-ndjson",
    )


@router.get("/{planning_session_id}", response_model=TripPlanSummaryResponse)
def get_trip_plan(
    planning_session_id: str,
    db: Session = Depends(get_db),
) -> TripPlanSummaryResponse:
    try:
        return get_trip_plan_summary(db, planning_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
