"""Corte rápido de um trecho (com opção de verticalização) — útil para preview/QA.

Uso:
    python scripts/cortar.py <video> --start 12.3 --dur 18 [--out work/corte.mp4]
                              [--vertical blurpad|crop] [--x 0.5] [--y 0.45]

blurpad = gameplay em faixa central com fundo desfocado (bom p/ fonte 360p)
crop    = recorte cheio 9:16 (upscalling maior, só vale p/ fonte 720p+)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--vertical", choices=["blurpad", "crop"], default="blurpad")
    ap.add_argument("--x", type=float, default=0.5, help="0..1 posição horizontal do crop")
    ap.add_argument("--y", type=float, default=0.45, help="0..1 altura da mira no quadro")
    args = ap.parse_args()

    video = Path(args.video)
    out = Path(args.out) if args.out else Path("work") / f"corte_{int(args.start)}s.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.vertical == "crop":
        # recorta 9:16 ja na resolucao alvo (upscalling do bruto)
        vf = (
            f"crop=w='min(iw\\,ih*9/16)':h='min(ih\\,iw*16/9)'"
            f":x='(iw-ow)*{args.x}':y='(ih-oh)*{args.y}',"
            "scale=1080:1920:flags=lanczos"
        )
    else:
        vf = (
            "split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=30,eq=brightness=-0.20:saturation=0.85[bgf];"
            "[fg]scale=1080:-2[fgs];"
            "[bgf][fgs]overlay=x=0:y='(1920-h)*" + f"{args.y}" + "'"
        )

    cmd = [
        find_ffmpeg(), "-y",
        "-ss", f"{args.start}", "-t", f"{args.dur}", "-i", str(video),
        "-vf", vf, "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(out),
    ]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("ffmpeg falhou")
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
