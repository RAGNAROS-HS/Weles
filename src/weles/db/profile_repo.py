import json
from datetime import datetime
from typing import Any

from weles.db.connection import get_db
from weles.profile.models import UserProfile

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
    return UserProfile.model_validate(dict(row))


def update_profile(patch: dict[str, Any]) -> UserProfile:
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
    return UserProfile.model_validate(dict(row))


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
