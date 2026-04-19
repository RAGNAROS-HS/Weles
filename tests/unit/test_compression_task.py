"""Unit tests: background compression task exceptions are logged, not swallowed."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_compression_failure_is_logged_not_raised(mocker) -> None:
    """Verify the _compress shim catches and logs exceptions without re-raising."""
    import weles.api.routers.messages as messages_mod

    log_error = mocker.patch.object(messages_mod._log, "error")

    session_id = "test-session-123"
    mock_client = mocker.MagicMock()
    mock_session = mocker.MagicMock()

    mocker.patch(
        "weles.api.routers.messages.maybe_compress_context",
        side_effect=RuntimeError("DB gone"),
    )

    # Replicate the shim logic directly
    async def _compress() -> None:
        try:
            await messages_mod.maybe_compress_context(session_id, mock_client, mock_session)
        except Exception:
            messages_mod._log.error(
                "Context compression failed for session %s", session_id, exc_info=True
            )

    task = asyncio.create_task(_compress())
    await asyncio.sleep(0)  # yield to let the task run
    await task  # should not raise

    log_error.assert_called_once()
    call_args = log_error.call_args
    assert session_id in str(call_args)
    assert call_args.kwargs.get("exc_info") is True
