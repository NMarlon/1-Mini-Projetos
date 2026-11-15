# 03 — Fluxo de edição (pipeline técnico)

> Reproduzível do zero. Tudo roda local/offline.

## Setup

1. FFmpeg: instalado via `winget install Gyan.FFmpeg` (binário em
   `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\bin\` — PATH só atualiza em novo shell;
   nas scripts, resolver o caminho completo ou pedir novo shell).
2. Python 3.11 + `pip install -r requirements.txt` (faster-whisper, srt).

## A) Pipeline de TRADUÇÃO (vídeo estrangeiro → PT-BR com legenda editável)

```
1. scripts/extract_audio.py    → work/<nome>_audio.wav (16kHz mono)
2. scripts/transcribe.py       → work/<nome>.raw.srt   (idioma detectado + timestamps)
                                 + work/<nome>.transcript.txt
3. Tradução PT-BR (pelo agente) → work/<nome>.pt-BR.srt (editável, estilo TikTok)
4. QA visual: players/ffmpeg -vf subtitles p/ conferir timing (preview só, não cravar)
5. output/<nome>/ → vídeo ORIGINAL intacto + <nome>.pt-BR.srt + meta.md
6. commit
```

**Decisão do usuário (2026-05):** legendas **NÃO são cravadas** no vídeo — entrega-se o
`.srt` editável. Áudio original mantido (sem dublagem).

## B) Pipeline de EDIÇÃO viral (clips Warzone → short)

Reproduzível de ponta a ponta (tudo local, offline). Exemplo real: `roteiros/01-aura-3x1.json`.

```
1. Análise do bruto
   python scripts/analisar_bruto.py <bruto.mp4>
   → work/<bruto>_analise.md (janelas ranqueadas por energia + cortes de cena + silêncios)

2. Transcrição das zonas quentes (Whisper medium)
   python scripts/legendar.py <bruto.mp4> --start <t> --dur <s> --lang pt --out work/<zona>.srt
   → ATENÇÃO: tempos do .srt são RELATIVOS ao --start. Validar com frames:
   ffmpeg -ss <t> -i <bruto> -frames:v 1 work\chk.jpg   (alucinação = frase repetida — ver 05)

3. Roteiro: criar roteiros/<slug>.json (copiar o 01) com segmentos, zooms, hook, sfx, bgm, meta
   + gerar a legenda do timeline:
   python scripts/montar_srt.py work/<zona>.srt --seg <rel1>:<rel2>,... --out roteiros/<slug>.srt

4. Render (2 passos):
   python scripts/render_short.py roteiros/<slug>.json --so-video   # só geometria (QA rápido)
   python scripts/render_short.py roteiros/<slug>.json              # completo

5. QA: extrair frames em 3–5 pontos, conferir hook/legenda/enquadramento; conferir áudio:
   ffmpeg -i output/<slug>/video.mp4 -af volumedetect -f null -   (max_volume < -1 dB)

6. output/<slug>/video.mp4 + meta.md (título, legenda, hashtags, specs, checklist) → commit
```

Modos de verticalização: `blurpad` (faixa central + fundo desfocado — **padrão p/ fonte 360p**)
e `crop` (recorte cheio, só p/ fonte 720p+). Estilo de legenda/hook: `templates/estilo.json`.
Assets: só CC0/CC BY, baixados por `scripts/baixar_assets.py`, créditos em `assets/CREDITOS.md`.

## Especificações de saída (shorts)

- 1080×1920 (9:16), H.264, AAC 128k+, loudness ~-14 LUFS, 21–34s.
- Detalhes: `07-ESPECIFICACOES-PLATAFORMA.md`.
