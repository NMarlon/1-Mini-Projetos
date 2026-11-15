"""Sonda janelas de áudio em modo AUTO (idioma escolhido pelo Whisper).

Diferente de forçar 'pt' ou 'zh', aqui o modelo detecta e transcreve nativamente
— se a fala for pt, sai texto pt; se zh, sai zh. Serve p/ decidir a mistura real.

Uso: python scripts/lang_probe.py <audio.wav> [ini:fim,ini:fim,...]
"""
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

DEFAULT_WINDOWS = "0:4,3.5:6.5,9:14,13:18,17:21,20:26,30:35,41:45"
MODEL_SIZE = "medium"
SR = 16000


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"Uso: python scripts/lang_probe.py <audio.wav> [janelas] "
                 f"(padrao: {DEFAULT_WINDOWS})")
    import wave
    audio_path = Path(sys.argv[1])
    windows = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WINDOWS

    with wave.open(str(audio_path), "rb") as w:
        raw = w.readframes(w.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    lines = []
    for part in windows.split(","):
        a, b = part.split(":")
        a, b = float(a), float(b)
        seg = audio[int(a * SR):int(b * SR)]
        segs, info = model.transcribe(
            seg, language=None, task="transcribe",
            vad_filter=True, beam_size=5,
            condition_on_previous_text=False,
        )
        texts = [f"    {s.start + a:5.2f}->{s.end + a:5.2f} | {s.text.strip()}"
                 for s in segs]
        head = (f"[{a:5.1f}-{b:5.1f}s] idioma={info.language} "
                f"(p={info.language_probability:.2f})")
        block = head + ("\n" + "\n".join(texts) if texts else "\n    (sem fala)")
        print(block, flush=True)
        lines.append(block)

    out = audio_path.with_name(audio_path.stem.replace("_audio", "") + ".probe.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
