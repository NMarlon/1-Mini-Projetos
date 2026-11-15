"""Transcreve um TRECHO do vídeo → .srt com tempos relativos ao início do trecho.

Feito para legendar shorts: extrai o áudio do intervalo, roda faster-whisper
(word_timestamps) e grava o .srt já deslocado para 0 (pronto p/ queimar no render).

Uso:
    python scripts/legendar.py <video> --start 12.3 --dur 28 [--out work/x.srt]
                               [--lang pt] [--modelo medium]

Observações:
- modelo medium é o mínimo confiável (small alucina — ver 05-ERROS-E-APRENDIZADOS).
- se o áudio for misto pt + outro idioma, rode 2× (--lang pt / --lang xx) e mescure
  por timestamps (ex.: scripts/transcribe_mixed.py).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import srt
from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg


def td(seconds: float) -> timedelta:
    """faster-whisper devolve float; srt exige timedelta (ver 05-ERROS)."""
    return timedelta(seconds=max(0.0, float(seconds)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--lang", default=None, help="força idioma (pt, zh, en...)")
    ap.add_argument("--modelo", default="medium")
    ap.add_argument("--sem-vad", action="store_true",
                    help="desliga o VAD (pega fala sobre música/ruído; "
                         "risco maior de alucinação — validar no vídeo)")
    args = ap.parse_args()

    video = Path(args.video)
    out = Path(args.out) if args.out else Path("work") / (
        f"{video.stem[:40]}_{int(args.start)}s.srt")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    cmd = [
        find_ffmpeg(), "-y", "-ss", f"{args.start}", "-t", f"{args.dur}",
        "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2000:])
        sys.exit("extracao de audio falhou")

    print(f"carregando modelo '{args.modelo}'...")
    model = WhisperModel(args.modelo, device="cpu", compute_type="int8")
    kw = dict(word_timestamps=True, vad_filter=not args.sem_vad)
    if args.lang:
        kw["language"] = args.lang
    segments, info = model.transcribe(str(wav), **kw)
    print(f"idioma: {info.language} (prob {info.language_probability:.2f})")

    subs = []
    for seg in segments:
        txt = seg.text.strip()
        if not txt:
            continue
        subs.append(srt.Subtitle(index=len(subs) + 1, start=td(seg.start),
                                 end=td(seg.end), content=txt))
    wav.unlink(missing_ok=True)
    if not subs:
        sys.exit("nenhum segmento transcrito")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt.compose(subs), encoding="utf-8")
    print(f"OK -> {out} ({len(subs)} legendas, "
          f"última em {subs[-1].end})")


if __name__ == "__main__":
    main()
