"""Baixa o modelo Whisper com retomada automática (download pode travar na rede).

Uso: python scripts/download_model.py [tamanho]
  tamanho: 'medium' (padrão) ou 'small'

O huggingface_hub retoma de onde parou (.incomplete). Este script apenas
repete a chamada enquanto ela falhar/estagnar, com limite de tentativas.
"""
import os
import sys
import time
from pathlib import Path

# timeouts p/ nao ficar preso em conexao morta (segundos)
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")

from huggingface_hub import hf_hub_download

MODEL = sys.argv[1] if len(sys.argv) > 1 else "medium"
REPO = f"Systran/faster-whisper-{MODEL}"
MAX_TRIES = 30


def incomplete_size() -> int:
    root = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{REPO.replace('/', '--')}"
    if not root.exists():
        return 0
    return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())


for attempt in range(1, MAX_TRIES + 1):
    before = incomplete_size()
    print(f"[tentativa {attempt}/{MAX_TRIES}] modelo={MODEL} cache_local={before/1024/1024:.0f}MB",
          flush=True)
    try:
        path = hf_hub_download(REPO, "model.bin")
        print(f"DOWNLOAD COMPLETO -> {path}", flush=True)
        break
    except Exception as exc:  # noqa: BLE001 - qualquer erro de rede: tentar de novo
        time.sleep(5)
        after = incomplete_size()
        print(f"  erro/estagnação: {type(exc).__name__}: {exc} | cache {after/1024/1024:.0f}MB "
              f"(+{(after-before)/1024/1024:.1f}MB nesta tentativa)", flush=True)
        if after > before:
            print("  progresso foi feito; retomando...", flush=True)
else:
    sys.exit(f"FALHOU apos {MAX_TRIES} tentativas (rede instavel).")
