import pytest

from weles.agent.client import get_client
from weles.utils.errors import ConfigurationError


def test_get_client_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        get_client()
