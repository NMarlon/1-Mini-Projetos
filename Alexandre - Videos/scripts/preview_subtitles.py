"""Preview de legendas SEM cravar no video (so p/ QA visual).

Gera um MP4 temporario em work/ com as legendas queimadas apenas para conferencia.
O output final NUNCA e alterado — conforme decisão do usuário: .srt editável.

Uso: python scripts/preview_subtitles.py <video> <legendas.srt>
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Uso: python scripts/preview_subtitles.py <video> <srt>")
    video = Path(sys.argv[1])
    srt_file = Path(sys.argv[2])
    out = Path("work") / (video.stem + "_preview.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    # escape de caminho p/ filtro do ffmpeg (Windows): usar caminho RELATIVO sem
    # drive letter — "C:" quebra o parser de filtros (ver 05-ERROS-E-APRENDIZADOS)
    srt_rel = srt_file.resolve().relative_to(Path.cwd().resolve()).as_posix()
    vf = (
        f"subtitles=filename={srt_rel}:force_style="
        "'FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=3,Shadow=0,MarginV=60,Alignment=2'"
    )
    cmd = [find_ffmpeg(), "-y", "-i", str(video), "-vf", vf, "-c:a", "copy", str(out)]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("ffmpeg falhou")
    print(f"PREVIEW OK -> {out} (video original intacto)")


if __name__ == "__main__":
    main()
