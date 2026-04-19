from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from weles.db.history_repo import delete_history_item, get_history

router = APIRouter(tags=["history"])


@router.get("/history")
async def list_history(
    domain: str | None = None,
    status: str | None = None,
    search: str | None = None,
    sort: Literal["newest", "oldest"] = "newest",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    return get_history(
        domain=domain, status=status, search=search, sort=sort, limit=limit, offset=offset
    )


@router.delete("/history/{item_id}", status_code=204)
async def delete_history(item_id: str) -> None:
    if not delete_history_item(item_id):
        raise HTTPException(status_code=404, detail="History item not found")
