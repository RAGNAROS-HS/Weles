from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["data"])


@router.delete("/data", status_code=204)
async def clear_data() -> Response:
    from alembic import command
    from alembic.config import Config

    from weles.utils.paths import resource_path

    cfg = Config(str(resource_path("alembic.ini")))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return Response(status_code=204)
