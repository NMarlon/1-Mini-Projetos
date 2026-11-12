"""Entry point do Terabox Auto-Backuper."""

import sys
import os

# pythonw.exe não tem stdout/stderr. Redireciona para um arquivo de log
# para que o servidor funcione sem janela de console.
if sys.stdout is None or sys.stderr is None:
    _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = open(os.path.join(_log_dir, "app.log"), "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = _log_file
    if sys.stderr is None:
        sys.stderr = _log_file

import asyncio
import webbrowser
import socket
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import HOST, PORT, FRONTEND_DIR, DATA_DIR, PROJECT_DIR
from backend import database
from backend.api import router, file_monitor, sync_scheduler, sync_engine
from backend import auth


def _port_in_use(host, port):
    """Verifica se a porta já está em uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.init_db()

    # Configurar scheduler
    async def periodic_sync():
        await sync_engine.start_sync()

    sync_scheduler.set_callback(periodic_sync)
    await sync_scheduler.start()

    # Configurar file monitor (respeita a opção "Sync automático")
    async def monitor_sync():
        auto = await database.get_setting("auto_sync")
        if auto == "true":
            await sync_engine.start_sync()

    mappings = await database.fetch_all("SELECT local_path FROM mappings WHERE enabled = 1")
    paths = [m["local_path"] for m in mappings]
    file_monitor.start(paths, monitor_sync, debounce_seconds=2.0)

    # Ativar autostart se configurado
    from backend import windows_startup
    autostart = await database.get_setting("autostart")
    if autostart == "true":
        windows_startup.enable()

    # Primeiro salvamento do cadastro remoto (ou atualização do atalho) sem
    # bloquear a abertura da interface. Só roda se já houver autenticação.
    try:
        from backend.remote_config import remote_config_manager
        mapping_count = await database.fetch_one(
            "SELECT COUNT(*) AS total FROM mappings"
        )
        if (
            await auth.get_cached_auth()
            and mapping_count
            and int(mapping_count["total"]) > 0
        ):
            remote_config_manager.request_save("startup", delay=3.0)
    except Exception:
        pass

    yield

    # Shutdown
    file_monitor.stop()
    await sync_scheduler.stop()


app = FastAPI(title="Terabox Auto-Backuper", lifespan=lifespan)
app.include_router(router, prefix="/api")

# Servir frontend
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


def main():
    # Verificar se já há uma instância rodando
    already_running = _port_in_use(HOST, PORT)
    if not already_running:
        # Abrir navegador após um breve delay (para o servidor iniciar)
        import threading
        def _open_browser():
            import time
            time.sleep(2)
            webbrowser.open(f"http://{HOST}:{PORT}")
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()