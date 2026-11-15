"""Mapeia o idioma falado por janela de tempo (pt x zh) no áudio misto.

Uso: python scripts/lang_map.py <audio.wav> [janela_s] [salto_s]

Saída: work/<prefixo>.langmap.txt com trecho -> idioma detectado.
Serve p/ decidir qual passada (zh ou pt) usar em cada trecho do .srt final.
"""
import sys
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

MODEL_SIZE = "medium"


def load_wav16k(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1, "esperado 16k mono"
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/lang_map.py <audio.wav> [janela_s] [salto_s]")
    audio_path = Path(sys.argv[1])
    win = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    hop = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    audio = load_wav16k(str(audio_path))
    sr = 16000
    total_s = len(audio) / sr
    print(f"audio: {total_s:.1f}s | janela={win}s salto={hop}s", flush=True)

    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("modelo carregado; detectando...", flush=True)

    lines = []
    t = 0.0
    while t < total_s:
        seg = audio[int(t * sr):int((t + win) * sr)]
        if len(seg) < sr:  # janela final curta demais
            break
        try:
            _segs, info = model.transcribe(
                seg, language=None, task="transcribe",
                vad_filter=True, beam_size=5,
                condition_on_previous_text=False,
            )
            lang, prob = info.language, info.language_probability
        except Exception as exc:  # noqa: BLE001
            lang, prob = f"erro:{type(exc).__name__}", 0.0
        line = f"[{t:6.1f} -> {min(t + win, total_s):6.1f}] {lang} (p={prob:.2f})"
        print(line, flush=True)
        lines.append(line)
        t += hop

    out = audio_path.with_name(audio_path.stem.replace("_audio", "") + ".langmap.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
