"""Renderiza um short viral a partir de uma receita JSON (roteiro).

Uso:
    python scripts/render_short.py roteiros/<slug>.json [--dry-run] [--so-video]

Passos internos (2 encodes, sem perda acumulada):
  PASSO 1  recorta os segmentos, monta 9:16 (blurpad/crop), zoom pulse, loop
           -> work/<slug>_p1.mp4
  PASSO 2  queima legendas + hook (ASS gerado em runtime), mistura bgm/sfx,
           normaliza loudness -> output/<slug>/video.mp4 + meta.md

Receita (JSON) — ver roteiros/_exemplo.json:
    slug, fonte, modo(blurpad|crop), y_mira, fps, dur_max,
    segmentos[{start,end}], zooms[{start,fim,valor}],
    hook[{texto,inicio,fim}], legenda(srt opcional), destaque[palavras],
    bgm{arquivo,volume}, sfx[{t,arquivo,volume}], loop,
    meta{titulo,legenda_post,hashtags[]}
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import srt as srtlib

sys.path.insert(0, str(Path(__file__).parent))
from find_ffmpeg import find_ffmpeg

ROOT = Path(__file__).resolve().parent.parent  # raiz do projeto (cwd deve ser ela)
ESTILO = ROOT / "templates" / "estilo.json"

DEFAULT_ESTILO = {
    "fonte": "Arial",
    "legenda_tam": 74,
    "legenda_margem_v": 300,
    "hook_tam": 86,
    "hook_margem_v": 420,
    "contorno": 6,
    "max_palavras": 6,
    "max_chars": 32,
}


# ---------------------------------------------------------------- utilidades
def run(cmd: list[str], dry: bool = False) -> None:
    print("$", " ".join(str(c) for c in cmd))
    if dry:
        return
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       errors="replace")
    if r.returncode != 0:
        print(r.stderr[-4000:])
        sys.exit("ffmpeg falhou (ver acima)")


def ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def chunkize(texto: str, max_palavras: int, max_chars: int) -> list[str]:
    """Quebra em telas de 4–7 palavras (regra do 02-PESQUISA-VIRAL).

    Distribui as palavras EM BALANÇO (n chunks de tamanho parecido) para não
    sobrar um "cara." sozinho no fim — erro de QA do piloto 01.
    """
    palavras = texto.split()
    if len(palavras) <= max_palavras:
        return [texto]
    import math
    n_chunks = math.ceil(len(palavras) / max_palavras)
    base = math.ceil(len(palavras) / n_chunks)
    chunks, atual = [], ""
    for i, p in enumerate(palavras):
        restam = len(palavras) - i
        falta = n_chunks - len(chunks) - 1
        cand = (atual + " " + p).strip()
        # fecha o chunk quando atingir o alvo e ainda houver pedaço p/ os próximos
        if atual and (len(cand.split()) >= base or len(cand) > max_chars) and falta > 0:
            chunks.append(atual)
            atual = p
        else:
            atual = cand
    if atual:
        chunks.append(atual)
    # evita chunk minúsculo no fim: distribui de volta
    if len(chunks) >= 2 and len(chunks[-1].split()) < 3:
        ultimo = chunks.pop()
        chunks[-1] = (chunks[-1] + " " + ultimo).strip()
    return chunks or [texto]


def destaque(texto: str, palavras: list[str]) -> str:
    """Pinta palavra-chave de amarelo (ASS &H0000FFFF&) — estilo TikTok."""
    out = texto
    for p in palavras or []:
        out = re.sub(re.escape(p), r"{\\c&H0000FFFF&}" + p + r"{\\c&H00FFFFFF&}",
                     out, flags=re.IGNORECASE)
    return out


def monta_ass(recipe: dict, estilo: dict, dur: float) -> str:
    """Gera o .ass com HOOK (topo) + legendas (base, acima da UI)."""
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        (f"Style: Leg,{estilo['fonte']},{estilo['legenda_tam']},&H00FFFFFF,"
         f"&H0000FFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,"
         f"{estilo['contorno']},0,2,60,60,{estilo['legenda_margem_v']},1"),
        (f"Style: Hook,{estilo['fonte']},{estilo['hook_tam']},&H00FFFFFF,"
         f"&H0000FFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,"
         f"{estilo['contorno'] + 1},0,8,60,60,{estilo['hook_margem_v']},1"),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text", "",
    ]

    # hook (topo) — 0–3s
    for h in recipe.get("hook", []):
        txt = h["texto"].replace("\n", "\\N")
        linhas.append(
            f"Dialogue: 0,{ass_time(h['inicio'])},{ass_time(h['fim'])},Hook,,"
            f"0,0,0,,{txt}"
        )

    # legendas (base) — 4–7 palavras por tela
    srt_path = recipe.get("legenda")
    if srt_path and Path(srt_path).exists():
        subs = list(srtlib.parse(Path(srt_path).read_text(encoding="utf-8")))
        for sub in subs:
            inicio = sub.start.total_seconds()
            fim = min(sub.end.total_seconds(), dur)
            if fim <= inicio:
                continue
            chunks = chunkize(sub.content.replace("\n", " "),
                              estilo["max_palavras"], estilo["max_chars"])
            total_chars = sum(len(c) for c in chunks) or 1
            t = inicio
            for c in chunks:
                d = (fim - inicio) * len(c) / total_chars
                linhas.append(
                    f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Leg,,"
                    f"0,0,0,,{destaque(c, recipe.get('destaque', []))}"
                )
                t += d
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- passo 1
def passo1(recipe: dict, out: Path, dry: bool) -> float:
    """Segmentos + verticalização + zoom pulse + loop -> work/<slug>_p1.mp4"""
    fonte = recipe["fonte"]
    segs = recipe["segmentos"]
    dur = sum(s["end"] - s["start"] for s in segs)
    if recipe.get("loop"):
        dur += 0.4  # repete o primeiro 0.4s no fim (emenda no início)
    if dur > recipe.get("dur_max", 60):
        sys.exit(f"duração {dur:.1f}s maior que o máximo {recipe.get('dur_max', 60)}s")

    fps = recipe.get("fps", 30)
    y_mira = recipe.get("y_mira", 0.45)
    modo = recipe.get("modo", "blurpad")

    fc: list[str] = []
    vlabels, alabels = [], []
    for i, s in enumerate(segs):
        fc.append(f"[0:v]trim=start={s['start']}:end={s['end']},"
                  f"setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[0:a]atrim=start={s['start']}:end={s['end']},"
                  f"asetpts=PTS-STARTPTS[a{i}]")
        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")

    n = len(segs)
    fc.append("".join(vlabels) + f"concat=n={n}:v=1:a=0[vcat]")
    fc.append("".join(alabels) + f"concat=n={n}:v=0:a=1[acat]")

    # verticalização
    if modo == "crop":
        fc.append(
            "[vcat]crop=w='min(iw\\,ih*9/16)':h='min(ih\\,iw*16/9)'"
            f":x='(iw-ow)*{recipe.get('x_mira', 0.5)}':y='(ih-oh)*{y_mira}',"
            "scale=1080:1920:flags=lanczos,setsar=1[base]"
        )
    else:  # blurpad
        fc.append(
            "[vcat]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=30,"
            "eq=brightness=-0.20:saturation=0.85[bgf];"
            f"[fg]scale=1080:-2[fgs];"
            f"[bgf][fgs]overlay=x=0:y='(1920-h)*{y_mira}'[base]"
        )

    # loop: reaproveita os primeiros 0.4s do próprio short no final
    if recipe.get("loop"):
        fc.append("[base]split=2[bmain][bhead]")
        fc.append("[bhead]trim=0:0.4,setpts=PTS-STARTPTS[headv]")
        fc.append("[acat]asplit=2[amain][ahead]")
        fc.append("[ahead]atrim=0:0.4,asetpts=PTS-STARTPTS[heada]")
        fc.append("[bmain][headv]concat=n=2:v=1:a=0[vloop]")
        fc.append("[amain][heada]concat=n=2:v=0:a=1[aloop]")
        v_final, a_final = "[vloop]", "[aloop]"
    else:
        v_final, a_final = "[base]", "[acat]"

    # zoom pulse (zoompan anima por frame; usamos o índice de saída on/fps,
    # pois zoompan NÃO expõe a variável t — ver 05-ERROS-E-APRENDIZADOS)
    zooms = recipe.get("zooms", [])
    T = f"(on/{fps})"
    expr = "0"
    for z in zooms:
        a, b, val = z["start"], z["fim"], z.get("valor", 0.14)
        r = 0.35  # rampa de entrada/saída (s)
        pulso = (f"if(lt({T},{a}),0,"
                 f"if(lt({T},{a + r}),({T}-{a})/{r},"
                 f"if(lt({T},{b}),1,"
                 f"if(lt({T},{b + r}),1-({T}-{b})/{r},0))))")
        expr = f"{expr}+{val}*({pulso})"
    expr = f"1+({expr})"

    fc.append(
        f"{v_final}fps={fps},zoompan=z='{expr}'"
        ":x='iw/2-(iw/zoom/2)'"
        f":y='(ih-(ih/zoom))*{y_mira}'"
        f":d=1:s=1080x1920:fps={fps},format=yuv420p,setsar=1[vout]"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [find_ffmpeg(), "-y", "-i", fonte,
           "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", a_final,
           "-c:v", "libx264", "-crf", "16", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-t", f"{dur:.3f}", str(out)]
    run(cmd, dry)
    return dur


# ---------------------------------------------------------------- passo 2
def passo2(recipe: dict, p1: Path, dur: float, out_dir: Path, dry: bool,
           estilo: dict) -> Path:
    slug = recipe["slug"]
    ass_path = Path("work") / f"{slug}.ass"
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(monta_ass(recipe, estilo, dur), encoding="utf-8")

    out = out_dir / "video.mp4"
    out_dir.mkdir(parents=True, exist_ok=True)

    fc = [f"[0:v]ass={ass_path.as_posix()}[v]"]
    mixes = ["[0:a]"]
    idx = 1

    bgm = recipe.get("bgm")
    if bgm and Path(bgm["arquivo"]).exists():
        fc.append(f"[{idx}:a]volume={bgm.get('volume', 0.10)},"
                  f"atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[abgm]")
        mixes.append("[abgm]")
        idx += 1

    for i, s in enumerate(recipe.get("sfx", [])):
        if not Path(s["arquivo"]).exists():
            print(f"AVISO: sfx ausente, pulando: {s['arquivo']}")
            continue
        ms = int(s["t"] * 1000)
        fc.append(f"[{idx}:a]volume={s.get('volume', 1.0)},"
                  f"adelay={ms}:all=1,apad=whole_dur={dur:.3f},"
                  f"atrim=0:{dur:.3f}[asfx{i}]")
        mixes.append(f"[asfx{i}]")
        idx += 1

    n = len(mixes)
    fc.append("".join(mixes) +
              f"amix=inputs={n}:normalize=0:dropout_transition=0,"
              f"atrim=0:{dur:.3f},"
              f"afade=t=out:st={max(0, dur - 0.3):.3f}:d=0.3,"
              "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

    cmd = [find_ffmpeg(), "-y", "-i", str(p1)]
    if bgm and Path(bgm["arquivo"]).exists():
        cmd += ["-stream_loop", "-1", "-t", f"{dur:.3f}", "-i", bgm["arquivo"]]
    for s in recipe.get("sfx", []):
        if Path(s["arquivo"]).exists():
            cmd += ["-ss", f"{s['t']}", "-i", s["arquivo"]]
    cmd += ["-filter_complex", ";".join(fc),
            "-map", "[v]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-t", f"{dur:.3f}", str(out)]
    run(cmd, dry)
    return out


# ---------------------------------------------------------------- meta
def escreve_meta(recipe: dict, dur: float, out_dir: Path) -> None:
    m = recipe.get("meta", {})
    segs = ", ".join(f"{s['start']:.1f}–{s['end']:.1f}s"
                     for s in recipe["segmentos"])
    tags = " ".join(m.get("hashtags", []))
    txt = [
        f"# {m.get('titulo', recipe['slug'])}", "",
        f"**Legenda do post:** {m.get('legenda_post', '')}", "",
        f"**Hashtags:** {tags}", "",
        "## Specs", "",
        f"- duração: {dur:.1f}s | 1080×1920 (9:16) | 30 fps | H.264 + AAC",
        f"- modo: {recipe.get('modo', 'blurpad')} | fonte: `{Path(recipe['fonte']).name}`",
        f"- segmentos da fonte (s): {segs}",
        f"- receita: `roteiros/{recipe['slug']}.json`", "",
        "## Checklist de QA", "",
        "- [ ] hook visível nos 1ºs 3s (texto no topo)",
        "- [ ] legendas legáveis e acima da UI (bottom 15% livre)",
        "- [ ] ação dentro do quadro em todo momento (sem mira cortada)",
        "- [ ] áudio sem clipping, voz inteligível",
        "- [ ] último quadro emenda no primeiro (loop)",
        "- [ ] duração ≤ 60s",
    ]
    (out_dir / "meta.md").write_text("\n".join(txt), encoding="utf-8")
    print(f"OK -> {out_dir / 'meta.md'}")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("receita", help="JSON do roteiro (roteiros/<slug>.json)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--so-video", action="store_true",
                    help="para só no passo 1 (QA de enquadramento)")
    args = ap.parse_args()

    recipe = json.loads(Path(args.receita).read_text(encoding="utf-8"))
    estilo = dict(DEFAULT_ESTILO)
    if ESTILO.exists():
        estilo.update(json.loads(ESTILO.read_text(encoding="utf-8")))

    slug = recipe["slug"]
    p1 = Path("work") / f"{slug}_p1.mp4"
    print(f"== PASSO 1: {slug} ==")
    dur = passo1(recipe, p1, args.dry_run)
    print(f"duração total: {dur:.1f}s")
    if args.so_video:
        return

    out_dir = Path("output") / slug
    print(f"== PASSO 2: {slug} ==")
    out = passo2(recipe, p1, dur, out_dir, args.dry_run, estilo)
    if not args.dry_run:
        escreve_meta(recipe, dur, out_dir)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
