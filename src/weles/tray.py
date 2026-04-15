"""Weles system tray entry point.

Start the FastAPI server in a daemon thread and manage the system tray icon.
This must be the PyInstaller entry point (``src/weles/tray.py``).
"""

# ruff: noqa: E402 — freeze_support() must be called before any other imports.
from __future__ import annotations

import multiprocessing

multiprocessing.freeze_support()

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import httpx
import pystray
import uvicorn
from dotenv import load_dotenv, set_key
from PIL import Image

from weles.utils.paths import resource_path

_WELES_DIR = Path.home() / ".weles"
_ENV_FILE = _WELES_DIR / ".env"


def _load_env() -> None:
    load_dotenv(override=False)
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE, override=False)


def _get_port() -> int:
    return int(os.getenv("WELES_PORT", "8000"))


def _port_in_use(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    try:
        sock.connect(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _open_browser(port: int) -> None:
    webbrowser.open(f"http://localhost:{port}")


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    """Poll GET /health until the server responds or timeout elapses."""
    deadline = time.monotonic() + timeout
    url = f"http://localhost:{port}/health"
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(url, timeout=1.0)
            if resp.is_success:
                return True
        except httpx.RequestError:
            pass
        time.sleep(0.5)
    return False


def _is_first_run(port: int) -> bool:
    try:
        resp = httpx.get(f"http://localhost:{port}/health", timeout=2.0)
        return bool(resp.json().get("first_run", False))
    except Exception:
        return False


def _change_port(icon: pystray.Icon) -> None:
    """Prompt the user to enter a new port and persist it to ~/.weles/.env."""
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    new_port = simpledialog.askstring(
        "Change port", "Enter new port number:", initialvalue=str(_get_port())
    )
    root.destroy()
    if new_port and new_port.strip().isdigit():
        _WELES_DIR.mkdir(parents=True, exist_ok=True)
        if not _ENV_FILE.exists():
            _ENV_FILE.touch()
        set_key(str(_ENV_FILE), "WELES_PORT", new_port.strip())
        os.environ["WELES_PORT"] = new_port.strip()
        icon.title = f"Weles (restart to apply port {new_port.strip()})"


def main() -> None:
    _load_env()

    port = _get_port()
    port_conflict = _port_in_use(port)

    icon_path = resource_path("assets/icon.ico")
    image = Image.open(icon_path)

    server: uvicorn.Server | None = None
    server_thread: threading.Thread | None = None

    if not port_conflict:
        config = uvicorn.Config(
            "weles.api.main:app",
            host="127.0.0.1",
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        server_thread = threading.Thread(
            target=server.run,
            daemon=True,
        )
        server_thread.start()

    def on_open(icon: pystray.Icon, item: pystray.MenuItem) -> None:  # noqa: ARG001
        _open_browser(_get_port())

    def on_restart(icon: pystray.Icon, item: pystray.MenuItem) -> None:  # noqa: ARG001
        nonlocal server, server_thread
        if server is not None:
            server.should_exit = True
            if server_thread is not None:
                server_thread.join(timeout=5)
        new_port = _get_port()
        new_config = uvicorn.Config(
            "weles.api.main:app",
            host="127.0.0.1",
            port=new_port,
            log_level="info",
        )
        server = uvicorn.Server(new_config)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()
        icon.title = f"Weles (port {new_port})"

    def on_quit(icon: pystray.Icon, item: pystray.MenuItem) -> None:  # noqa: ARG001
        icon.stop()
        if server is not None:
            server.should_exit = True
            if server_thread is not None:
                server_thread.join(timeout=5)
        sys.exit(0)

    if port_conflict:
        tooltip = f"Weles — Port {port} already in use"
        menu_items: list[pystray.MenuItem] = [
            pystray.MenuItem("Open", on_open, default=True),
            pystray.MenuItem("Change port", lambda icon, item: _change_port(icon)),
            pystray.MenuItem("Quit", on_quit),
        ]
    else:
        tooltip = f"Weles (port {port})"
        menu_items = [
            pystray.MenuItem("Open", on_open, default=True),
            pystray.MenuItem("Restart server", on_restart),
            pystray.MenuItem("Quit", on_quit),
        ]

    icon = pystray.Icon(
        name="Weles",
        icon=image,
        title=tooltip,
        menu=pystray.Menu(*menu_items),
    )

    # On first launch, open the browser automatically after the server is ready.
    if not port_conflict:

        def _auto_open_if_first_run() -> None:
            if _wait_for_server(port) and _is_first_run(port):
                _open_browser(port)

        threading.Thread(target=_auto_open_if_first_run, daemon=True).start()

    icon.run()


if __name__ == "__main__":
    main()
