import pytest

from weles.utils.errors import ConfigurationError


def test_get_client_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from weles.agent import client as client_module
    import importlib

    importlib.reload(client_module)
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        client_module.get_client()
