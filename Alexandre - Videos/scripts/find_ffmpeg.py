"""Localiza o binário do ffmpeg (winget não atualiza PATH de shells abertos)."""
import glob
import os
import shutil
from pathlib import Path

FULL_BIN = None  # cache


def find_ffmpeg() -> str:
    global FULL_BIN
    if FULL_BIN:
        return FULL_BIN
    # 1) PATH (funciona em shells novos)
    p = shutil.which("ffmpeg")
    if p:
        FULL_BIN = p
        return p
    # 2) WinGet packages (preferir full_build 9.0.2)
    patterns = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe"),
    ]
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(pat))
    if not candidates:
        raise FileNotFoundError(
            "ffmpeg nao encontrado. Instale com: winget install --id Gyan.FFmpeg -e"
        )
    # prioriza full_build (nao 'essentials')
    full = [c for c in candidates if "essentials" not in c.lower()]
    FULL_BIN = sorted(full or candidates)[-1]
    return FULL_BIN


if __name__ == "__main__":
    print(find_ffmpeg())
