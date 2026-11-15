"""Monta o .srt do short remapeando os tempos do bruto para a linha do tempo do corte.

O bruto é transcrito em tempo absoluto (ou relativo a um --start); o short é uma
CONCATENAÇÃO de segmentos. Este script desloca cada legenda para o tempo correto
dentro do short e descarta as que caem fora dos segmentos.

Uso:
    python scripts/montar_srt.py <srt_entrada> --seg 702:714.5,718:724,725:730 \
                                 --out roteiros/01.srt

`--seg` usa os MESMOS inícios/fins do campo "segmentos" do JSON da receita.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import srt


def parse_segs(txt: str) -> list[tuple[float, float]]:
    segs = []
    for parte in txt.split(","):
        a, b = parte.split(":")
        segs.append((float(a), float(b)))
    return segs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("--seg", required=True, help="inicio:fim,inicio:fim,...")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    segs = parse_segs(args.seg)
    subs = list(srt.parse(Path(args.entrada).read_text(encoding="utf-8")))

    novos, cursor = [], 0.0  # cursor = tempo do início do segmento no short
    for ini, fim in segs:
        dur = fim - ini
        for s in subs:
            si, sf = s.start.total_seconds(), s.end.total_seconds()
            if sf <= ini or si >= fim:          # fora deste segmento
                continue
            a = max(si, ini) - ini + cursor
            b = min(sf, fim) - ini + cursor
            if b - a < 0.15:
                continue
            novos.append(srt.Subtitle(index=len(novos) + 1,
                                      start=timedelta(seconds=a),
                                      end=timedelta(seconds=b),
                                      content=s.content))
        cursor += dur

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt.compose(novos), encoding="utf-8")
    print(f"OK -> {out} ({len(novos)} legendas, "
          f"última em {novos[-1].end if novos else '—'})")


if __name__ == "__main__":
    main()
