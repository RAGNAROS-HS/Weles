.PHONY: dev build test lint install uninstall package

dev:
	npx concurrently \
		"cd frontend && npm run dev" \
		"uv run uvicorn src.weles.api.main:app --reload --port 8000"

build:
	cd frontend && npm run build

test:
	uv run pytest

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src/

package:
	cd frontend && npm run build
	uv run pyinstaller weles.spec --clean

install:
	powershell -NoProfile -ExecutionPolicy Bypass -Command "\
		\$$src = 'dist\\Weles.exe'; \
		\$$dst = \"\$$env:LOCALAPPDATA\\Weles\\Weles.exe\"; \
		\$$startup = \"\$$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Weles.lnk\"; \
		New-Item -ItemType Directory -Force -Path (Split-Path \$$dst) | Out-Null; \
		Copy-Item -Force \$$src \$$dst; \
		\$$ws = New-Object -ComObject WScript.Shell; \
		\$$lnk = \$$ws.CreateShortcut(\$$startup); \
		\$$lnk.TargetPath = \$$dst; \
		\$$lnk.WorkingDirectory = (Split-Path \$$dst); \
		\$$lnk.Save(); \
		Write-Host 'Installed Weles to' \$$dst; \
		Write-Host 'Startup shortcut created at' \$$startup \
	"

uninstall:
	powershell -NoProfile -ExecutionPolicy Bypass -Command "\
		\$$startup = \"\$$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Weles.lnk\"; \
		if (Test-Path \$$startup) { Remove-Item -Force \$$startup; Write-Host 'Removed startup shortcut.' } \
		else { Write-Host 'No startup shortcut found.' } \
	"
