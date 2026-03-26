from fastapi import APIRouter, HTTPException, Query

from app.db.session import get_db_session
from app.schemas.trip_plan import (
    SavedTripListResponse,
    SavedTripSummaryResponse,
    TripPromoteRequest,
    TripSignalCreateRequest,
    TripSignalListResponse,
    TripSignalResponse,
    TripVersionListResponse,
    TripVersionResponse,
    TripVersionRestoreRequest,
    TripVersionSnapshotRequest,
)
from app.services.trip_plan_service import (
    create_trip_signal,
    create_trip_version_snapshot,
    get_current_trip_version,
    get_saved_trip_summary,
    list_saved_trips,
    list_trip_signals,
    list_trip_versions,
    promote_trip_plan_to_saved_trip,
    restore_trip_version,
)

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/from-plan/{planning_session_id}", response_model=SavedTripSummaryResponse)
def create_saved_trip_from_plan(
    planning_session_id: str,
    payload: TripPromoteRequest,
) -> SavedTripSummaryResponse:
    db = get_db_session()
    try:
        try:
            return promote_trip_plan_to_saved_trip(db, planning_session_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("", response_model=SavedTripListResponse)
def get_saved_trips(
    traveller_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> SavedTripListResponse:
    db = get_db_session()
    try:
        return list_saved_trips(db, traveller_id=traveller_id, limit=limit)
    finally:
        db.close()


@router.get("/{trip_id}", response_model=SavedTripSummaryResponse)
def get_saved_trip(
    trip_id: str,
) -> SavedTripSummaryResponse:
    db = get_db_session()
    try:
        try:
            return get_saved_trip_summary(db, trip_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/{trip_id}/versions", response_model=TripVersionListResponse)
def get_trip_versions(
    trip_id: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> TripVersionListResponse:
    db = get_db_session()
    try:
        try:
            return list_trip_versions(db, trip_id=trip_id, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/{trip_id}/versions", response_model=TripVersionResponse)
def create_version_snapshot(
    trip_id: str,
    payload: TripVersionSnapshotRequest,
) -> TripVersionResponse:
    db = get_db_session()
    try:
        try:
            return create_trip_version_snapshot(db, trip_id=trip_id, payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()

@router.get("/{trip_id}/versions/current", response_model=TripVersionResponse)
def get_current_version(
    trip_id: str,
) -> TripVersionResponse:
    db = get_db_session()
    try:
        try:
            return get_current_trip_version(db, trip_id=trip_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/{trip_id}/versions/{version_id}/restore", response_model=SavedTripSummaryResponse)
def restore_version_snapshot(
    trip_id: str,
    version_id: str,
    payload: TripVersionRestoreRequest,
) -> SavedTripSummaryResponse:
    db = get_db_session()
    try:
        try:
            return restore_trip_version(db, trip_id=trip_id, version_id=version_id, payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/{trip_id}/signals", response_model=TripSignalListResponse)
def get_trip_signals(
    trip_id: str,
    limit: int = Query(default=100, ge=1, le=200),
) -> TripSignalListResponse:
    db = get_db_session()
    try:
        try:
            return list_trip_signals(db, trip_id=trip_id, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/{trip_id}/signals", response_model=TripSignalResponse)
def create_signal(
    trip_id: str,
    payload: TripSignalCreateRequest,
) -> TripSignalResponse:
    db = get_db_session()
    try:
        try:
            return create_trip_signal(db, trip_id=trip_id, payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()