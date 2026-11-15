"""Entrega final: copia o vídeo original + .srt + meta.md para output/<nome>/.

O vídeo NUNCA é re-encodeado — conforme decisão do usuário, as legendas ficam
em arquivo .srt editável, separado do vídeo.

Uso: python scripts/deliver.py <video_original> <srt_final> <nome_entrega> [titulo]
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit("Uso: python scripts/deliver.py <video> <srt> <nome_entrega> [titulo]")
    video = Path(sys.argv[1])
    srt_file = Path(sys.argv[2])
    name = sys.argv[3]
    title = sys.argv[4] if len(sys.argv) > 4 else name

    out_dir = Path("output") / name
    out_dir.mkdir(parents=True, exist_ok=True)

    dst_video = out_dir / video.name
    shutil.copy2(video, dst_video)
    dst_srt = out_dir / (name + ".pt-BR.srt")
    shutil.copy2(srt_file, dst_srt)

    meta = out_dir / "meta.md"
    meta.write_text(
        f"""# Entrega: {title}

- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Vídeo: `{dst_video.name}` (ORIGINAL, sem legendas cravadas — áudio original mantido)
- Legenda: `{dst_srt.name}` (editável — arraste no player / suba no TikTok como caption)
- Idioma do áudio: misto pt-BR + chinês
- Tradução: PT-BR

## Como usar a legenda

- **VLC:** Ferramentas → Legendas → Fich. de legendas (ou arraste o .srt no vídeo)
- **CapCut/TikTok:** importar o vídeo e adicionar o .srt como texto automático
- Editar: qualquer editor de texto (UTF-8, formato SRT padrão)

## Título sugerido

{title}
""",
        encoding="utf-8",
    )
    print(f"ENTREGA OK -> {out_dir}")
    for p in sorted(out_dir.iterdir()):
        print(f"  - {p.name} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
