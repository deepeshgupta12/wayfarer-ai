from fastapi import APIRouter, HTTPException

from app.db.session import get_db_session
from app.schemas.trip_plan import (
    TripBriefParseRequest,
    TripPlanResponse,
    TripPlanSummaryResponse,
)
from app.services.trip_plan_service import (
    get_trip_plan_summary,
    parse_and_save_trip_brief,
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