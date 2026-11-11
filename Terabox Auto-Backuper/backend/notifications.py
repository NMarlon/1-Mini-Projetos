"""Notificações toast do Windows."""

import asyncio
from backend.config import PROJECT_DIR


async def _send_toast(title: str, message: str):
    """Envia toast de forma não-bloqueante."""
    try:
        from winotify import Notification
        toast = Notification(
            app_id="Terabox Auto-Backuper",
            title=title,
            msg=message,
            duration="short",
        )
        toast.show()
    except ImportError:
        # Fallback: log no console
        print(f"[NOTIFICAÇÃO] {title}: {message}")
    except Exception as e:
        print(f"[NOTIFICAÇÃO ERRO] {e}")


async def notify_success(title: str, message: str):
    await _send_toast(title, message)


async def notify_error(title: str, message: str):
    await _send_toast(title, message)


async def notify_info(title: str, message: str):
    await _send_toast(title, message)