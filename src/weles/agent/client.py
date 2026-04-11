import anthropic


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()
