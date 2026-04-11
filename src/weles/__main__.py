import os


def main() -> None:
    import uvicorn

    from weles.api.startup import check_port_free

    check_port_free()

    port = int(os.getenv("WELES_PORT", "8000"))
    reload = os.getenv("WELES_ENV", "development") == "development"
    uvicorn.run(
        "weles.api.main:app",
        host="127.0.0.1",
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
