# 06 — Tarefas

> **Estado atual:** **T00–T15 concluídas.** Os dois livros estão montados e
> verificados; o **modo genérico one-click** também está implementado e
> empacotado. Áudios em `output/MKT-120/` e `output/COM-150/`; app em
> `dist/PDF TTS/PDF TTS.exe` (local, não versionado).
> **Próximo passo:** ouvir as amostras/S01 e testar PDFs reais no app; OCR,
> instalador e assinatura ficam no backlog.

Este é o quadro vivo do projeto. Atualize o status ao final de cada tarefa.
Legenda: `[ ]` pendente · `[~]` em andamento · `[x]` concluído · `[!]` bloqueado.

## Visão geral

| ID | Tarefa | Status | Commit |
|---|---|---|---|
| T00 | Scaffold, AGENTS.md, DOCS, config, .gitignore | `[x]` | `chore(pdf-tts): scaffold, documentação e regras` |
| T01 | Ambiente Python 3.11, dependências, doctor | `[x]` | `chore(pdf-tts): ambiente e verificação de dependências` |
| T02 | Extração + classificação + manuscript | `[x]` | `feat(pdf-tts): extração e estruturação dos PDFs` |
| T03 | Normalização pt-BR + segmentação S01–S07 | `[x]` | `feat(pdf-tts): normalização e segmentação por aula` |
| T04 | Backend Edge TTS, cache, retry, resume | `[x]` | `feat(pdf-tts): backend edge-tts com cache e retomada` |
| T05 | Amostras de voz + guia de pronúncia | `[x]` | `feat(pdf-tts): amostras de voz e guia de pronúncia` |
| T06 | Primeira aula (MKT S01) ponta a ponta | `[x]` | `feat(pdf-tts): primeira aula completa` |
| T07 | Ajustes de qualidade (pausas, loudness, joins) | `[x]` | `fix(pdf-tts): ajustes de qualidade de áudio` |
| T08 | Build completo MKT 120 | `[x]` | `feat(pdf-tts): build completo do MKT 120` |
| T09 | Build completo COM 150 | `[x]` | `feat(pdf-tts): build completo do COM 150` |
| T10 | Verificação final e manifests | `[x]` | `chore(pdf-tts): verificação final e manifests` |
| T11 | Documentação final e handoff | `[x]` | `docs(pdf-tts): handoff e estado final` |
| T12 | Ingestão genérica + detecção de capítulos | `[x]` | `feat(pdf-tts): conversão genérica e detecção de capítulos` |
| T13 | Interface local + fila de jobs | `[x]` | `feat(pdf-tts): interface one-click e fila de conversões` |
| T14 | Empacotamento portátil Windows | `[x]` | `build(pdf-tts): empacotamento portátil Windows` |
| T15 | Testes/QA do app one-click e docs | `[x]` | `docs(pdf-tts): guia do app one-click` |

Tarefas opcionais no [`07-BACKLOG.md`](07-BACKLOG.md).

---

## Estado final (2026-11-17)

### App one-click (2026-11-18)

- `python -m pdf_tts gui` abre a interface local.
- `dist/PDF TTS/PDF TTS.exe` é o portátil Windows (gerado por
  `packaging/build_portable.ps1`; não versionado).
- Detecta capítulos por outline/fonte/padrões; sem estrutura, avisa e divide em
  blocos de 10 páginas.
- Modo **Automático** (padrão) e **Tudo (fiel)**.
- Capítulos: automático, manual ou livro inteiro.
- `coverage.json` lista páginas sem áudio e páginas só de imagem.
- Teste ponta a ponta com PDF sintético e com o `.exe` empacotado: **OK**.
- Detalhes em [`12-ONE-CLICK-APP.md`](12-ONE-CLICK-APP.md).

### Entregas

| Livro | Aulas | Duração | Capítulos | Cues SRT | Tamanho |
|---|---|---|---|---|---|
| MKT 120 | S01–S07 | 03:39:26 | 68 | 1.473 | ~425 MB |
| COM 150 | S01–S07 | 07:50:42 | 92 | 3.457 | ~910 MB |
| **Total** | **14** | **11:30:08** | **160** | **4.930** | **1,335 GB** |

Arquivos em:

- `output/MKT-120/` — S01…S07 `.mp3`/`.m4b`/`.srt`, `MKT-120-completo.*`, `cover.jpg`, `manifest.json`, `README.md`.
- `output/COM-150/` — o mesmo para o COM 150.

Os manifests versionados estão em `manifests/MKT-120.json` e
`manifests/COM-150.json`.

### Verificação

- `python -m pdf_tts verify --project all` → **tudo OK**.
- Loudness: **-16,45 LUFS**; true peak entre **-1,36 e -0,79 dB**.
- Nenhum silêncio > 5 s.
- Capítulos e capa presentes em todos os M4B.
- SRT termina dentro da duração de cada áudio.
- 43 testes automatizados (`pytest`) passando.
- Nenhum PDF/texto/áudio versionado no Git.

### Limitações conhecidas

- A IA não ouviu o áudio subjetivamente; a aprovação foi **técnica**. Ouça as
  amostras e a S01 e reporte pronúncias estranhas (página/trecho) para ajustar o
  léxico.
- Alguns textos de tabelas/diagramas podem soar truncados; os rótulos dentro de
  imagens não passam por OCR.
- SRT é por frase, não palavra a palavra.
- Edge TTS é um serviço não oficial; o cache e o `--resume` protegem o build.
- Áudio/texto/PDFs ficam fora do Git por direitos autorais e tamanho.

### Como ouvir

1. Abra `output/MKT-120/S01.m4b` no Apple Books/VLC/Android (capítulos por seção).
2. Ou use os MP3 por aula em qualquer player.
3. Para legendas, carregue o `.srt` de mesmo nome no VLC.
4. Para comparar vozes, ouça `samples/francisca.mp3`, `antonio.mp3` e
   `thalita.mp3`.

### Se precisar regerar

```powershell
python -m pdf_tts build --project mkt120 --lesson S01 --force
python -m pdf_tts assemble --project mkt120 --lesson S01
python -m pdf_tts verify --project mkt120 --lesson S01
```

Para mudar pronúncia, edite `config/pronunciation.pt-BR.yaml`, rode
`segment`/`build`/`assemble` do escopo afetado e registre em
`DOCS/09-DECISIONS.md`.

---

## T00 — Scaffold e documentação

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Criar a árvore do projeto.
- Escrever `AGENTS.md` (raiz e projeto), `README.md`, `.gitignore`,
  `pyproject.toml`.
- Criar `DOCS/00`…`11`.
- Criar `config/projects.yaml`, `structure.yaml`, `pronunciation.pt-BR.yaml`.
- Criar `input/README.md`, `content/README.md`, `manifests/README.md`,
  `samples/README.md`.
- Mover os PDFs para `input/` e registrar SHA-256.

**Critério de aceite:**
- `git status` mostra apenas arquivos do projeto.
- PDFs não aparecem como untracked (ignorados).
- Documentação cobre objetivo, arquitetura, pesquisa, pipeline, operações,
  erros, decisões, voz e verificação.
- Commit feito.

**Referências:** `00-OVERVIEW.md`, `01-ARCHITECTURE.md`, `02-RESEARCH-TTS.md`.

---

## T01 — Ambiente e doctor

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- `py -3.11 -m venv .venv`.
- Instalar `-e ".[dev]"`.
- Implementar `doctor.py` e o comando `pdf_tts doctor`.
- Validar ffmpeg/ffprobe, codecs, edge-tts, vozes pt-BR, conectividade, PDFs e
  SHA-256, espaço em disco.
- Gerar `requirements.lock.txt` (`pip freeze`).
- Rodar `pytest` (mesmo sem testes ainda).

**Critério de aceite:**
- `python -m pdf_tts doctor` sai com código 0 e mostra tudo OK.
- `edge-tts --list-voices` lista as 3 vozes pt-BR.
- `.venv` no `.gitignore`.
- Commit feito.

**Referências:** `05-OPERATIONS.md`.

---

## T02 — Extração e estruturação

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Implementar `extract.py`, `classify.py`, `clean.py`, `segment.py` (parte de
  manuscript).
- Gerar `content/mkt120/` e `content/com150/`.
- Comparar as contagens de caracteres por semana com `03-PDF-PIPELINE.md`.
- Revisar `manuscript.md` das páginas difíceis: MKT 10/12/13/17; COM 19–23.
- Ajustar regras de referências, cabeçalhos e tabelas.
- Escrever testes de limpeza com texto sintético.

**Critério de aceite:**
- 7 semanas por projeto, com páginas corretas.
- Nenhum PUA/ligadura no texto.
- `skipped.jsonl` com motivos plausíveis.
- `manuscript.md` legível e sem trechos grandes faltando.
- Nenhum PDF/texto commitado.
- Commit feito.

**Referências:** `03-PDF-PIPELINE.md`.

---

## T03 — Normalização e segmentação

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Implementar `normalize.py` e `chunking.py`.
- Aplicar léxico, números, moedas, percentuais, datas, siglas, `S01`.
- Transformar `________` em “lacuna” e opções em “Opção:”.
- Gerar `lessons/S01.json`…`S07.json` e `.txt`.
- Escrever testes de normalização e chunking.
- Revisar uma amostra de cada tipo de conteúdo (exercício, quiz, tabela,
  tarefa, conclusão).

**Critério de aceite:**
- Nenhum `S01` ou `MKT 120` cru no texto falado.
- Números por extenso corretos em pt-BR.
- Chunks entre 80 e 1200 chars (exceto títulos).
- Nenhum chunk vazio.
- Commit feito.

**Referências:** `04-AUDIO-PIPELINE.md`, `10-VOICE-AND-PRONUNCIATION.md`.

---

## T04 — Backend Edge TTS

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Implementar `tts/base.py`, `tts/edge.py`, `tts/fake.py`, `state.py`.
- Cache por hash, escrita atômica, validação `ffprobe`, retry, concorrência.
- Implementar `build` (síntese) e `status`.
- Testes com backend fake (sem rede).
- Teste real com uma frase curta.

**Critério de aceite:**
- Chunk válido é cacheado e reutilizado.
- Chunk inválido é rejeitado e repetido.
- Interromper e retomar não re-sintetiza o que já está `done`.
- Commit feito.

**Referências:** `04-AUDIO-PIPELINE.md`, `08-ERRORS-AND-LESSONS.md`.

---

## T05 — Amostras de voz

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Implementar `samples`.
- Gerar Francisca, Antonio e Thalita com o mesmo texto sintético.
- Gerar um teste de pronúncia com números, siglas, datas, `S01`, `MKT 120`,
  termos em inglês e `________`.
- Documentar a escolha e como trocar de voz.

**Critério de aceite:**
- 4 arquivos em `samples/`, audíveis, com duração > 5 s.
- `10-VOICE-AND-PRONUNCIATION.md` atualizado.
- Commit feito (áudio sintético é permitido).

**Referências:** `10-VOICE-AND-PRONUNCIATION.md`.

---

## T06 — Primeira aula (MKT S01)

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Gerar `output/MKT-120/S01.mp3`, `.m4b`, `.srt`.
- Validar duração, capítulos, loudness, SRT.
- Ouvir (ou no mínimo inspecionar) o início, o meio e o fim.
- Ajustar pausas/pronúncia se necessário.
- Criar `manifests/MKT-120.json` parcial.

**Critério de aceite:**
- MP3/M4B/SRT existem e são válidos.
- Duração > 90% da estimativa.
- Capítulos navegáveis.
- Nenhum chunk falhado.
- Commit feito.

**Referências:** `04-AUDIO-PIPELINE.md`, `11-VERIFICATION.md`.

---

## T07 — Ajustes de qualidade

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Corrigir problemas encontrados na S01: pronúncia, pausas, joins, volume.
- Ajustar léxico e regras de chunking.
- Re-gerar S01 e comparar.
- Atualizar `08-ERRORS-AND-LESSONS.md`.

**Critério de aceite:**
- Problemas registrados e corrigidos.
- S01 aprovada nos critérios de `11-VERIFICATION.md`.
- Commit feito.

---

## T08 — Build completo MKT 120

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Rodar `build --project mkt120 --resume`.
- Gerar S01…S07 + livro completo.
- Validar todos os arquivos.
- Atualizar `manifests/MKT-120.json`.

**Progresso (2026-11-17):** build concluído com **1.337 textos únicos / 0
falhas**; re-extração aplicou o fix E035; montagem gerou S01–S07 + livro
completo (3h39, 68 capítulos, ~450 MB). Verificação técnica em andamento.
Logs: `logs/build-mkt120.log`.

**Critério de aceite:**
- 7 MP3 + 7 M4B + 7 SRT + completo MP3/M4B.
- Nenhum chunk falhado.
- Manifest completo.
- Commit feito.

---

## T09 — Build completo COM 150

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Rodar `build --project com150 --resume`.
- Gerar S01…S07 + livro completo.
- Validar todos os arquivos.
- Atualizar `manifests/COM-150.json`.

**Progresso (2026-11-17):** build concluído com **3.222 textos únicos / 0
falhas**; montagem gerou S01–S07 + livro completo (7:50:42, 92 capítulos);
`verify` 100% OK (-16,45 LUFS; TP ≤ -0,79; sem silêncios >5 s). Log:
`logs/build-com150.log`.

**Critério de aceite:**
- 7 MP3 + 7 M4B + 7 SRT + completo MP3/M4B.
- Nenhum chunk falhado.
- Manifest completo.
- Commit feito.

---

## T10 — Verificação final

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Rodar `pytest`.
- Rodar `status` e um script de verificação de duração/capítulos/SRT.
- Conferir loudness de uma amostra de cada aula.
- Conferir que nenhum PDF/texto/áudio foi commitado.
- Atualizar `11-VERIFICATION.md` com os resultados.

**Critério de aceite:**
- Checklist de `11-VERIFICATION.md` cumprido.
- Commit feito.

---

## T11 — Documentação final e handoff

**Status:** `[x]` (2026-11-17)

**O que fazer:**
- Atualizar `README.md`, `05-OPERATIONS.md`, `06-TASKS.md`.
- Escrever o estado final, onde estão os áudios e o que falta.
- Registrar decisões finais e pendências no backlog.
- Commit final.

**Critério de aceite:**
- Uma IA nova consegue entender o estado em < 10 min.
- Comandos de reprodução funcionam.
- Commit feito.

---

## T12–T15 — App one-click (2026-11-18)

**Status:** `[x]`

**Entregas:**
- `discover.py`: outline, títulos por fonte, padrões, fallback por páginas,
  remoção de sumário, capítulos contínuos.
- `generic.py`: projeto dinâmico, `--mode auto|all`, `--chapters
  auto|none|manual`, `coverage.json`.
- `api.py` + `web/` + `launcher.py`: upload, análise, editor de capítulos,
  progresso, abrir pasta, fila SQLite.
- `packaging/`: spec PyInstaller, entrypoint, LEIA-ME, build portátil.
- `tests`: 52 testes, incluindo descoberta, API e montagem.
- Teste real do `.exe` com PDF sintético: upload → job → MP3/M4B/SRT → OK.

**Critério de aceite atendido:**
- PDF sem estrutura gera áudio e aviso.
- “Tudo” mantém referências; “Automático” limpa.
- Páginas com texto sem áudio aparecem no relatório.
- Páginas de imagem são listadas; OCR fica para a v2.
- App roda sem Python/FFmpeg instalados no Windows.

**Referência:** [`12-ONE-CLICK-APP.md`](12-ONE-CLICK-APP.md).

## Diário de progresso

| Data | Tarefa | Observação |
|---|---|---|
| 2026-11-17 | T00 | Scaffold e documentação inicial criados; PDFs movidos para `input/` e ignorados no Git. |
| 2026-11-17 | T01 | `.venv` 3.11 criado; dependências instaladas; `doctor` OK (20 checks); 4 testes passando. |
| 2026-11-17 | T02 | Extração concluída: MKT 179.597 chars / 901 blocos; COM 389.692 chars / 2.103 blocos; 7 semanas cada; PUA/URLs zero; tabelas formatadas; referências removidas. |
| 2026-11-17 | T03 | 1.473 chunks MKT / 3.457 COM; 35 testes; sem dígitos/S01 nos textos falados; duração estimada 3h22 + 7h11. |
| 2026-11-17 | T04 | Backend Edge com cache/retry/resume; S01 MKT sintetizada (162 chunks, 0 falhas, 2m39s); retomada 100% cache em 1s. |
| 2026-11-17 | T05 | Amostras geradas: francisca 28,2s; antonio 31,7s; thalita 28,6s; pronúncia 36,7s. |
| 2026-11-17 | T06 | MKT S01: 23:05, 11 capítulos, 163 cues SRT, -16,46 LUFS / TP -1,46; MP3 11,1 MB; M4B 11,2 MB com capa 1081x1400. |
| 2026-11-17 | T07 | QA técnico da S01 aprovado: nenhum silêncio >3 s; capítulos/cover/metadata OK; `-dn/-sn` no M4B. |
| 2026-11-17 | T08 | MKT completo: 7 aulas + livro (3:39:26), 1.473 cues, 68 capítulos, 425 MB; verify 100% OK (-16,45 LUFS; TP ≤ -0,94; sem silêncios >5 s). |
| 2026-11-17 | T09 | COM completo: 7 aulas + livro (7:50:42), 3.457 cues, 92 capítulos; verify 100% OK (-16,45 LUFS; TP ≤ -0,79; sem silêncios >5 s). |
| 2026-11-17 | T10 | Verificação final dos dois livros: 54 arquivos, 1,335 GB, 14 aulas + 2 completos; tudo OK. |
| 2026-11-17 | T11 | Documentação final, README e handoff atualizados. |
| 2026-11-18 | T12 | Modo genérico: descoberta por outline/fonte/fallback; modo Automático/Tudo; cobertura. |
| 2026-11-18 | T13 | Interface FastAPI + web local, fila SQLite, progresso, editor de capítulos; teste com PDF sintético. |
| 2026-11-18 | T14 | PyInstaller onedir + ffmpeg/ffprobe + LEIA-ME; `.exe` testado com upload e job completo. |
| 2026-11-18 | T15 | 52 testes passando; documentação one-click e backlog atualizados. |
