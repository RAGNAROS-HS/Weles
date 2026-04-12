from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from weles.db.profile_repo import _PROFILE_FIELDS, get_profile, update_profile
from weles.profile.models import UserProfile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_profile_endpoint() -> UserProfile:
    return get_profile()


@router.patch("")
async def patch_profile(body: dict[str, Any]) -> UserProfile:
    unknown = set(body.keys()) - _PROFILE_FIELDS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
    try:
        validated = UserProfile.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    patch = validated.model_dump(exclude_unset=True, mode="json")
    return update_profile(patch)
