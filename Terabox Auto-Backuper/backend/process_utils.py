"""Execução de subprocessos sem abrir janelas de console no Windows.

Quando o app roda com ``pythonw.exe`` (sem console), qualquer processo de
console filho — como ``curl.exe``, ``tasklist`` ou ``powershell`` — faria o
Windows criar uma janela de console nova. Em uploads isso acontece a cada
arquivo/chunk, causando o "pisca-pisca" de CMDs.

As funções deste módulo aplicam ``CREATE_NO_WINDOW`` e escondem a janela
inicial, mantendo o processo totalmente funcional.
"""

import os
import subprocess
from typing import Any, Dict, Sequence

IS_WINDOWS = os.name == "nt"


def _make_startupinfo():
    """Cria STARTUPINFO configurado para não exibir janela (somente Windows)."""
    if not IS_WINDOWS:
        return None

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo


def hidden_kwargs(kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mescla opções para execução silenciosa de um subprocesso."""
    result = dict(kwargs or {})
    if IS_WINDOWS:
        flags = result.pop("creationflags", 0)
        result["creationflags"] = flags | subprocess.CREATE_NO_WINDOW
        # Respeita um startupinfo fornecido explicitamente pelo chamador.
        result.setdefault("startupinfo", _make_startupinfo())
    return result


def run_hidden(cmd: Sequence[str], **kwargs: Any):
    """Equivalente a ``subprocess.run``, sem abrir janela de console."""
    return subprocess.run(cmd, **hidden_kwargs(kwargs))


def popen_hidden(cmd: Sequence[str], **kwargs: Any):
    """Equivalente a ``subprocess.Popen``, sem abrir janela de console."""
    return subprocess.Popen(cmd, **hidden_kwargs(kwargs))
