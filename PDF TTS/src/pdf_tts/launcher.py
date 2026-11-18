"""Launcher da interface local do Pathway PDF TTS."""

from __future__ import annotations

import faulthandler
import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler

from pdf_tts.config import ROOT

APP_ID = "pathway-pdf-tts"
APP_VERSION = "0.3.0"
_LOG_HANDLE = None
_CRASH_HANDLE = None
_LOGGING_READY = False


def _ensure_streams() -> None:
    """No .exe com --noconsole, sys.stdout/stderr são None; uvicorn exige streams."""
    global _LOG_HANDLE
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_HANDLE = (log_dir / "launcher.log").open("a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = _LOG_HANDLE
    if sys.stderr is None:
        sys.stderr = _LOG_HANDLE


def _configure_logging() -> None:
    global _CRASH_HANDLE, _LOGGING_READY
    if _LOGGING_READY:
        return
    _LOGGING_READY = True
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(getattr(handler, "_pathway_tts", False) for handler in root.handlers):
        handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler._pathway_tts = True  # type: ignore[attr-defined]
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    _CRASH_HANDLE = (log_dir / "crash.log").open("a", encoding="utf-8", buffering=1)
    faulthandler.enable(_CRASH_HANDLE)


def _free_port(start: int = 8765) -> int:
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("Não encontrei uma porta livre para a interface.")


def _health(port: int, timeout: float = 0.8) -> dict:
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - porta livre ou outro serviço
        return {}


def _find_existing_instance() -> int | None:
    for port in range(8765, 8796):
        data = _health(port)
        if data.get("app") == APP_ID:
            return port
    return None


def _wait_health(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _health(port).get("ok"):
            return True
        time.sleep(0.3)
    return False


def open_url(url: str) -> None:
    """Abre o navegador sem passar por cmd.exe (evita janelas de console)."""
    if os.name == "nt":
        os.startfile(url)  # noqa: S606 - URL local
    else:
        webbrowser.open(url)


def open_output_folder() -> None:
    output = ROOT / "output"
    output.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(output))  # noqa: S606 - pasta local do projeto


def run_serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    _ensure_streams()
    _configure_logging()
    import uvicorn

    logging.getLogger("pdf_tts.launcher").info("servidor manual em http://%s:%s", host, port)
    uvicorn.run("pdf_tts.api:app", host=host, port=port, log_level="warning")


def _show_existing_message(url: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print(f"O Pathway PDF TTS já está aberto em {url}")
        return
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Pathway PDF TTS",
        f"O Pathway PDF TTS já está aberto.\n\nA interface foi aberta no navegador:\n{url}",
    )
    root.destroy()


def run_gui() -> int:
    _ensure_streams()
    _configure_logging()
    logger = logging.getLogger("pdf_tts.launcher")

    existing = _find_existing_instance()
    if existing:
        url = f"http://127.0.0.1:{existing}/"
        logger.info("instância já aberta na porta %s", existing)
        open_url(url)
        _show_existing_message(url)
        return 0

    import uvicorn

    port = _free_port()
    config = uvicorn.Config("pdf_tts.api:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="pathway-tts-server", daemon=True)
    thread.start()
    logger.info("servidor iniciado na porta %s", port)

    url = f"http://127.0.0.1:{port}/"
    if not _wait_health(port):
        logger.error("a interface não respondeu na porta %s", port)
        print(f"Não foi possível iniciar a interface. Abra manualmente: {url}")
        return 1
    open_url(url)

    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError:
        print(f"Pathway PDF TTS rodando em {url}. Feche esta janela para encerrar.")
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
        return 0

    root = tk.Tk()
    root.title("Pathway PDF TTS")
    root.geometry("500x300")
    root.resizable(False, False)
    root.configure(padx=18, pady=16)

    ttk.Label(
        root,
        text="Pathway PDF TTS está rodando",
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        root,
        text="A interface abriu no navegador. Mantenha esta janela aberta enquanto usa o app.",
        wraplength=450,
    ).pack(anchor="w", pady=(6, 8))
    warning = ttk.Label(
        root,
        text="Se você fechar esta janela, o navegador perde a conexão.",
        foreground="#b42318",
        wraplength=450,
    )
    warning.pack(anchor="w", pady=(0, 10))
    ttk.Label(root, text=url, foreground="#2457d6").pack(anchor="w", pady=(0, 14))

    status = ttk.Label(root, text="Servidor ativo.", foreground="#087443")
    status.pack(anchor="w", pady=(0, 8))

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", pady=(8, 0))
    ttk.Button(buttons, text="Abrir interface", command=lambda: open_url(url)).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Abrir pasta dos áudios", command=open_output_folder).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Sair", command=root.destroy).pack(side="left")

    def check_server() -> None:
        if not thread.is_alive():
            status.configure(text="O servidor parou. Feche e abra o app novamente.", foreground="#b42318")
        else:
            root.after(3000, check_server)

    def on_close() -> None:
        if not messagebox.askokcancel(
            "Fechar o Pathway PDF TTS?",
            "Se fechar agora, o navegador perde a conexão e uma conversão em andamento será interrompida.\n\n"
            "Deseja realmente fechar?",
        ):
            return
        server.should_exit = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(3000, check_server)
    root.mainloop()
    server.should_exit = True
    logger.info("app encerrado")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui())
