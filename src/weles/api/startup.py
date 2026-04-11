import logging
import os
import socket
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from weles.db.connection import get_db
from weles.utils.errors import ConfigurationError

logger = logging.getLogger(__name__)

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
    """Exit with a readable message if WELES_PORT is already bound."""
    port = int(os.getenv("WELES_PORT", "8000"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        print(
            f"[ERROR] Port {port} is already in use."
            " Stop the existing Weles process and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        sock.close()


async def startup(state: Any) -> None:
    """Initialise app state: validate env, run migrations, seed settings."""
    # Derive weles dir from WELES_DB_PATH (defaults to ~/.weles)
    raw_db = os.getenv("WELES_DB_PATH", str(Path.home() / ".weles" / "weles.db"))
    weles_dir = Path(raw_db).expanduser().parent

    # 1. Load ~/.weles/.env if it exists — supplements env, does not override shell
    env_file = weles_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    # 2. Validate ANTHROPIC_API_KEY
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ConfigurationError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment or ~/.weles/.env."
        )

    # 3. Create weles dir if absent
    weles_dir.mkdir(parents=True, exist_ok=True)

    # 4. Run alembic upgrade head
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
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
