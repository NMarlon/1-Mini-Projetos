# 04 — TAREFAS (status do trabalho)

> **Formato:** cada tarefa tem status, passo atual (onde parou) e como proceder.
> Ao continuar: atualize este arquivo ANTES de encerrar a sessão.

---

## TAREFA EM ANDAMENTO: shorts virais do bruto Warzone

**Status:** 🟡 PILOTO CONCLUÍDO — falta o lote (+3 shorts)
**Bruto:** `YTDown..._MORRE-DIABLO..._003_360p.mp4` (12min24s, 360p) — versão não rastreada no git (decisão do usuário).
**Fluxo:** `03-FLUXO-DE-EDICAO.md` (seção B) · pesquisa `02-PESQUISA-VIRAL.md` · specs `07`.

### Concluído

- [x] `scripts/analisar_bruto.py` → `work/*_analise.md` (energia + cortes de cena ranqueados).
      Zonas quentes: **8:55–9:35** e **11:10–12:24** (+ intro 0:00–0:41).
- [x] Transcrições: `work/bruto.srt` (varredura VAD) e `work/fim.srt` (11:40–12:24, sem VAD, falas reais).
- [x] Assets livres baixados (`scripts/baixar_assets.py` → `assets/` + `assets/CREDITOS.md`).
- [x] Pipeline de render em 2 passos (`scripts/render_short.py`) + `templates/estilo.json`
      (hook no topo, legendas 4–7 palavras com palavra-chave em amarelo, blurpad 9:16,
      zoom pulse, SFX/bgm com loudnorm -14 LUFS, loop, `meta.md` automático).
- [x] **Piloto `01-aura-3x1`** → `output/01-aura-3x1/` (22,8s, 1080×1920) — commit `54b1685`.

### Falta (como proceder)

- [ ] Transcrição do 1º terço: `work/inicio.srt` (roda em background; se morrer, repetir
      `scripts/legendar.py <bruto> --start 0 --dur 535 --lang pt --out work/inicio.srt`).
- [ ] Escolher **+3 momentos**: transcrever a zona quente com `legendar.py` e **conferir frames**
      (`ffmpeg -ss T -frames:v 1`) antes de virar legenda — `--sem-vad` alucina (ver `05`).
- [ ] Para cada: copiar `roteiros/01-aura-3x1.json` → `roteiros/<slug>.json`, ajustar segmentos/zooms/hook;
      `montar_srt.py` (tempos RELATIVOS ao `--start`); `render_short.py`; QA de frames; commit.

### Cuidados já mapeados (ler `05-ERROS-E-APRENDIZADOS.md` antes)

- Fonte **360p** → usar modo `blurpad` (nunca `crop`, fica borrado demais).
- `--sem-vad` repete frase (alucinação); chunk de legenda minúsculo no fim → `chunkize` balanceado já corrigido.
- Black frame de transição no bruto (~12:03) → cortar segmentos nos limites limpos.

---

## TAREFA CONCLUÍDA: shorts virais do bruto Warzone

**Status:** ✅ — **4 shorts entregues** (piloto + 3), todos em `output/` com `meta.md`
(título, legenda do post, hashtags, specs e checklist de QA).

| # | Slug | Duração | Base |
|---|---|---|---|
| 1 | `01-aura-3x1` | 22,8s | fala real "você não tem aura" → morte → 3x1 → cara vence o jogo |
| 2 | `02-oracao-na-troca` | 28,4s | fala real "bóra pai / na cara não / o sangue de Jesus tem poder" na troca |
| 3 | `03-revolta-dos-vencedores` | 22,9s | fala real "é a revolta dos vencedores… é agora que ele vai" |
| 4 | `04-free-kill` | 19,4s | só hook textual (2:54–3:15, sem fala na fonte) |

**QC programático dos 4:** 1080×1920, H.264, duração 19–29s, pico de áudio < 0 dB.

### Como foram feitos (reproduzir p/ próximos)

1. `scripts/analisar_bruto.py` → zonas quentes; `scripts/legendar.py` por zona (VAD ligado).
2. `roteiros/<slug>.json` (copiar um existente) + `scripts/montar_srt.py` (tempos relativos).
3. `scripts/render_short.py roteiros/<slug>.json` → `output/<slug>/video.mp4` + `meta.md`.
4. QA: `ffprobe` (duração/resolução), `volumedetect` (pico < 0 dB) e leitura do `.ass`
   gerado em `work/` (o texto é conferido no `.ass`, não só no frame).

### Aprendizado importante sobre o material

- O bruto de 12min tem **fala real só em 3 trechos** (11:14–11:41, 11:42–12:18, 10:22–10:39);
  o resto é menu/rotação (e o Whisper `--sem-vad` alucina — ver `05`).
- **Próximos shorts exigem material novo** (mais VODs do streamer) ou reaproveitamento
  criativo dos mesmos trechos com outros cortes — backlog em `06-IDEIAS-FUTURAS.md`.

---

## TAREFA EM ANDAMENTO (outra sessão): Tradução do vídeo chinês → PT-BR

**Status:** ✅ CONCLUÍDA (2026-11-15) — entrega em `output/traducao-chines-PTBR/`
(vídeo original intacto + `traducao-chines-PTBR.pt-BR.srt` editável + `meta.md` com
diagnóstico de timeline, incertezas e título sugerido).
**Arquivo:** `Tradução do chinês/ssstik.io_1794764333421.mp4` (51,8s, 1,8 MB, TikTok)
**Decisões do usuário (2026-05):**
- Legendas em arquivo `.srt` **editável, NÃO cravadas** no vídeo.
- Áudio original mantido (sem dublagem).
- Estilo de referência TikTok (para o .srt e futuras legendas).
- Instalações autorizadas.

### Contexto do vídeo (verificado nos frames)

- Gameplay de Warzone (UI PT-BR: "PREPARE-SE PARA LUTA", "Fuzileiro", mapa "Downtown"),
  overlay de moldura/coroa "King Azuos" + **sticker meme chinês** (caricatura + bandeira da China)
  e username "cookY".
- **Áudio MISTO pt-br + chinês** (confirmado pelo usuário) → Whisper detecta 1 idioma por chamada.
- **Estratégia:** transcrever 2× — passada forçando `language='pt'` e passada `language='zh'` —
  e mesclar segmentos por timestamps. Modelo `medium` (o `small` alucinou em trechos com música).

### Passos e status

- [x] Instalar FFmpeg (winget) e faster-whisper + srt (pip)
- [x] Estrutura de pastas + AGENTS.md + DOCS
- [x] Extrair áudio (`scripts/extract_audio.py`) → `work/ssstik.io_1794764333421_audio.wav`
- [x] Transcrição 1 (modelo small) — detectou `zh`, mas alucinou → descartada como base
- [x] Transcrição 2 (modelo medium) — download travou a 976MB; resolvido com `download_model.py`
- [x] Transcrições forçadas `zh` e `pt` (`scripts/transcribe_mixed.py`)
- [x] Mapear idioma por janela (`scripts/lang_map.py`) — 2 passes (4s/2s e 3s/1s)
- [x] Comparar passes (`scripts/compare_passes.py`) → zh vence em logprob; passada pt
      estava traduzindo (espelho semântico) — ver `05-ERROS-E-APRENDIZADOS.md`
- [x] Sonda AUTO por janela (`scripts/lang_probe.py`) — idioma real + texto nativo
      → achado: **pt-br real em 21.7–24.4s** ("ou morra tentando"); resto é chinês + música
- [x] Montar .srt final misto → `work/ssstik.pt-BR.srt` (9 legendas, chinês traduzido,
      pt preservado, música descartada)
- [x] QA de timing/quebras (preview em `work/*_preview.mp4`, frames conferidos — vídeo intacto)
- [x] Entregar em `output/traducao-chines-PTBR/` (vídeo original + .srt + meta.md)
- [x] Registrar aprendizados em `05-ERROS-E-APRENDIZADOS.md`
- [x] Commit

### Como proceder (referências)

- Fluxo detalhado: `03-FLUXO-DE-EDICAO.md` (seção A).
- Erros conhecidos: `05-ERROS-E-APRENDIZADOS.md`.

---

## TAREFA CONCLUÍDA: Setup do projeto

**Status:** ✅ (estrutura, AGENTS.md, DOCS, requirements.txt, pipeline base)

---

## TAREFA CONCLUÍDA: pesquisa viral + higiene do git

**Status:** ✅ — `02-PESQUISA-VIRAL.md` ampliada (dados de retenção, crop no crosshair,
horários de post), `08-REFERENCIAS.md` criada, mp4 brutos fora do versionamento.
