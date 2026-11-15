"""Compara passes zh x pt por segmento: avg_logprob e no_speech_prob.

O idioma REAL do áudio tende a ter avg_logprob menos negativo (melhor ajuste).
Se as duas passes tiverem logprob parecido, o Whisper está traduzindo
(alucinação) — aí vale o idioma do lang_map.

Uso: python scripts/compare_passes.py <audio.wav> [prefixo]
Saida: work/<prefixo>.compare.txt
"""
import sys
from pathlib import Path

from faster_whisper import WhisperModel

MODEL_SIZE = "medium"


def run(model: WhisperModel, audio: str, language: str) -> list[dict]:
    segs, _ = model.transcribe(
        audio, language=language, task="transcribe",
        word_timestamps=True, vad_filter=True,
        condition_on_previous_text=False,
    )
    out = []
    for s in segs:
        out.append({
            "start": s.start, "end": s.end, "text": s.text.strip(),
            "avg_logprob": getattr(s, "avg_logprob", None),
            "no_speech_prob": getattr(s, "no_speech_prob", None),
        })
    return out


def fmt(seg: dict) -> str:
    lp = seg["avg_logprob"]
    ns = seg["no_speech_prob"]
    return (f"[{seg['start']:6.2f} -> {seg['end']:6.2f}] "
            f"logp={lp if lp is None else round(lp, 3)!s:>6} "
            f"nospeech={ns if ns is None else round(ns, 3)!s:>5} | {seg['text']}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/compare_passes.py <audio.wav> [prefixo]")
    audio = str(Path(sys.argv[1]))
    prefix = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("work") / "compare"

    print("carregando modelo...", flush=True)
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    lines = []
    results = {}
    for lang in ("zh", "pt"):
        print(f"passada {lang}...", flush=True)
        results[lang] = run(model, audio, lang)

    lines.append("=== PASSADA zh (forçado) ===")
    lines += [fmt(s) for s in results["zh"]]
    lines.append("")
    lines.append("=== PASSADA pt (forçado) ===")
    lines += [fmt(s) for s in results["pt"]]

    # sobreposicao: melhor logprob por segundo coberto
    lines.append("")
    lines.append("=== DECISÃO POR TRECHO (melhor avg_logprob) ===")
    best: dict[int, tuple[float, str]] = {}
    for lang, segs in results.items():
        for s in segs:
            if s["avg_logprob"] is None:
                continue
            for sec in range(int(s["start"]), int(s["end"]) + 1):
                cur = best.get(sec)
                if cur is None or s["avg_logprob"] > cur[0]:
                    best[sec] = (s["avg_logprob"], lang)
    # agrupa segundos consecutivos com mesmo vencedor
    secs = sorted(best)
    i = 0
    while i < len(secs):
        j = i
        winner = best[secs[i]][1]
        while j + 1 < len(secs) and secs[j + 1] == secs[j] + 1 and best[secs[j + 1]][1] == winner:
            j += 1
        avg = sum(best[s][0] for s in secs[i:j + 1]) / (j - i + 1)
        lines.append(f"  {secs[i]:3d}-{secs[j] + 1:3d}s -> {winner} (logp medio {avg:.3f})")
        i = j + 1

    out = prefix.with_name(prefix.name + ".compare.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
