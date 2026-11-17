# 07 — Backlog (futuro, não implementar agora)

Ideias, melhorias e dívidas técnicas que não entram no escopo imediato. Ao
retomar, avaliar custo/benefício e mover para `06-TASKS.md` se for executar.

## Qualidade de áudio

- [ ] **Provider Google Chirp 3 HD** (`pt-BR`): primeiro 1M de chars/mês grátis;
      exige conta/billing. Comparar naturalidade com Francisca.
- [ ] **Provider Azure DragonHD** (`pt-BR-Thalita:DragonHDLatestNeural`):
      potencialmente o mais natural; exige conta Azure/API key.
- [ ] **Fallback local Phonon 40m PT** (Gradio `ptts`, CC BY-NC): melhor Elo
      local; modelo com gate no HF. Implementar como `--engine phonon`.
- [ ] **Fallback local Pocket TTS** (MIT, voz Rafael): simples, sem gate.
- [ ] **Teste A/B com UTMOS/MOS** para escolher voz com métrica objetiva.
- [ ] **Whisper QC**: transcrever 1–2% do áudio e comparar com o texto para
      detectar omissões/alucinações. CPU-only pode ser lento.
- [ ] **Ajuste fino de pausas** por tipo de seção (exercício, quiz, tabela).
- [ ] **Normalização de loudness por seção** em vez de por aula.
- [ ] **Fade in/out** de 50 ms para evitar cliques em joins.

## Conteúdo e estrutura

- [ ] **OCR de diagramas** com Tesseract para capturar rótulos dentro de imagens
      (SWOT, 4 Ps, processo de decisão).
- [ ] **Detecção manual de seções** via `manual_sections` no
      `config/structure.yaml` para páginas problemáticas.
- [ ] **Sumário audível** no início de cada livro (gerado a partir de
      `structure.json`).
- [ ] **Nomes de capítulos mais curtos** para players que truncam.
- [ ] **Versionar o texto em repo privado/Git LFS**, se o usuário quiser.
- [ ] **Gerar EPUB** a partir do texto limpo.
- [ ] **Exportar flashcards/Anki** das listas de vocabulário.
- [ ] **Suporte a EPUB** além de PDF.

## Áudio e entrega

- [ ] **MP3 por subseção** (`S01-01-Participacao.mp3`) além do MP3 por semana.
- [ ] **M4B por subseção** (hoje só por aula/livro).
- [ ] **Capítulos aninhados** (M4B não suporta nativamente; usar títulos
      “S01 — …”).
- [ ] **Capa personalizada** por semana (hoje só capa do livro).
- [ ] **Player/índice HTML** local com links para os arquivos.
- [ ] **Sincronização palavra-a-palavra** usando word boundaries do Edge TTS
      (karaokê/leitura imersiva).
- [ ] **Conversão para OGG/Opus** para menor tamanho.
- [ ] **Ganho de volume opcional** para escuta em ambientes barulhentos.

## Engenharia

- [ ] **`clean-cache`** com retenção por dias/tamanho.
- [ ] **Testes de integração** com PDFs sintéticos (gerados por reportlab) para
      não depender dos PDFs reais.
- [ ] **CI** (GitHub Actions) rodando `ruff` + `pytest` (sem PDFs).
- [ ] **Empacotamento** com `pipx`/wheel.
- [ ] **Interface CLI mais amigável** (Typer/Rich progress).
- [ ] **Log estruturado** em JSON + rotação.
- [ ] **Métricas de build**: tempo por chunk, taxa de retry, tamanho.
- [ ] **Paralelismo por aula** (hoje a concorrência é por chunk).
- [ ] **Suporte a proxy** explícito no `edge-tts`.
- [ ] **Validação de hash do PDF** automática no início do build.

## Documentação

- [ ] **Vídeo/gif curto** demonstrando o build.
- [ ] **FAQ** com erros comuns.
- [ ] **Diagrama atualizado** da arquitetura.
- [ ] **Changelog** por versão.

## Riscos a monitorar

- Edge TTS pode bloquear/limitar; manter fallback documentado.
- Google/Azure podem mudar preços/cotas.
- Modelos locais podem sair do ar/gate.
- Direitos autorais: não redistribuir texto/áudio.
