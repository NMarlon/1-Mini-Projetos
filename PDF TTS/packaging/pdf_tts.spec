# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec do Pathway PDF TTS portátil (Windows)."""

import shutil
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH é definido pelo PyInstaller
SRC = ROOT / "src"

datas = [
    (str(SRC / "pdf_tts" / "web"), "pdf_tts/web"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "samples"), "samples"),
]

binaries = []
for name in ("ffmpeg", "ffprobe"):
    path = shutil.which(name)
    if path:
        binaries.append((path, "."))
    else:
        print(f"AVISO: {name}.exe não encontrado no PATH; o app empacotado não conseguirá montar áudio.")

hiddenimports = collect_submodules("uvicorn") + [
    "pdf_tts.api",
    "tkinter",
    "tkinter.ttk",
    "anyio._backends._asyncio",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["reportlab", "pytest", "ruff", "pyinstaller", "httpx"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pathway PDF TTS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Pathway PDF TTS (PyInstaller)",
)
