import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from weles.api.routers import data, history, messages, preferences, profile, sessions, settings
from weles.utils.paths import resource_path


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from weles.api.startup import startup

    await startup(app.state)
    yield


app = FastAPI(title="Weles", lifespan=lifespan)

# CORS — dev only (same-origin in production)
if os.getenv("WELES_ENV", "development") == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(profile.router)
app.include_router(history.router)
app.include_router(settings.router)
app.include_router(data.router)
app.include_router(preferences.router)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "web_search": app.state.web_search_available,
        "first_run": app.state.is_first_run,
    }


# Serve built frontend in production
_dist = resource_path("frontend/dist")
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
