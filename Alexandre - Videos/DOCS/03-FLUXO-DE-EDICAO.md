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

```
1. Inspecionar bruto: ffprobe + extrair áudio + scene detection
2. Analisar picos de áudio (gritos/risos) e cortes de cena → work/analise.md ranqueado
3. Selecionar segmento com arco (hook → tensão → punchline), 21–34s
4. Render (FFmpeg): corte fino, 9:16 com fundo desfocado, zoom pulse 3–5s,
   legendas estilo TikTok, SFX/meme no punchline, trilha com ducking
5. QA: extrair frames-chave, conferir specs (resolução, loudness, duração)
6. output/<nome>/video.mp4 + meta.md (título, legenda, hashtags)
7. commit
```

## Especificações de saída (shorts)

- 1080×1920 (9:16), H.264, AAC 128k+, loudness ~-14 LUFS, 21–34s.
- Detalhes: `07-ESPECIFICACOES-PLATAFORMA.md`.
