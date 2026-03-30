from __future__ import annotations

from typing import Any
from collections import Counter

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.clients.google_places_client import GooglePlacesClient
from app.core.config import get_settings
from app.models.place_photo import PlacePhotoRecord
from app.schemas.destination import PlacePhotoAsset
from app.services.persona_embedding_service import calculate_persona_relevance_score

google_places_client = GooglePlacesClient()
settings = get_settings()


def _safe_aspect_ratio(width: int | None, height: int | None) -> float | None:
    if not width or not height or height == 0:
        return None
    return round(width / height, 4)


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = str(item).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _infer_scene_type(tags: list[str], category: str | None, caption: str | None) -> str:
    blob = " ".join(tags + [category or "", caption or ""]).lower()

    if any(term in blob for term in ["food", "market", "restaurant", "cafe", "coffee", "dining"]):
        return "food"
    if any(term in blob for term in ["culture", "heritage", "temple", "museum", "historic", "shrine"]):
        return "culture"
    if any(term in blob for term in ["nature", "park", "garden", "river", "scenic", "bamboo"]):
        return "nature"
    if any(term in blob for term in ["nightlife", "bar", "cocktail", "evening", "neon"]):
        return "nightlife"
    if any(term in blob for term in ["luxury", "boutique", "fine", "upscale"]):
        return "luxury"

    return "city"


def _build_visual_embedding_text(
    *,
    place_name: str,
    city: str,
    country: str,
    category: str,
    scene_type: str,
    tags: list[str],
    caption: str | None,
) -> str:
    tags_text = ", ".join(tags) if tags else "travel"
    return (
        f"place={place_name}; "
        f"city={city}; "
        f"country={country}; "
        f"category={category}; "
        f"scene_type={scene_type}; "
        f"tags={tags_text}; "
        f"caption={caption or 'none'}"
    )


def _contextual_visual_bonus(
    *,
    tags: list[str],
    scene_type: str,
    traveller_type: str | None,
    interests: list[str],
    context_tags: list[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    tag_set = set(_unique_strings(tags + [scene_type]))

    for interest in interests[:3]:
        normalized_interest = interest.strip().lower()
        if normalized_interest in tag_set:
            score += 5.0
            reasons.append(f"matches your {normalized_interest} preference")

    if traveller_type == "couple" and any(tag in tag_set for tag in ["romantic", "ambience", "scenic", "evening"]):
        score += 2.5
        reasons.append("fits a couple-oriented visual vibe")
    elif traveller_type == "family" and any(tag in tag_set for tag in ["family", "park", "open", "daytime"]):
        score += 2.5
        reasons.append("fits a family-friendly visual vibe")
    elif traveller_type == "solo" and any(tag in tag_set for tag in ["local", "walkable", "culture", "coffee"]):
        score += 2.0
        reasons.append("fits a solo-exploration visual vibe")
    elif traveller_type == "friends" and any(tag in tag_set for tag in ["nightlife", "food", "city", "energy"]):
        score += 2.5
        reasons.append("fits a friends-trip visual vibe")

    for context_tag in context_tags:
        normalized_context = context_tag.strip().lower()
        if normalized_context in tag_set:
            score += 3.0
            reasons.append(f"fits the current {normalized_context} context")

    return score, reasons


def _slot_context_tags(slot_type: str | None) -> list[str]:
    if slot_type == "lunch":
        return ["food", "market", "daytime"]
    if slot_type == "evening":
        return ["evening", "nightlife", "ambience"]
    if slot_type == "morning":
        return ["culture", "nature", "calm"]
    if slot_type == "afternoon":
        return ["culture", "scenic", "city"]
    return []


def _build_photo_reason(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    return "Ranked highly because it " + "; ".join(reasons[:3]) + "."


def _upsert_place_photo(
    db: Session,
    *,
    location_id: str,
    photo: dict[str, Any],
    category: str,
) -> PlacePhotoRecord:
    photo_id = str(photo.get("photo_id") or "").strip()
    if not photo_id:
        raise ValueError("photo_id is required for photo persistence.")

    width = int(photo.get("width")) if photo.get("width") is not None else None
    height = int(photo.get("height")) if photo.get("height") is not None else None
    tags = _unique_strings(list(photo.get("tags") or []))
    caption = str(photo.get("caption") or "").strip() or None
    scene_type = str(photo.get("scene_type") or "").strip() or _infer_scene_type(tags, category, caption)
    quality_score = float(photo.get("quality_score") or 0.0)

    record = (
        db.query(PlacePhotoRecord)
        .filter(PlacePhotoRecord.photo_id == photo_id)
        .first()
    )

    if record is None:
        record = PlacePhotoRecord(
            photo_id=photo_id,
            location_id=location_id,
            image_url=str(photo.get("image_url") or ""),
            source=str(photo.get("source") or "google_places"),
            width=width,
            height=height,
            aspect_ratio=_safe_aspect_ratio(width, height),
            caption=caption,
            tags=tags,
            scene_type=scene_type,
            quality_score=quality_score,
            metadata={
                "provider_payload": dict(photo),
            },
        )
        db.add(record)
    else:
        record.location_id = location_id
        record.image_url = str(photo.get("image_url") or record.image_url)
        record.source = str(photo.get("source") or record.source)
        record.width = width
        record.height = height
        record.aspect_ratio = _safe_aspect_ratio(width, height)
        record.caption = caption
        record.tags = tags
        record.scene_type = scene_type
        record.quality_score = quality_score
        record.metadata = {
            "provider_payload": dict(photo),
        }

    return record


def ingest_place_photos(
    db: Session,
    *,
    location_id: str,
    place_name: str,
    city: str,
    country: str,
    category: str,
    limit: int | None = None,
) -> list[PlacePhotoRecord]:
    resolved_limit = limit or settings.photo_default_limit

    provider_photos = google_places_client.get_place_photos(
        location_id=location_id,
        name=place_name,
        city=city,
        country=country,
        category=category,
        limit=resolved_limit,
    )

    persisted: list[PlacePhotoRecord] = []
    for photo in provider_photos[:resolved_limit]:
        record = _upsert_place_photo(
            db,
            location_id=location_id,
            photo=photo,
            category=category,
        )
        persisted.append(record)

    db.commit()

    return (
        db.query(PlacePhotoRecord)
        .filter(PlacePhotoRecord.location_id == location_id)
        .order_by(desc(PlacePhotoRecord.quality_score), desc(PlacePhotoRecord.id))
        .limit(resolved_limit)
        .all()
    )


def get_ranked_place_photos(
    db: Session,
    *,
    location_id: str,
    place_name: str,
    city: str,
    country: str,
    category: str,
    traveller_id: str | None = None,
    traveller_type: str | None = None,
    interests: list[str] | None = None,
    context_tags: list[str] | None = None,
    limit: int | None = None,
) -> list[PlacePhotoAsset]:
    if not settings.photo_intelligence_enabled:
        return []

    resolved_limit = limit or settings.photo_card_limit
    resolved_interests = list(interests or [])
    resolved_context_tags = _unique_strings(list(context_tags or []))

    records = (
        db.query(PlacePhotoRecord)
        .filter(PlacePhotoRecord.location_id == location_id)
        .order_by(desc(PlacePhotoRecord.quality_score), desc(PlacePhotoRecord.id))
        .all()
    )

    if not records:
        records = ingest_place_photos(
            db,
            location_id=location_id,
            place_name=place_name,
            city=city,
            country=country,
            category=category,
            limit=max(resolved_limit, settings.photo_default_limit),
        )

    ranked_rows: list[tuple[float, PlacePhotoAsset]] = []

    for record in records:
        tags = _unique_strings(list(record.tags or []))
        scene_type = str(record.scene_type or _infer_scene_type(tags, category, record.caption))

        score = float(record.quality_score or 0.0)
        reasons: list[str] = []

        contextual_bonus, contextual_reasons = _contextual_visual_bonus(
            tags=tags,
            scene_type=scene_type,
            traveller_type=traveller_type,
            interests=resolved_interests,
            context_tags=resolved_context_tags,
        )
        score += contextual_bonus
        reasons.extend(contextual_reasons)

        persona_relevance_score: float | None = None
        if traveller_id:
            persona_relevance_score = calculate_persona_relevance_score(
                db=db,
                traveller_id=traveller_id,
                text=_build_visual_embedding_text(
                    place_name=place_name,
                    city=city,
                    country=country,
                    category=category,
                    scene_type=scene_type,
                    tags=tags,
                    caption=record.caption,
                ),
            )
            score += (persona_relevance_score or 0.0) * 10.0
            if persona_relevance_score is not None and persona_relevance_score >= 0.72:
                reasons.append("shows a strong visual fit for this traveller")

        asset = PlacePhotoAsset(
            photo_id=record.photo_id,
            location_id=record.location_id,
            image_url=record.image_url,
            source=record.source,
            width=record.width,
            height=record.height,
            aspect_ratio=record.aspect_ratio,
            caption=record.caption,
            tags=tags,
            scene_type=scene_type,
            visual_score=round(score, 1),
            why_ranked=_build_photo_reason(reasons),
        )
        ranked_rows.append((asset.visual_score, asset))

    ranked_rows.sort(key=lambda item: item[0], reverse=True)
    return [asset for _, asset in ranked_rows[:resolved_limit]]


def enrich_place_payload_with_ranked_photos(
    db: Session,
    *,
    payload: dict[str, Any],
    traveller_id: str | None = None,
    traveller_type: str | None = None,
    interests: list[str] | None = None,
    context_tags: list[str] | None = None,
    limit: int | None = None,
    output_field: str = "photos",
) -> dict[str, Any]:
    location_id = str(payload.get("location_id") or "").strip()
    name = str(payload.get("name") or "").strip()
    city = str(payload.get("city") or "Unknown").strip()
    country = str(payload.get("country") or "Unknown").strip()
    category = str(payload.get("category") or "place").strip()

    if not location_id or not name:
        enriched = dict(payload)
        enriched[output_field] = []
        return enriched

    photos = get_ranked_place_photos(
        db,
        location_id=location_id,
        place_name=name,
        city=city,
        country=country,
        category=category,
        traveller_id=traveller_id,
        traveller_type=traveller_type,
        interests=interests,
        context_tags=context_tags,
        limit=limit,
    )

    enriched = dict(payload)
    enriched[output_field] = [item.model_dump(mode="json") for item in photos]
    return enriched

def build_deep_cv_research_summary(
    photos: list[PlacePhotoAsset],
) -> dict[str, Any]:
    limited = photos[: settings.photo_research_sample_limit]
    scene_counter = Counter(photo.scene_type or "unknown" for photo in limited)
    tag_counter = Counter(
        tag
        for photo in limited
        for tag in list(photo.tags or [])
    )

    return {
        "enabled": settings.photo_deep_cv_research_enabled,
        "mode": "future_ready_placeholder",
        "sampled_photo_count": len(limited),
        "dominant_scene_types": [
            {"scene_type": scene_type, "count": count}
            for scene_type, count in scene_counter.most_common(4)
        ],
        "dominant_tags": [
            {"tag": tag, "count": count}
            for tag, count in tag_counter.most_common(8)
        ],
        "next_step": (
            "Replace this lightweight abstraction with a deeper CV research pipeline "
            "when post-V3 model experimentation begins."
        ),
    }


def build_custom_training_summary(
    photos: list[PlacePhotoAsset],
) -> dict[str, Any]:
    scene_types = sorted(
        {
            photo.scene_type
            for photo in photos
            if photo.scene_type
        }
    )
    tags = sorted(
        {
            tag
            for photo in photos
            for tag in list(photo.tags or [])
            if tag
        }
    )

    return {
        "enabled": settings.photo_custom_training_enabled,
        "mode": "future_ready_placeholder",
        "training_ready_signal": bool(photos),
        "photo_count": len(photos),
        "scene_type_coverage": scene_types[:12],
        "tag_coverage": tags[:20],
        "next_step": (
            "Use these persisted metadata distributions as seed inputs for future "
            "custom large-scale visual model training beyond V3."
        ),
    }


def build_visual_runtime_signal(
    *,
    photos: list[PlacePhotoAsset],
    place_name: str,
) -> dict[str, Any]:
    if not settings.photo_runtime_visual_signals_enabled:
        return {
            "enabled": False,
            "place_name": place_name,
            "photo_count": 0,
            "top_scene_types": [],
            "top_tags": [],
            "deep_cv_research": build_deep_cv_research_summary([]),
            "custom_training": build_custom_training_summary([]),
        }

    scene_counter = Counter(photo.scene_type or "unknown" for photo in photos)
    tag_counter = Counter(
        tag
        for photo in photos
        for tag in list(photo.tags or [])
    )

    return {
        "enabled": True,
        "place_name": place_name,
        "photo_count": len(photos),
        "top_scene_types": [
            {"scene_type": scene_type, "count": count}
            for scene_type, count in scene_counter.most_common(4)
        ],
        "top_tags": [
            {"tag": tag, "count": count}
            for tag, count in tag_counter.most_common(8)
        ],
        "deep_cv_research": build_deep_cv_research_summary(photos),
        "custom_training": build_custom_training_summary(photos),
    }
