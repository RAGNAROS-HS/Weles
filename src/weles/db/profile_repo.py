import json
import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from weles.db.connection import get_db
from weles.profile.models import Preference, UserProfile

logger = logging.getLogger(__name__)

_PROFILE_FIELDS = {
    "height_cm",
    "weight_kg",
    "build",
    "fitness_level",
    "injury_history",
    "dietary_restrictions",
    "dietary_preferences",
    "dietary_approach",
    "aesthetic_style",
    "brand_rejections",
    "climate",
    "activity_level",
    "living_situation",
    "country",
    "budget_psychology",
    "fitness_goal",
    "dietary_goal",
    "lifestyle_focus",
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
        conn.execute(f"UPDATE profile SET {field} = ? WHERE id = 1", (value,))  # noqa: S608
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


def get_preferences() -> list[Preference]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM preferences ORDER BY created_at ASC").fetchall()
    return [Preference.model_validate(dict(row)) for row in rows]


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
