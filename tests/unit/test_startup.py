import types

import pytest
from pytest_mock import MockerFixture

from weles.utils.errors import ConfigurationError


async def test_startup_raises_without_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from weles.api.startup import startup

    state = types.SimpleNamespace()
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        await startup(state)


async def test_startup_web_search_false_without_tavily(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.fixture,
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    mock_conn = mocker.MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [(4,), None]
    mocker.patch("weles.api.startup.get_db", return_value=mock_conn)
    mocker.patch("weles.api.startup.check_port_free")
    mocker.patch("alembic.command.upgrade")

    from weles.api import startup as startup_mod

    mocker.patch.object(startup_mod, "_WELES_DIR", tmp_path / ".weles")

    state = types.SimpleNamespace()
    await startup_mod.startup(state)

    assert state.web_search_available is False


async def test_startup_web_search_true_with_tavily(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.fixture,
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")

    mock_conn = mocker.MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [(4,), None]
    mocker.patch("weles.api.startup.get_db", return_value=mock_conn)
    mocker.patch("weles.api.startup.check_port_free")
    mocker.patch("alembic.command.upgrade")

    from weles.api import startup as startup_mod

    mocker.patch.object(startup_mod, "_WELES_DIR", tmp_path / ".weles")

    state = types.SimpleNamespace()
    await startup_mod.startup(state)

    assert state.web_search_available is True


async def test_startup_creates_weles_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.fixture,
    mocker: MockerFixture,
) -> None:
    weles_dir = tmp_path / ".weles"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")

    assert not weles_dir.exists()

    mock_conn = mocker.MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [(4,), None]
    mocker.patch("weles.api.startup.get_db", return_value=mock_conn)
    mocker.patch("weles.api.startup.check_port_free")
    mocker.patch("alembic.command.upgrade")

    from weles.api import startup as startup_mod

    mocker.patch.object(startup_mod, "_WELES_DIR", weles_dir)

    state = types.SimpleNamespace()
    await startup_mod.startup(state)

    assert weles_dir.exists()
