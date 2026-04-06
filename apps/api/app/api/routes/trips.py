from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.trip_plan import (
    SavedTripListResponse,
    SavedTripSummaryResponse,
    TripPromoteRequest,
    TripSignalCreateRequest,
    TripSignalListResponse,
    TripSignalResponse,
    TripStatusUpdateRequest,
    TripVersionListResponse,
    TripVersionResponse,
    TripVersionRestoreRequest,
    TripVersionSnapshotRequest,
)
from app.services.trip_plan_service import (
    create_trip_signal,
    create_trip_version_snapshot,
    delete_saved_trip,
    get_current_trip_version,
    get_saved_trip_summary,
    list_saved_trips,
    list_trip_signals,
    list_trip_versions,
    promote_trip_plan_to_saved_trip,
    restore_trip_version,
    update_trip_status,
)

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/from-plan/{planning_session_id}", response_model=SavedTripSummaryResponse)
def create_saved_trip_from_plan(
    planning_session_id: str,
    payload: TripPromoteRequest,
    db: Session = Depends(get_db),
) -> SavedTripSummaryResponse:
    try:
        return promote_trip_plan_to_saved_trip(db, planning_session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=SavedTripListResponse)
def get_saved_trips(
    traveller_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SavedTripListResponse:
    return list_saved_trips(db, traveller_id=traveller_id, limit=limit)


@router.get("/{trip_id}", response_model=SavedTripSummaryResponse)
def get_saved_trip(
    trip_id: str,
    db: Session = Depends(get_db),
) -> SavedTripSummaryResponse:
    try:
        return get_saved_trip_summary(db, trip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{trip_id}/status", response_model=SavedTripSummaryResponse)
def patch_trip_status(
    trip_id: str,
    payload: TripStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> SavedTripSummaryResponse:
    try:
        return update_trip_status(db, trip_id=trip_id, new_status=payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: str,
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_saved_trip(db, trip_id=trip_id)
        return Response(status_code=204)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/versions", response_model=TripVersionListResponse)
def get_trip_versions(
    trip_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TripVersionListResponse:
    try:
        return list_trip_versions(db, trip_id=trip_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{trip_id}/versions", response_model=TripVersionResponse)
def create_version_snapshot(
    trip_id: str,
    payload: TripVersionSnapshotRequest,
    db: Session = Depends(get_db),
) -> TripVersionResponse:
    try:
        return create_trip_version_snapshot(db, trip_id=trip_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/versions/current", response_model=TripVersionResponse)
def get_current_version(
    trip_id: str,
    db: Session = Depends(get_db),
) -> TripVersionResponse:
    try:
        return get_current_trip_version(db, trip_id=trip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{trip_id}/versions/{version_id}/restore", response_model=SavedTripSummaryResponse)
def restore_version_snapshot(
    trip_id: str,
    version_id: str,
    payload: TripVersionRestoreRequest,
    db: Session = Depends(get_db),
) -> SavedTripSummaryResponse:
    try:
        return restore_trip_version(db, trip_id=trip_id, version_id=version_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/signals", response_model=TripSignalListResponse)
def get_trip_signals(
    trip_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> TripSignalListResponse:
    try:
        return list_trip_signals(db, trip_id=trip_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{trip_id}/signals", response_model=TripSignalResponse)
def create_signal(
    trip_id: str,
    payload: TripSignalCreateRequest,
    db: Session = Depends(get_db),
) -> TripSignalResponse:
    try:
        return create_trip_signal(db, trip_id=trip_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
