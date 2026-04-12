import logging
import os
import socket
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from weles.db.connection import get_db
from weles.utils.errors import ConfigurationError
from weles.utils.paths import resource_path

logger = logging.getLogger(__name__)

_WELES_DIR = Path.home() / ".weles"

_DEFAULT_SETTINGS = [
    ("follow_up_cadence", '"off"'),
    ("proactive_surfacing", '"true"'),
    (
        "decay_thresholds",
        '{"goals": 60, "fitness_level": 90, "dietary_approach": 90,'
        ' "body_metrics": 180, "taste_lifestyle": 365}',
    ),
    ("max_tool_calls_per_turn", '"6"'),
]


def check_port_free() -> None:
    """Exit with a readable message if WELES_PORT is already bound by another process."""
    port = int(os.getenv("WELES_PORT", "8000"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    try:
        sock.connect(("127.0.0.1", port))
        # Connection succeeded — something else is already listening on this port
        sock.close()
        print(
            f"[ERROR] Port {port} is already in use."
            " Stop the existing Weles process and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError:
        # Connection refused or timed out — port is free
        pass
    finally:
        sock.close()


async def startup(state: Any) -> None:
    """Initialise app state: validate env, run migrations, seed settings."""
    # 1. Load repo-root .env then ~/.weles/.env — neither overrides shell env
    load_dotenv(override=False)
    env_file = _WELES_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    # 2. Validate ANTHROPIC_API_KEY
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ConfigurationError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment or ~/.weles/.env."
        )

    # 3. Create ~/.weles/ if absent
    _WELES_DIR.mkdir(parents=True, exist_ok=True)

    # Port conflict check — exit before serving if port is already bound
    check_port_free()

    # 4. Run alembic upgrade head
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(resource_path("alembic.ini")))
    command.upgrade(cfg, "head")

    # 5. Seed default settings if table is empty
    conn = get_db()
    count_row = conn.execute("SELECT COUNT(*) FROM settings").fetchone()
    if count_row[0] == 0:
        conn.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", _DEFAULT_SETTINGS)
        conn.commit()

    # 6. Check TAVILY_API_KEY
    if os.getenv("TAVILY_API_KEY"):
        state.web_search_available = True
    else:
        logger.warning("[WARN] Tavily key not set — web search disabled")
        state.web_search_available = False

    # 7. Set is_first_run based on profile.first_session_at
    profile_row = conn.execute("SELECT first_session_at FROM profile LIMIT 1").fetchone()
    state.is_first_run = profile_row is None or profile_row[0] is None
