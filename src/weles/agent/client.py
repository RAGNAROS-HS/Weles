import os

import anthropic

from weles.utils.errors import ConfigurationError


def get_client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ConfigurationError(
            "ANTHROPIC_API_KEY is not set. Add it to your environment or ~/.weles/.env."
        )
    return anthropic.Anthropic()
