from typing import Any

from fastapi import APIRouter, HTTPException

from weles.db.profile_repo import _PROFILE_FIELDS, get_profile, update_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_profile_endpoint() -> dict[str, Any]:
    return get_profile()


@router.patch("")
async def patch_profile(body: dict[str, Any]) -> dict[str, Any]:
    unknown = set(body.keys()) - _PROFILE_FIELDS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
    return update_profile(body)
