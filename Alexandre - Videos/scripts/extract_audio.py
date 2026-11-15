"""Extrai o áudio do vídeo em WAV 16kHz mono (entrada ideal p/ Whisper).

Uso: python scripts/extract_audio.py <video> [saida.wav]
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/extract_audio.py <video> [saida.wav]")
    video = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("work") / (video.stem + "_audio.wav")
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        find_ffmpeg(), "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(out),
    ]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("ffmpeg falhou")
    print(f"OK -> {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
