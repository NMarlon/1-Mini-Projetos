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

## TAREFA EM ANDAMENTO (outra sessão): Tradução do vídeo chinês → PT-BR

**Status:** 🟡 EM ANDAMENTO
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
- [ ] Sonda AUTO por janela (`scripts/lang_probe.py`) — idioma real + texto nativo
- [ ] Montar .srt final misto (zh traduzido + pt real preservado) → `work/*.pt-BR.srt`
- [ ] QA de timing/quebras (preview com legendas, sem cravar)
- [ ] Entregar em `output/` (vídeo original + .srt + meta.md)
- [ ] Registrar aprendizados em `05-ERROS-E-APRENDIZADOS.md`
- [ ] Commit

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
