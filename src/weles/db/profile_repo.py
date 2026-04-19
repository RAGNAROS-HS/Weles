import json
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from weles.db.connection import get_db
from weles.profile.models import Preference, UserProfile

logger = logging.getLogger(__name__)

_PROFILE_COLUMN_MAP: dict[str, str] = {
    "height_cm": "height_cm",
    "weight_kg": "weight_kg",
    "build": "build",
    "fitness_level": "fitness_level",
    "injury_history": "injury_history",
    "dietary_restrictions": "dietary_restrictions",
    "dietary_preferences": "dietary_preferences",
    "dietary_approach": "dietary_approach",
    "aesthetic_style": "aesthetic_style",
    "brand_rejections": "brand_rejections",
    "climate": "climate",
    "activity_level": "activity_level",
    "living_situation": "living_situation",
    "country": "country",
    "budget_psychology": "budget_psychology",
    "fitness_goal": "fitness_goal",
    "dietary_goal": "dietary_goal",
    "lifestyle_focus": "lifestyle_focus",
}

_PROFILE_FIELDS = set(_PROFILE_COLUMN_MAP.keys())

_UPDATE_SQLS: dict[str, str] = {
    field: f"UPDATE profile SET {col} = ? WHERE id = 1"
    for field, col in _PROFILE_COLUMN_MAP.items()
}


def get_profile() -> UserProfile:
    conn = get_db()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if row is None:
        return UserProfile()
    try:
        return UserProfile.model_validate(dict(row))
    except ValidationError:
        logger.exception("Profile row contains invalid data; returning empty profile")
        return UserProfile()


def update_profile(patch: dict[str, Any]) -> UserProfile:
    unknown = set(patch) - _PROFILE_FIELDS
    if unknown:
        raise ValueError(f"Unknown profile fields: {sorted(unknown)}")

    conn = get_db()
    existing = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()

    if existing is None:
        conn.execute("INSERT INTO profile (id, field_timestamps) VALUES (1, '{}')")
        conn.commit()
        existing = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()

    timestamps = json.loads(existing["field_timestamps"] or "{}")
    now_iso = datetime.utcnow().isoformat()

    for field, value in patch.items():
        conn.execute(_UPDATE_SQLS[field], (value,))
        timestamps[field] = now_iso

    conn.execute(
        "UPDATE profile SET field_timestamps = ? WHERE id = 1",
        (json.dumps(timestamps),),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    try:
        return UserProfile.model_validate(dict(row))
    except ValidationError:
        logger.exception("Profile row contains invalid data after update; returning empty profile")
        return UserProfile()


def update_preference(
    dimension: str,
    value: str,
    reason: str | None = None,
    source: str = "user_explicit",
) -> None:
    """Upsert a preference row. Updates value/reason/source if the dimension already exists."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM preferences WHERE dimension = ?", (dimension,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE preferences SET value = ?, reason = ?, source = ?, created_at = ?"
            " WHERE dimension = ?",
            (value, reason, source, datetime.utcnow(), dimension),
        )
    else:
        conn.execute(
            "INSERT INTO preferences (id, dimension, value, reason, source, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), dimension, value, reason, source, datetime.utcnow()),
        )
    conn.commit()


def get_preferences() -> list[Preference]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM preferences ORDER BY created_at ASC").fetchall()
    result: list[Preference] = []
    for row in rows:
        try:
            result.append(Preference.model_validate(dict(row)))
        except ValidationError:
            logger.exception("Skipping invalid preference row id=%s", row["id"])
    return result


def set_first_session_at(dt: datetime) -> None:
    conn = get_db()
    existing = conn.execute("SELECT id FROM profile WHERE id = 1").fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO profile (id, first_session_at, field_timestamps) VALUES (1, ?, '{}')",
            (dt,),
        )
    else:
        conn.execute(
            "UPDATE profile SET first_session_at = ? WHERE id = 1 AND first_session_at IS NULL",
            (dt,),
        )
    conn.commit()
