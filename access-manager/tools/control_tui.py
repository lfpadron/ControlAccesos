from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, RichLog, Static

SYSTEM_NAME = "Access Manager"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_URL = "http://localhost:8080/"
HEALTH_URL = "http://localhost:8080/api/health"


def command_text(command: Iterable[str]) -> str:
    return " ".join(command)


def health_is_ok() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def find_browser_executable() -> Path | None:
    if sys.platform != "win32":
        return None

    roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root:
            continue
        base = Path(root)
        candidates.extend(
            [
                base / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                base / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


class SystemControlApp(App[None]):
    TITLE = f"Control del Sistema {SYSTEM_NAME}"
    SUB_TITLE = "Podman Compose local"
    CSS = """
    Screen {
        layout: vertical;
        background: #101923;
        color: #edf4ff;
    }

    #title {
        content-align: center middle;
        height: 3;
        text-style: bold;
        background: #172333;
        color: #ffffff;
    }

    #status {
        height: 3;
        padding: 1 2;
        background: #0f1720;
        border-bottom: solid #2a3d52;
    }

    #body {
        layout: horizontal;
        height: 1fr;
    }

    #actions {
        width: 32;
        min-width: 28;
        padding: 1;
        background: #111c28;
        border-right: solid #2a3d52;
    }

    #actions Button {
        width: 100%;
        margin-bottom: 1;
    }

    #logs-panel {
        width: 1fr;
        padding: 1;
    }

    #logs-title {
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }

    #logs {
        height: 1fr;
        border: solid #2a3d52;
        background: #07111d;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.command_running = False
        self.browser_process: subprocess.Popen[bytes] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(f"Control del Sistema {SYSTEM_NAME}", id="title")
        yield Static("Estado: verificando...", id="status")
        with Horizontal(id="body"):
            with Vertical(id="actions"):
                yield Button("Arrancar podman", id="start-podman", variant="primary")
                yield Button("Construir aplicación", id="build-app", variant="warning")
                yield Button("Encender", id="turn-on", variant="success")
                yield Button("Abrir navegador", id="open-browser", variant="primary")
                yield Button("Apagar", id="turn-off", variant="error")
                yield Button("Cerrar", id="close", variant="default")
            with Vertical(id="logs-panel"):
                yield Static("Logs", id="logs-title")
                yield RichLog(id="logs", markup=True, wrap=True, highlight=True)
        yield Footer()

    async def on_mount(self) -> None:
        self.write_log("TUI lista. Use los botones para controlar el entorno local.")
        self.write_log(f"Raiz del proyecto: {PROJECT_ROOT}")
        await self.refresh_status()
        self.set_interval(5, self.refresh_status)

    def write_log(self, message: str, style: str | None = None) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[dim]{timestamp}[/dim] {message}"
        logs = self.query_one("#logs", RichLog)
        logs.write(line if style is None else f"[{style}]{line}[/{style}]")

    async def refresh_status(self) -> None:
        is_on = await asyncio.to_thread(health_is_ok)
        label = "encendido" if is_on else "apagado"
        color = "green" if is_on else "red"
        self.query_one("#status", Static).update(
            f"Estado: [{color}]{label.upper()}[/{color}]  |  URL local: {LOCAL_URL}"
        )

    def set_buttons_disabled(self, disabled: bool) -> None:
        for button in self.query(Button):
            if button.id != "close":
                button.disabled = disabled

    async def run_system_command(self, title: str, command: list[str]) -> None:
        if self.command_running:
            self.write_log("Ya hay una acción en ejecución.", "yellow")
            return

        self.command_running = True
        self.set_buttons_disabled(True)
        self.write_log(f"> {title}: {command_text(command)}", "cyan")
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=PROJECT_ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            async for raw_line in process.stdout:
                line = raw_line.decode(errors="replace").rstrip()
                if line:
                    self.write_log(line)
            code = await process.wait()
            if code == 0:
                self.write_log(f"{title} finalizó correctamente.", "green")
            else:
                self.write_log(f"{title} terminó con código {code}.", "red")
        except FileNotFoundError:
            self.write_log(f"No se encontro el comando: {command[0]}", "red")
        except Exception as exc:
            self.write_log(f"Error ejecutando {title}: {exc}", "red")
        finally:
            self.command_running = False
            self.set_buttons_disabled(False)
            await self.refresh_status()

    async def run_system_commands(self, title: str, commands: list[tuple[str, list[str]]]) -> None:
        if self.command_running:
            self.write_log("Ya hay una acción en ejecución.", "yellow")
            return

        self.command_running = True
        self.set_buttons_disabled(True)
        self.write_log(f"> {title}", "cyan")
        try:
            for step_title, command in commands:
                self.write_log(f"> {step_title}: {command_text(command)}", "cyan")
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=PROJECT_ROOT,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                assert process.stdout is not None
                async for raw_line in process.stdout:
                    line = raw_line.decode(errors="replace").rstrip()
                    if line:
                        self.write_log(line)
                code = await process.wait()
                if code != 0:
                    self.write_log(f"{step_title} terminó con código {code}.", "red")
                    return
                self.write_log(f"{step_title} finalizó correctamente.", "green")
            self.write_log(f"{title} finalizó correctamente.", "green")
        except FileNotFoundError as exc:
            self.write_log(f"No se encontro el comando: {exc.filename}", "red")
        except Exception as exc:
            self.write_log(f"Error ejecutando {title}: {exc}", "red")
        finally:
            self.command_running = False
            self.set_buttons_disabled(False)
            await self.refresh_status()

    @on(Button.Pressed, "#start-podman")
    def start_podman(self) -> None:
        self.run_worker(
            self.run_system_command("Arrancar podman", ["podman", "machine", "start"]),
            exclusive=False,
        )

    @on(Button.Pressed, "#build-app")
    def build_app(self) -> None:
        self.run_worker(
            self.run_system_command("Construir aplicación", ["podman", "compose", "build"]),
            exclusive=False,
        )

    @on(Button.Pressed, "#turn-on")
    def turn_on(self) -> None:
        self.run_worker(
            self.run_system_commands(
                "Encender",
                [
                    ("Encender servicios", ["podman", "compose", "up", "-d"]),
                    ("Aplicar migraciones", ["podman", "compose", "exec", "-T", "backend", "uv", "run", "alembic", "upgrade", "head"]),
                ],
            ),
            exclusive=False,
        )

    @on(Button.Pressed, "#open-browser")
    async def open_browser(self) -> None:
        self.write_log(f"Abriendo navegador en {LOCAL_URL}", "cyan")
        browser_path = find_browser_executable()
        if browser_path is not None:
            self.browser_process = subprocess.Popen(
                [str(browser_path), "--new-window", LOCAL_URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.write_log("Navegador abierto en una ventana nueva.", "green")
            return

        opened = await asyncio.to_thread(webbrowser.open, LOCAL_URL, 2)
        if opened:
            self.write_log("Navegador solicitado correctamente.", "green")
        else:
            self.write_log("No fue posible abrir el navegador automáticamente.", "red")

    def close_tracked_browser(self) -> None:
        if self.browser_process is None:
            self.write_log("No hay un proceso de navegador asociado a esta TUI.", "yellow")
            return
        if self.browser_process.poll() is not None:
            self.write_log("El navegador asociado ya estaba cerrado.", "yellow")
            self.browser_process = None
            return
        self.browser_process.terminate()
        self.write_log("Navegador abierto por la TUI cerrado.", "green")
        self.browser_process = None

    async def shutdown_system(self) -> None:
        self.close_tracked_browser()
        await self.run_system_command("Apagar", ["podman", "compose", "down"])

    @on(Button.Pressed, "#turn-off")
    def turn_off(self) -> None:
        self.run_worker(self.shutdown_system(), exclusive=False)

    @on(Button.Pressed, "#close")
    def close_app(self) -> None:
        self.exit()


def smoke_test() -> int:
    checks: list[tuple[str, bool, str]] = [
        ("compose.yaml", (PROJECT_ROOT / "compose.yaml").exists(), str(PROJECT_ROOT / "compose.yaml")),
        ("podman disponible", shutil.which("podman") is not None, shutil.which("podman") or "no encontrado"),
        ("raiz del proyecto", PROJECT_ROOT.name == "access-manager", str(PROJECT_ROOT)),
        ("textual importado", True, "ok"),
    ]

    for name, ok, detail in checks:
        status = "OK" if ok else "ERROR"
        print(f"{status}: {name} - {detail}")

    commands = {
        "Arrancar podman": ["podman", "machine", "start"],
        "Construir aplicación": ["podman", "compose", "build"],
        "Encender servicios": ["podman", "compose", "up", "-d"],
        "Aplicar migraciones": ["podman", "compose", "exec", "-T", "backend", "uv", "run", "alembic", "upgrade", "head"],
        "Apagar": ["podman", "compose", "down"],
    }
    for name, command in commands.items():
        print(f"CMD: {name}: {command_text(command)}")

    try:
        asyncio.run(textual_smoke_test())
        print("OK: textual headless - widgets principales montados")
    except Exception as exc:
        print(f"ERROR: textual headless - {exc}")
        return 1

    return 0 if all(ok for _, ok, _ in checks) else 1


async def textual_smoke_test() -> None:
    app = SystemControlApp()
    async with app.run_test(size=(110, 32)) as pilot:
        await pilot.pause(0.1)
        app.query_one("#status", Static)
        app.query_one("#logs", RichLog)
        assert len(list(app.query(Button))) == 6


def main() -> int:
    parser = argparse.ArgumentParser(description=f"TUI de control para {SYSTEM_NAME}.")
    parser.add_argument("--smoke-test", action="store_true", help="Valida dependencias básicas sin abrir la TUI.")
    args = parser.parse_args()

    if args.smoke_test:
        return smoke_test()

    SystemControlApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
