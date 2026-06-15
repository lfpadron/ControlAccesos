@echo off
setlocal

cd /d "%~dp0"

uv --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo No se encontro uv. Instala uv desde https://github.com/astral-sh/uv
  exit /b 1
)

uv run --with textual python tools\control_tui.py %*
exit /b %ERRORLEVEL%
