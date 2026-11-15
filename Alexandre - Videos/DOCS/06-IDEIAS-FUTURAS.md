# 06 — Ideias futuras, bugs e backlog

> NÃO implementar agora. Serviço de apoio para quem continuar.

## Ideias — canal Warzone

- [ ] **Novos brutos do streamer** → material novo p/ shorts (hoje o bruto de 12min só
      rendeu 3 trechos com fala real; ver `04-TAREFAS.md`).
- [ ] Reaproveitar os mesmos trechos com **ângulos/cortes diferentes** (variação de hook
      para testar retenção — A/B de ganchos).

- [ ] Pack de SFX/memes próprio em `assets/` (royalty-free) com preset de uso por tipo de punchline.
- [x] ~~Template FFmpeg de legenda TikTok reutilizável~~ → feito: `templates/estilo.json` + ASS
      gerado por `scripts/render_short.py` (hook no topo, legenda na base, destaque amarelo).
- [x] ~~Script de análise automática de bruto~~ → feito: `scripts/analisar_bruto.py`.
- [ ] Detectar loops (fim ↔ começo) nos shorts (hoje: loop = repetir os 0,4s do início no fim).
- [ ] Estudar melhor horário/formato de postagem e A/B de thumbnails (spec em `07`).
- [ ] Possível dublagem TTS PT-BR (decisão futura do usuário — hoje: manter áudio original).
- [ ] Meme de imagem/cutaway por cima do gameplay (hoje: só SFX + textos) — exigiria assets
      de meme com licença limpa e posicionamento manual por receita.
- [ ] Legenda palavra-a-palavra (hoje: 4–7 palavras por tela com tempo proporcional).
- [ ] Thumbnail/frame de capa gerado automaticamente para TikTok/Shorts.

## Bugs / pendências conhecidas

- [ ] PATH do ffmpeg não atualizado em shells abertos (ver `05`) — considerar wrapper `scripts/ffmpeg.cmd`.
- [ ] Vídeo bruto Warzone está em **360p** — qualidade limitada; pedir original em 720p/1080p se existir.

## Melhorias de fluxo

- [x] ~~Padronizar `output/<nome>/meta.md`~~ → feito: gerado por `scripts/render_short.py`.
- [x] ~~Checklist de QA automatizado~~ → parcial: checklist escrito no `meta.md` + verificação
      manual de frames/áudio; automatizar checagem de specs num script ainda falta.
