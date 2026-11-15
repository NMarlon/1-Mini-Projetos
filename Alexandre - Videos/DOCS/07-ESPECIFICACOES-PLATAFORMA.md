# 07 — Especificações de plataforma (TikTok / YouTube Shorts)

## Formato técnico

| Item | TikTok | YT Shorts |
|---|---|---|
| Resolução | 1080×1920 (9:16) | 1080×1920 (9:16) |
| Codec | H.264 + AAC | H.264 + AAC |
| Duração ideal | 21–34s (até 60s p/ retenção) | ≤60s |
| Loudness | ~-14 LUFS | ~-14 LUFS |
| Frame rate | 30 ou 60 fps | 30 ou 60 fps |

## Segurança de UI (área não coberta)

- TikTok: manter **~130px livres embaixo** (botões/legenda da UI) e ~120px no topo.
- Shorts: barra de progresso inferior ~120px; título no topo.
- Legendas: centro-vertical levemente acima do meio (~45% da altura).

## Legendas (.srt) — estilo TikTok

- 1–2 linhas máx., ~32 caracteres por linha.
- Palavra-chave em CAIXA ALTA ou marcada no meta (o player/render aplica destaque).
- Timing palavra-a-palavra quando o Whisper fornecer (`word_timestamps=True`).

## Título/legenda

- Gancho no início, pergunta ou revés. Ex.: "ele achava que era 1v1… 😭".
- Hashtags: #warzone #callofduty #cod #gaming #clips #fyp #brasil.
