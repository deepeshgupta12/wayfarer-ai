from fastapi import APIRouter, HTTPException

from app.db.session import get_db_session
from app.schemas.trip_plan import (
    TripBriefParseRequest,
    TripPlanEnrichResponse,
    TripPlanResponse,
    TripPlanSummaryResponse,
    TripPlanUpdateRequest,
    TripSlotReplacementRequest,
)
from app.services.trip_plan_service import (
    enrich_trip_plan,
    get_trip_plan_summary,
    parse_and_save_trip_brief,
    replace_trip_plan_slot,
    update_trip_plan,
)

router = APIRouter(prefix="/trip-plans", tags=["trip-plans"])


@router.post("/parse-and-save", response_model=TripPlanResponse)
def parse_trip_brief_and_create_plan(
    payload: TripBriefParseRequest,
) -> TripPlanResponse:
    db = get_db_session()
    try:
        return parse_and_save_trip_brief(db, payload)
    finally:
        db.close()


@router.patch("/{planning_session_id}", response_model=TripPlanSummaryResponse)
def update_saved_trip_plan(
    planning_session_id: str,
    payload: TripPlanUpdateRequest,
) -> TripPlanSummaryResponse:
    db = get_db_session()
    try:
        try:
            return update_trip_plan(db, planning_session_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/{planning_session_id}/replace-slot", response_model=TripPlanSummaryResponse)
def replace_saved_trip_plan_slot(
    planning_session_id: str,
    payload: TripSlotReplacementRequest,
) -> TripPlanSummaryResponse:
    db = get_db_session()
    try:
        try:
            return replace_trip_plan_slot(db, planning_session_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/{planning_session_id}/enrich", response_model=TripPlanEnrichResponse)
def enrich_saved_trip_plan(
    planning_session_id: str,
) -> TripPlanEnrichResponse:
    db = get_db_session()
    try:
        try:
            return enrich_trip_plan(db, planning_session_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/{planning_session_id}", response_model=TripPlanSummaryResponse)
def get_trip_plan(
    planning_session_id: str,
) -> TripPlanSummaryResponse:
    db = get_db_session()
    try:
        try:
            return get_trip_plan_summary(db, planning_session_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()