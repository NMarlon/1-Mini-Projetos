"""Monitoramento de pastas via watchdog."""

import asyncio
import os
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


def resolve_watch_target(path: str) -> Optional[Tuple[str, bool]]:
    """Diz qual pasta vigiar para um mapeamento e se deve ser recursivo.

    - pasta existente -> ela mesma, recursivo;
    - arquivo existente -> a pasta pai, não recursivo;
    - caminho inexistente -> o ancestral existente mais próximo, para
      detectar quando a pasta/arquivo for criado;
    - raiz de unidade -> não recursivo (evita vigiar o disco inteiro).
    """
    if not path:
        return None

    try:
        target = Path(path)
        if target.is_dir():
            return str(target), target.parent != target
        if target.is_file():
            return str(target.parent), False

        anchor = target.parent
        while not anchor.is_dir():
            if anchor.parent == anchor:
                return None
            anchor = anchor.parent
        return str(anchor), anchor.parent != anchor
    except OSError:
        return None


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(
        self,
        callback: Callable,
        debounce_seconds: float = 2.0,
        loop=None,
        monitor=None,
    ):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.loop = loop
        self.monitor = monitor
        self._last_event = 0.0
        self._pending = False

    def on_any_event(self, event: FileSystemEvent):
        # Eventos de diretório também importam: criar uma pasta vazia deve
        # disparar o sync para que ela apareça no Terabox.
        name = Path(event.src_path).name
        if name.startswith(".") or name.endswith((".tmp", ".part", "~")):
            return
        self._last_event = time.time()
        if not self._pending:
            self._pending = True
            if self.loop is not None:
                # O watchdog chama este handler em outra thread; o event loop
                # principal é quem deve criar a task assíncrona.
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(self._debounce())
                )
            else:
                asyncio.ensure_future(self._debounce())

    async def _debounce(self):
        await asyncio.sleep(self.debounce_seconds)
        self._pending = False
        try:
            await self.callback()
        except Exception:
            pass
        if self.monitor is not None:
            try:
                self.monitor.restart_if_ready()
            except Exception:
                pass


class FileMonitor:
    """Monitora pastas e dispara callback após debounce."""

    def __init__(self):
        self._observer: Optional[Observer] = None
        self._watched_paths: set = set()
        self._mappings: list = []
        self._callback: Optional[Callable] = None
        self._debounce_seconds: float = 2.0
        self._pending_paths: set = set()
        self._path_targets: dict = {}

    def start(self, mappings: list, callback: Callable, debounce_seconds: float = 2.0):
        """Inicia o monitor para uma lista de mapeamentos.

        Cada item pode ser um caminho ou um dict com ``local_path`` e
        ``is_file``. O tipo é usado apenas para validar o alvo; caminhos
        inexistentes vigiam o ancestral existente mais próximo.
        """
        if self._observer is not None:
            self.stop()
        self._mappings = list(mappings or [])
        self._callback = callback
        self._debounce_seconds = debounce_seconds
        self._observer = Observer()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        targets: dict = {}
        self._pending_paths = set()
        self._path_targets = {}

        for item in self._mappings:
            if isinstance(item, str):
                local_path = item
            elif isinstance(item, dict):
                local_path = item.get("local_path")
            else:
                local_path = None
            if not local_path:
                continue

            normalized_path = os.path.normcase(os.path.abspath(str(local_path)))
            if not os.path.exists(normalized_path):
                self._pending_paths.add(normalized_path)

            target = resolve_watch_target(str(local_path))
            if target is None:
                continue
            watch_dir, recursive = target
            try:
                resolved_dir = str(Path(watch_dir).resolve())
            except OSError:
                resolved_dir = os.path.abspath(watch_dir)
            key = os.path.normcase(resolved_dir)
            if key not in targets:
                targets[key] = (resolved_dir, recursive)
            elif recursive and not targets[key][1]:
                targets[key] = (resolved_dir, True)
            self._path_targets[normalized_path] = (key, recursive)

        for watch_dir, recursive in targets.values():
            try:
                if not os.path.isdir(watch_dir):
                    continue
                handler = _DebouncedHandler(
                    callback,
                    debounce_seconds,
                    loop=loop,
                    monitor=self,
                )
                self._observer.schedule(
                    handler, watch_dir, recursive=recursive
                )
                self._watched_paths.add(watch_dir)
            except Exception:
                continue
        self._observer.start()

    def restart_if_ready(self):
        """Recarrega o monitor quando um caminho pendente ficou mais próximo."""
        if not self._pending_paths:
            return False
        for path in list(self._pending_paths):
            target = resolve_watch_target(path)
            if target is None:
                continue
            watch_dir, recursive = target
            try:
                resolved_dir = str(Path(watch_dir).resolve())
            except OSError:
                resolved_dir = os.path.abspath(watch_dir)
            key = os.path.normcase(resolved_dir)
            if self._path_targets.get(path) != (key, recursive):
                self.start(
                    self._mappings,
                    self._callback,
                    self._debounce_seconds,
                )
                return True
        return False

    def stop(self):
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._watched_paths.clear()
        self._pending_paths.clear()
        self._path_targets.clear()

    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
