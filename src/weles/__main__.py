import asyncio
import sys


async def _repl() -> None:
    from weles.agent.client import get_client
    from weles.agent.prompts import build_system_prompt
    from weles.agent.session import Session
    from weles.agent.stream import DoneEvent, TextDeltaEvent, stream_response

    client = get_client()
    session = Session()
    system = build_system_prompt("general", None)

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() == "exit":
            break

        if not user_input:
            continue

        session.add_message("user", user_input)

        print("Weles: ", end="", flush=True)
        reply_parts: list[str] = []
        async for event in stream_response(client, session.get_messages(), [], system):
            if isinstance(event, TextDeltaEvent):
                print(event.text, end="", flush=True)
                reply_parts.append(event.text)
            elif isinstance(event, DoneEvent):
                print()
        if reply_parts:
            session.add_message("assistant", "".join(reply_parts))


def main() -> None:
    from weles.utils.errors import ConfigurationError

    try:
        asyncio.run(_repl())
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
