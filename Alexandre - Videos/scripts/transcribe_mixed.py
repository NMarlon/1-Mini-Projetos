"""Transcreve áudio misto pt-BR/chinês em duas passadas Whisper.

Uso: python scripts/transcribe_mixed.py <audio.wav> [prefixo_saida]

Cria <prefixo>.pt.raw.srt / .zh.raw.srt e transcrições txt.
Não mescla automaticamente: transcrições concorrentes devem ser comparadas e
revisadas antes de produzir a tradução final (evita esconder palavras/idiomas).
"""
import sys
from datetime import timedelta
from pathlib import Path

import srt
from faster_whisper import WhisperModel

MODEL_SIZE = "medium"


def save_pass(model: WhisperModel, audio: Path, prefix: Path, language: str) -> None:
    segments, info = model.transcribe(
        str(audio),
        language=language,
        task="transcribe",
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    subs = []
    lines = [f"Idioma forçado: {language}; detectado: {info.language} "
             f"(probabilidade {info.language_probability:.2f})"]
    for index, seg in enumerate(segments, start=1):
        text = seg.text.strip()
        if not text:
            continue
        subs.append(srt.Subtitle(
            index=index,
            start=timedelta(seconds=max(0.0, seg.start)),
            end=timedelta(seconds=max(0.0, seg.end)),
            content=text,
        ))
        lines.append(f"[{seg.start:7.2f} -> {seg.end:7.2f}] {text}")

    srt_path = prefix.with_name(prefix.name + f".{language}.raw.srt")
    txt_path = prefix.with_name(prefix.name + f".{language}.transcript.txt")
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(srt.compose(subs), encoding="utf-8")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{language}: {len(subs)} segmentos -> {srt_path}, {txt_path}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/transcribe_mixed.py <audio.wav> [prefixo_saida]")
    audio = Path(sys.argv[1])
    prefix = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("work") / audio.stem
    print(f"Carregando modelo '{MODEL_SIZE}'...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    for language in ("zh", "pt"):
        print(f"Transcrevendo passada {language}...")
        save_pass(model, audio, prefix, language)


if __name__ == "__main__":
    main()
