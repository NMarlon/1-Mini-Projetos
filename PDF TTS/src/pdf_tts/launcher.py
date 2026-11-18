"""Launcher da interface local (um duplo clique)."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

from pdf_tts.config import ROOT

_LOG_HANDLE = None


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


def _wait_health(port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:  # noqa: BLE001 - servidor ainda subindo
            time.sleep(0.3)
    return False


def open_output_folder() -> None:
    output = ROOT / "output"
    output.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(output))  # noqa: S606 - pasta local do projeto


def run_serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    _ensure_streams()
    import uvicorn

    uvicorn.run("pdf_tts.api:app", host=host, port=port, log_level="warning")


def run_gui() -> int:
    _ensure_streams()
    import uvicorn

    port = _free_port()
    config = uvicorn.Config("pdf_tts.api:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="pdf-tts-server", daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    if not _wait_health(port):
        print(f"Não foi possível iniciar a interface. Abra manualmente: {url}")
        return 1
    webbrowser.open(url)

    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        print(f"PDF TTS rodando em {url}. Feche esta janela para encerrar.")
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
        return 0

    root = tk.Tk()
    root.title("PDF TTS")
    root.geometry("430x220")
    root.resizable(False, False)
    root.configure(padx=18, pady=16)

    ttk.Label(
        root,
        text="PDF TTS está rodando",
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        root,
        text="A interface abriu no navegador. Se não abriu, use o botão abaixo.",
        wraplength=390,
    ).pack(anchor="w", pady=(6, 12))
    ttk.Label(root, text=url, foreground="#2457d6").pack(anchor="w", pady=(0, 14))

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", pady=(8, 0))
    ttk.Button(buttons, text="Abrir interface", command=lambda: webbrowser.open(url)).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Abrir pasta dos áudios", command=open_output_folder).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Sair", command=root.destroy).pack(side="left")

    def on_close() -> None:
        server.should_exit = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui())
