# 06 — Ideias futuras, bugs e backlog

> NÃO implementar agora. Serviço de apoio para quem continuar.

## Ideias — canal Warzone

- [ ] Pack de SFX/memes próprio em `assets/` (royalty-free) com preset de uso por tipo de punchline.
- [ ] Template FFmpeg de legenda TikTok reutilizável (`templates/legenda_tiktok.ass`).
- [ ] Script de análise automática de bruto: picos de áudio + scene detection → ranquear momentos.
- [ ] Detectar loops (fim ↔ começo) nos shorts.
- [ ] Estudar melhor horário/formato de postagem e A/B de thumbnails (spec em `07`).
- [ ] Possível dublagem TTS PT-BR (decisão futura do usuário — hoje: manter áudio original).

## Bugs / pendências conhecidas

- [ ] PATH do ffmpeg não atualizado em shells abertos (ver `05`) — considerar wrapper `scripts/ffmpeg.cmd`.
- [ ] Vídeo bruto Warzone está em **360p** — qualidade limitada; pedir original em 720p/1080p se existir.

## Melhorias de fluxo

- [ ] Padronizar `output/<nome>/meta.md` (título, legenda, hashtags, duração, specs).
- [ ] Checklist de QA automatizado (resolução, loudness, duração) via script.
