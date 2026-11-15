"""Analisa o bruto e ranqueia momentos virais.

Combina (a) envelope de energia do áudio (gritos/risos/tiro = picos) e
(b) detecção de mudança de cena (cortes de ação) para sugerir segmentos.

Uso:
    python scripts/analisar_bruto.py <video> [--janela 10] [--passo 5] [--top 15]

Saida: work/<stem>_analise.md (e .json com os numeros crus)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg


def ffprobe_duration(video: Path) -> float:
    import shutil
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        cand = find_ffmpeg().replace("ffmpeg.exe", "ffprobe.exe")
        ffprobe = cand if Path(cand).exists() else None
    if not ffprobe:
        return _duration_manual(video)
    r = subprocess.run(
        [ffprobe, "-v", "error",
         "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def _duration_manual(video: Path) -> float:
    """Fallback: parser do atomo mvhd (ver scripts/mp4_info.py e 05-ERROS)."""
    import struct
    data = video.read_bytes()
    i = data.find(b"mvhd")
    if i < 0:
        raise RuntimeError("sem ffprobe e sem atomo mvhd")
    if data[i + 4] == 1:
        ts = struct.unpack(">I", data[i + 24:i + 28])[0]
        d = struct.unpack(">Q", data[i + 28:i + 36])[0]
    else:
        ts = struct.unpack(">I", data[i + 16:i + 20])[0]
        d = struct.unpack(">I", data[i + 20:i + 24])[0]
    return d / ts


def rms_envelope(video: Path, hop: float = 0.25) -> tuple[np.ndarray, float]:
    """Extrai audio mono 16k e devolve RMS por janela de `hop` segundos."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    subprocess.run(
        [find_ffmpeg(), "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(wav)],
        capture_output=True, text=True, check=True,
    )
    import wave

    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    wav.unlink(missing_ok=True)

    n = max(1, int(sr * hop))
    nwin = len(data) // n
    data = data[: nwin * n].reshape(nwin, n)
    rms = np.sqrt((data ** 2).mean(axis=1))
    rms = rms / (rms.max() + 1e-9)
    return rms, hop


def scene_cuts(video: Path, threshold: float = 0.35) -> list[float]:
    cmd = [
        find_ffmpeg(), "-i", str(video), "-vf",
        f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def fmt(t: float) -> str:
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--janela", type=float, default=10.0)
    ap.add_argument("--passo", type=float, default=5.0)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    video = Path(args.video)
    out_md = Path("work") / (video.stem + "_analise.md")
    out_json = Path("work") / (video.stem + "_analise.json")
    out_md.parent.mkdir(parents=True, exist_ok=True)

    dur = ffprobe_duration(video)
    print(f"duration: {dur:.1f}s ({fmt(dur)})")
    rms, hop = rms_envelope(video)
    print(f"envelope: {len(rms)} janelas de {hop}s")
    cuts = scene_cuts(video)
    print(f"cenas detectadas: {len(cuts)}")

    # janela fixa de silencio (corte natural)
    sil_thr = max(0.01, float(np.percentile(rms, 15)))
    silences = []
    in_sil = None
    for i, v in enumerate(rms):
        t = i * hop
        if v < sil_thr:
            if in_sil is None:
                in_sil = t
        else:
            if in_sil is not None and t - in_sil >= 2.0:
                silences.append((in_sil, t))
            in_sil = None
    if in_sil is not None and dur - in_sil >= 2.0:
        silences.append((in_sil, dur))

    # score por janela
    results = []
    t = 0.0
    while t + args.janela <= dur + 1e-6:
        a, b = t, t + args.janela
        i0, i1 = int(a / hop), max(int(a / hop) + 1, int(b / hop))
        seg = rms[i0:i1]
        energia = float(seg.mean())
        pico = float(seg.max())
        pico_t = a + int(np.argmax(seg)) * hop
        n_cuts = sum(1 for c in cuts if a <= c <= b)
        # energetic + ação (cortes) + sem silencio
        score = energia * 2.0 + pico * 1.5 + min(n_cuts, 4) * 0.12
        results.append(dict(start=round(a, 2), end=round(b, 2), score=round(score, 3),
                            energia=round(energia, 3), pico=round(pico, 3),
                            pico_t=round(pico_t, 2), cortes=n_cuts))
        t += args.passo

    results.sort(key=lambda r: r["score"], reverse=True)
    top = results[: args.top]

    # dedup: descarta janelas sobrepostas em >50%
    sel = []
    for r in top:
        if any(min(r["end"], s["end"]) - max(r["start"], s["start"])
               > 0.5 * args.janela for s in sel):
            continue
        sel.append(r)

    lines = [
        f"# Análise — {video.name}",
        "",
        f"- duração: **{fmt(dur)}** ({dur:.1f}s)",
        f"- cortes de cena (thr 0.35): {len(cuts)}",
        f"- janelas de silêncio ≥2s (cortes naturais): {len(silences)}",
        f"- melhor energia da faixa: {max(r['energia'] for r in results):.2f}",
        "",
        "## Momentos ranqueados (janelas de "
        f"{args.janela:.0f}s, passo {args.passo:.0f}s)",
        "",
        "| # | Início → Fim | Score | Energia | Pico em | Cortes na janela | Sugestão (arco 15–30s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(sel, 1):
        sug_a = max(0.0, r["start"] - 3)
        sug_b = min(dur, r["start"] + 30)
        lines.append(
            f"| {i} | {fmt(r['start'])} → {fmt(r['end'])} | {r['score']:.2f} | "
            f"{r['energia']:.2f} | {fmt(r['pico_t'])} | {r['cortes']} | "
            f"{fmt(sug_a)} → {fmt(sug_b)} ({sug_b - sug_a:.0f}s) |"
        )

    lines += ["", "## Cortes de cena (todos)", ""]
    lines += [f"- {fmt(c)}" for c in cuts[:80]]
    if len(cuts) > 80:
        lines.append(f"- … +{len(cuts) - 80}")

    lines += ["", "## Silêncios ≥2s (bons pontos de corte)", ""]
    lines += [f"- {fmt(a)} → {fmt(b)}" for a, b in silences]

    out_md.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(json.dumps(dict(dur=dur, cuts=cuts, silences=silences,
                                        top=sel), indent=1), encoding="utf-8")
    print(f"OK -> {out_md} e {out_json} ({len(sel)} momentos no top)")


if __name__ == "__main__":
    main()
