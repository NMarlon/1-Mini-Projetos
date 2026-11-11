"""Gerenciamento de autostart no Windows via registro HKCU."""

import sys
import os
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "TeraboxAutoBackuper"


def _get_command() -> str:
    """Retorna o comando para iniciar o app em background."""
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    return f'"{pythonw}" "{app_path}"'


def is_enabled() -> bool:
    """Verifica se o autostart está habilitado."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, REG_VALUE_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable():
    """Habilita autostart."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, _get_command())
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable():
    """Desabilita autostart."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, REG_VALUE_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False