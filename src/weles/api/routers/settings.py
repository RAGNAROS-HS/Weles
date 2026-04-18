from typing import Any

from fastapi import APIRouter, HTTPException

from weles.db.settings_repo import get_all_settings, known_keys, set_setting

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict[str, Any]:
    return get_all_settings()


@router.patch("")
async def patch_settings(body: dict[str, Any]) -> dict[str, Any]:
    unknown = set(body.keys()) - known_keys()
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings keys: {sorted(unknown)}")
    for key, value in body.items():
        try:
            set_setting(key, value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return get_all_settings()
