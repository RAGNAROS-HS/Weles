import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_claude(mocker: MockerFixture) -> MagicMock:
    """Mock Anthropic client; stream yields a text delta then stops."""
    mock_client = MagicMock()

    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta = MagicMock()
    text_event.delta.type = "text_delta"
    text_event.delta.text = "Test."

    stop_event = MagicMock()
    stop_event.type = "message_stop"

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.__iter__ = MagicMock(return_value=iter([text_event, stop_event]))

    mock_client.messages.stream.return_value = mock_stream
    mocker.patch("src.weles.agent.client.get_client", return_value=mock_client)
    return mock_client  # type: ignore[no-any-return]


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Temporary SQLite DB with all Alembic migrations applied."""
    db_path = tmp_path / "weles.db"
    os.environ["WELES_DB_PATH"] = str(db_path)

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    yield db_path  # type: ignore[misc]

    del os.environ["WELES_DB_PATH"]


@pytest.fixture
def client(tmp_db: Path) -> object:
    """FastAPI TestClient wired to the temporary database."""
    from fastapi.testclient import TestClient
    from src.weles.api.main import app

    with TestClient(app) as c:
        yield c
