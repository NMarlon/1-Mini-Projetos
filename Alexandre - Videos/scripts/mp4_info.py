"""Mostra info básica de um MP4 (duração) sem depender de ffprobe.

Uso: python scripts/mp4_info.py <video.mp4>
"""
import glob
import struct
import sys
from pathlib import Path


def duration(path: str) -> float:
    data = Path(path).read_bytes()
    i = data.find(b"mvhd")
    if i < 0:
        raise ValueError("mvhd nao encontrado (nao e mp4?)")
    ver = data[i + 4]
    if ver == 0:
        ts, dur = struct.unpack(">II", data[i + 16:i + 24])
    else:
        ts, dur = struct.unpack(">IQ", data[i + 24:i + 36])
    return dur / ts


def main() -> None:
    if len(sys.argv) < 2:
        # fallback: primeiro mp4 de exemplo
        cands = glob.glob(r"C:\MarlonScripts\1-Mini-Projetos\Alexandre - Videos\**\*.mp4",
                          recursive=True)
        if not cands:
            sys.exit("nenhum mp4 encontrado")
        path = cands[0]
    else:
        path = sys.argv[1]
    print(f"arquivo : {path}")
    print(f"tamanho : {Path(path).stat().st_size / (1024*1024):.1f} MB")
    print(f"duracao : {duration(path):.1f} s")


if __name__ == "__main__":
    main()
