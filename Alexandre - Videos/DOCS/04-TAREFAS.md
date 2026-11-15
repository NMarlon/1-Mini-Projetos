# 04 — TAREFAS (status do trabalho)

> **Formato:** cada tarefa tem status, passo atual (onde parou) e como proceder.
> Ao continuar: atualize este arquivo ANTES de encerrar a sessão.

---

## TAREFA ATUAL: Tradução do vídeo chinês → PT-BR (legendas editáveis)

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
- [ ] Mapear idioma por janela (`scripts/lang_map.py`) — em execução
- [ ] Montar .srt final misto (zh traduzido + pt revisado) → `work/*.pt-BR.srt`
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

## PRÓXIMA TAREFA (prevista): primeiro short viral do bruto Warzone

- Bruto: `YTDown..._MORRE-DIABLO..._003_360p.mp4` (12min24s, 360p).
- Fluxo: `03-FLUXO-DE-EDICAO.md` (seção B). Pesquisa: `02-PESQUISA-VIRAL.md`.
- Bloqueio: nenhum (não iniciada — começar analisando o bruto).
