"""Entry point do executável portátil."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


def main() -> int:
    try:
        from pdf_tts.launcher import run_gui

        return run_gui()
    except Exception:  # noqa: BLE001 - grava diagnóstico quando não há console
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
        log_dir = base / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "launcher-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
