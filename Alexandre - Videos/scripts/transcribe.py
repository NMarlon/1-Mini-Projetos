"""Transcreve áudio com faster-whisper (offline).

Uso: python scripts/transcribe.py <audio.wav> [prefixo_saida]
Saida: work/<prefixo>.raw.srt + work/<prefixo>.transcript.txt + imprime idioma detectado.
"""
import sys
from pathlib import Path

import srt
from faster_whisper import WhisperModel

# modelo small = bom equilibrio CPU/qualidade p/ chines + pt
MODEL_SIZE = "small"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/transcribe.py <audio.wav> [prefixo]")
    audio = Path(sys.argv[1])
    prefix = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("work") / audio.stem.replace("_audio", "")

    print(f"carregando modelo '{MODEL_SIZE}' (primeira execucao baixa ~460MB)...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        str(audio), word_timestamps=True, vad_filter=True,
    )
    print(f"IDIOMA DETECTADO: {info.language} (prob {info.language_probability:.2f})")

    subs, lines = [], []
    for i, seg in enumerate(segments, start=1):
        subs.append(srt.Subtitle(index=i, start=seg.start, end=seg.end,
                                 content=seg.text.strip()))
        lines.append(f"[{seg.start:7.2f} -> {seg.end:7.2f}] {seg.text.strip()}")

    prefix.parent.mkdir(parents=True, exist_ok=True)
    srt_path = prefix.with_suffix(".raw.srt")
    txt_path = prefix.with_suffix(".transcript.txt")
    srt_path.write_text(srt.compose(subs), encoding="utf-8")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> {srt_path} e {txt_path} ({len(subs)} segmentos)")


if __name__ == "__main__":
    main()
