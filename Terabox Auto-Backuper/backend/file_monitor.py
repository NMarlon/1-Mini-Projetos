"""Monitoramento de pastas via watchdog."""

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable, debounce_seconds: float = 2.0, loop=None):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.loop = loop
        self._last_event = 0.0
        self._pending = False

    def on_any_event(self, event: FileSystemEvent):
        if event.is_directory:
            return
        # Ignorar arquivos temporários
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


class FileMonitor:
    """Monitora pastas e dispara callback após debounce."""

    def __init__(self):
        self._observer: Optional[Observer] = None
        self._watched_paths: set = set()

    def start(self, paths: list, callback: Callable, debounce_seconds: float = 2.0):
        if self._observer is not None:
            self.stop()
        self._observer = Observer()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        watched_dirs = set()
        for p in paths:
            if not p:
                continue
            path = Path(p)
            # Para mapeamento de arquivo único, vigia a pasta pai.
            watch_dir = path if path.is_dir() else (path.parent if path.is_file() else None)
            if watch_dir is None or not watch_dir.is_dir():
                continue
            key = str(watch_dir.resolve()).lower()
            if key in watched_dirs:
                continue
            watched_dirs.add(key)
            handler = _DebouncedHandler(callback, debounce_seconds, loop=loop)
            self._observer.schedule(
                handler, str(watch_dir), recursive=path.is_dir()
            )
            self._watched_paths.add(str(watch_dir))
        self._observer.start()

    def stop(self):
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._watched_paths.clear()

    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()