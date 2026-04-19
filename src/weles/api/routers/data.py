import asyncio
import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

router = APIRouter(tags=["data"])


@router.delete("/data", status_code=204)
async def clear_data() -> Response:
    from alembic import command
    from alembic.config import Config

    from weles.utils.paths import resource_path

    cfg = Config(str(resource_path("alembic.ini")))
    await asyncio.to_thread(command.downgrade, cfg, "base")
    await asyncio.to_thread(command.upgrade, cfg, "head")
    return Response(status_code=204)


@router.get("/export")
async def export_data(format: Literal["json", "csv"] = "json") -> Response:
    from weles.db.connection import get_db

    conn = get_db()
    profile_row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    profile_data = dict(profile_row) if profile_row else {}
    preferences = [
        dict(r) for r in conn.execute("SELECT * FROM preferences ORDER BY created_at").fetchall()
    ]
    history = [
        dict(r) for r in conn.execute("SELECT * FROM history ORDER BY created_at").fetchall()
    ]

    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    if format == "csv":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("profile.csv", _dict_to_csv([profile_data]) if profile_data else "")
            zf.writestr("preferences.csv", _dict_to_csv(preferences) if preferences else "")
            zf.writestr("history.csv", _dict_to_csv(history) if history else "")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="weles-export-{date_str}.zip"'},
        )

    payload = json.dumps(
        {
            "exported_at": datetime.now(tz=UTC).isoformat(),
            "profile": profile_data,
            "preferences": preferences,
            "history": history,
        },
        default=str,
        indent=2,
    ).encode()
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="weles-export-{date_str}.json"'},
    )


def _dict_to_csv(rows: list[dict[str, object]]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
