from fastapi import FastAPI

app = FastAPI(title="Weles")

# Defaults before startup() is wired into lifespan (#5)
app.state.web_search_available = False
app.state.is_first_run = True


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "web_search": app.state.web_search_available,
        "first_run": app.state.is_first_run,
    }
