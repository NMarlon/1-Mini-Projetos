# AGENTS.md — Pathway PDF TTS

Este arquivo é a **porta de entrada** para qualquer agente de IA que for
continuar este projeto. Leia até o fim antes de alterar código, executar builds
ou fazer commits.

Atue como **Desenvolvedor Full-Stack experiente**: entenda o produto inteiro
(CLI, app, web, fila, empacotamento e documentação), preserve a arquitetura,
teste o que mudar e deixe o repositório reproduzível.

## 1. Objetivo

O projeto tem dois produtos que compartilham o mesmo núcleo:

1. **Modo curado** — os dois PDFs do Pathway já configurados:
   - `input/MKT 120.pdf` → `output/MKT-120/`
   - `input/Livro texto COM 150-1.pdf` → `output/COM-150/`
2. **Pathway PDF TTS** — app one-click para qualquer PDF com camada de texto:
   - detecta capítulos do Pathway (`Semana 1…7`, `S01…S07`);
   - aceita PDFs de outras origens no perfil genérico;
   - gera MP3 por capítulo, M4B com marcadores, SRT, livro completo,
     `coverage.json`, `manifest.json` e `README.md`.

Cada livro curado é dividido em 7 aulas/semanas (`S01`…`S07`), com:

- MP3 por aula;
- M4B por aula e um M4B completo, com capítulos e capa;
- SRT por aula;
- manifest com voz, ritmo, durações, páginas e hashes.

O conteúdo é falado com **Edge TTS**, voz **pt-BR-FranciscaNeural**, ritmo
**-5%**. A decisão e as alternativas estão em
[`DOCS/02-RESEARCH-TTS.md`](DOCS/02-RESEARCH-TTS.md) e
[`DOCS/09-DECISIONS.md`](DOCS/09-DECISIONS.md).

## 2. Ordem de leitura obrigatória

1. `AGENTS.md` (este arquivo)
2. [`DOCS/00-OVERVIEW.md`](DOCS/00-OVERVIEW.md) — visão geral e escopo
3. [`DOCS/06-TASKS.md`](DOCS/06-TASKS.md) — **estado atual e próxima tarefa**
4. [`DOCS/01-ARCHITECTURE.md`](DOCS/01-ARCHITECTURE.md) — módulos e fluxos
5. [`DOCS/03-PDF-PIPELINE.md`](DOCS/03-PDF-PIPELINE.md) — extração, perfis e
   modos de conteúdo
6. [`DOCS/04-AUDIO-PIPELINE.md`](DOCS/04-AUDIO-PIPELINE.md) — TTS, FFmpeg e
   montagem sem console
7. [`DOCS/05-OPERATIONS.md`](DOCS/05-OPERATIONS.md) — comandos e troubleshooting
8. [`DOCS/08-ERRORS-AND-LESSONS.md`](DOCS/08-ERRORS-AND-LESSONS.md) — erros já
   cometidos
9. [`DOCS/09-DECISIONS.md`](DOCS/09-DECISIONS.md) — decisões arquiteturais
10. [`DOCS/10-VOICE-AND-PRONUNCIATION.md`](DOCS/10-VOICE-AND-PRONUNCIATION.md)
11. [`DOCS/11-VERIFICATION.md`](DOCS/11-VERIFICATION.md) — critérios de aceite
12. [`DOCS/12-ONE-CLICK-APP.md`](DOCS/12-ONE-CLICK-APP.md) — app, API,
    detecção, empacotamento e limitações
13. [`DOCS/13-COMO-BAIXAR-O-PDF.md`](DOCS/13-COMO-BAIXAR-O-PDF.md) — tutorial
    visual para baixar o PDF pelo site do curso
14. [`DOCS/14-REPO-PROTOCOL.md`](DOCS/14-REPO-PROTOCOL.md) — protocolo do
    repositório, autonomia, commits, continuidade e o que fica fora do Git

## 3. Estado atual (2026-11-18)

- **T00–T20 concluídas.**
- **60 testes** passando; `ruff` limpo.
- Protocolo permanente e lock reproduzível em `DOCS/14-REPO-PROTOCOL.md` e
  `requirements.lock.txt`.
- Suporte por e-mail na interface, no rodapé e nos LEIA-MEs:
  `marlonrviana@gmail.com`; o card também abre, baixa e copia `logs/app.log`.
- MKT 120 e COM 150 montados e verificados:
  - MKT 120: 3:39:26, 68 capítulos, 1.473 cues;
  - COM 150: 7:50:42, 92 capítulos, 3.457 cues.
- App **Pathway PDF TTS v0.3.0** implementado:
  - perfil Pathway/genérico/automático;
  - modos `auto`, `all`, `raw`;
  - upload em blocos, fila SQLite, progresso e reanálise;
  - instância única, health check e logs;
  - FFmpeg sem janelas de CMD;
  - empacotamento com Python assinado + PyInstaller alternativo.
- Artefatos locais (não versionados):
  - `dist/Pathway PDF TTS/Pathway PDF TTS.exe` — **principal**;
  - `dist/Pathway-PDF-TTS-Windows.zip`;
  - `dist/Pathway PDF TTS (PyInstaller)/` — alternativa;
  - `dist/Pathway-PDF-TTS-Windows-PyInstaller.zip`.
- **Smart App Control:** a versão principal passa por usar o `pythonw.exe`
  assinado pela Python Software Foundation. A versão PyInstaller pode ser
  bloqueada (“política de Controle de Aplicativo”).
- Próximo passo: ouvir as amostras/S01 e testar PDFs reais; OCR, assinatura
  própria e instalador estão no backlog.

### O que já foi validado manualmente

- COM 150 real: análise Pathway em ~20 s, 8 capítulos.
- MKT 120 real: 8 capítulos Pathway.
- PDF sintético: `auto`/`all` removem cabeçalho/página/URL; `raw` mantém.
- Job sintético `raw`: 15 arquivos finais.
- `.exe` principal: health `pathway-pdf-tts` v0.3.0.
- ZIP principal extraído e executado.
- `run_hidden`: 10 chamadas de ffmpeg sem novos `cmd`/`conhost`.

### 3.1 Protocolo permanente do repositório

O protocolo completo está em
[`DOCS/14-REPO-PROTOCOL.md`](DOCS/14-REPO-PROTOCOL.md). Resumo:

1. Aja como desenvolvedor full-stack experiente.
2. Tudo que é **fundamental** (código, config, testes, docs, scripts, lock,
   manifests curados) fica no repositório. PDFs/áudio/texto e artefatos
   gerados ficam fora por copyright/tamanho, mas são reconstruíveis.
3. Toda a documentação fica em `DOCS/`.
4. `AGENTS.md` é a porta de entrada e referencia os documentos.
5. Erros e aprendizados ficam em `DOCS/08-ERRORS-AND-LESSONS.md`.
6. Tarefas e continuidade ficam em `DOCS/06-TASKS.md`.
7. Ideias futuras ficam em `DOCS/07-BACKLOG.md`.
8. Commit ao final de **cada** tarefa; o usuário usa os commits como rollback.
9. Autonomia máxima: só pare por ambiguidade, credencial, risco ou decisão de
   produto.
10. Dúvida ou ambiguidade: **pare e pergunte**; não invente requisito.
11. Diante de erro: reproduza, ache a causa raiz, corrija, teste, documente e
    commit.

Arquivos fundamentais não podem existir apenas em `temp/` ou fora do repo.
`temp/` é local do usuário e está no `.gitignore`.

## 4. Regras rígidas (o que você DEVE e o que NÃO DEVE fazer)

### 4.1 Perguntar antes de assumir

**Pare e pergunte** ao usuário quando houver:

- dúvida sobre escopo do conteúdo (o que entra ou não no áudio);
- mudança de voz, motor de TTS ou ritmo;
- necessidade de credencial/conta (Google Cloud, Azure, Hugging Face);
- conflito entre documentação e código;
- risco de apagar `cache/`, `content/`, `output/`, `input/` ou PDFs;
- dúvida sobre licença/copyright;
- qualquer ação destrutiva (`git reset --hard`, `git clean`, apagar arquivos);
- mudança no nome do app, portas ou formato dos ZIPs.

Não invente resposta. Registre a dúvida em `DOCS/06-TASKS.md` se precisar parar.

### 4.2 Autonomia

O usuário pediu **autonomia máxima**. Continue sem pedir confirmação para:

- criar/editar arquivos do projeto;
- instalar dependências no `.venv`;
- rodar extração, testes e builds;
- gerar áudio em `output/`;
- gerar os portáteis em `dist/`;
- fazer commits locais ao final de cada tarefa.

Só interrompa por: ambiguidade real, credencial ausente, ação destrutiva,
mudança de escopo/voz ou risco de perda de dados.

### 4.3 Commits

- Faça **um commit ao final de cada tarefa** concluída.
- Use mensagens convencionais:
  - `feat(pathway-tts): …`
  - `fix(pathway-tts): …`
  - `build(pathway-tts): …`
  - `docs(pathway-tts): …`
- Antes de commitar, rode `git status` e confira se só há arquivos deste
  projeto. **Não** inclua alterações de outros projetos nem arquivos do usuário
  em `temp/`.
- **Nunca** commite:
  - `input/*.pdf` (direitos autorais);
  - `content/` (texto extraído, direitos autorais);
  - `output/` (áudio, ~1,2 GB);
  - `cache/` (chunks, estado, jobs);
  - `dist/` e `build/` (executáveis e artefatos);
  - `manifests/AUTO-*.json` (PDFs arbitrários);
  - `temp/` (arquivos do usuário);
  - `.venv/`, segredos, logs.
- **Nunca** faça `push` sem pedido explícito.
- Se um commit falhar, resolva e registre em
  `DOCS/08-ERRORS-AND-LESSONS.md`.

### 4.4 Fonte de verdade

- Os PDFs em `input/` são **imutáveis**. Nunca edite, recorte ou substitua.
- Se o SHA-256 não bater com `input/README.md`, pare e pergunte.
- O texto limpo em `content/` é **derivado** e pode ser regenerado.
- O áudio em `output/` é **derivado** e pode ser regenerado.
- `manifests/` é a fonte de verdade do que foi gerado.
- Não edite o texto em `content/` à mão para “consertar” o áudio. Corrija a
  regra em `src/pdf_tts/` ou o léxico em `config/pronunciation.pt-BR.yaml` e
  regenere.
- O `sitecustomize.py` do pacote portátil é **gerado** por
  `packaging/build_python_portable.ps1`; não o edite à mão no `dist/`.

### 4.5 Qualidade

- Nunca aceite chunk vazio ou com duração zero. Valide com `ffprobe`.
- Nunca misture vozes no meio de um livro sem pedir.
- Nunca altere `voice`/`rate` silenciosamente. Se mudar, registre em
  `manifests/` e em `DOCS/09-DECISIONS.md`.
- Antes de um build completo, gere e valide a primeira aula (`S01`).
- Rode `pytest` antes de cada commit que altere código.
- Se o Edge TTS falhar repetidamente, **pare** e preserve o cache; não troque
  de motor automaticamente.
- A interface one-click usa **uma fila e um job por vez**; não rode dois builds
  Edge simultâneos.
- O modo genérico deve sempre avisar quando uma página com texto ficar sem
  áudio e nunca descartar páginas silenciosamente.
- **Todo subprocesso externo** (ffmpeg/ffprobe) deve usar
  `pdf_tts.audio.run_hidden()`; nunca `subprocess.run` direto em app GUI.
- Novas mudanças em `discover.py` precisam passar pelos testes de perfil
  Pathway e pelo `detect` nos PDFs reais MKT/COM.

### 4.6 Ambiente

- Use **Python 3.11** (`.venv`). O `py` padrão é 3.15 e pode quebrar
  dependências.
- Windows + PowerShell. Use `pathlib` e UTF-8 em todos os arquivos.
- FFmpeg/ffprobe precisam estar no `PATH` no modo curado; `doctor` valida.
- Não use PyMuPDF (AGPL). A extração é feita com `pdfplumber` (MIT).
- Não adicione dependências pesadas (torch, kokoro, etc.) sem aprovação; o
  fallback local está no backlog.

### 4.7 Documentação viva

Ao final de **toda** tarefa, atualize:

- `DOCS/06-TASKS.md` — status, data, próximo passo;
- `DOCS/08-ERRORS-AND-LESSONS.md` — erros e aprendizados;
- `DOCS/09-DECISIONS.md` — novas decisões;
- `DOCS/11-VERIFICATION.md` — se mudou critério de aceite;
- `DOCS/12-ONE-CLICK-APP.md` — se mexeu no app/empacotamento;
- `manifests/` — se gerou áudio.

Se você parar no meio de uma tarefa, deixe o comando exato para continuar.

## 5. Estrutura do repositório

```text
PDF TTS/
├─ AGENTS.md                 ← este arquivo
├─ README.md                 ← início rápido
├─ pyproject.toml
├─ config/
│  ├─ projects.yaml          ← projetos curados, páginas, voz/rate
│  ├─ structure.yaml         ← regras de detecção de títulos/seções
│  └─ pronunciation.pt-BR.yaml
├─ input/                    ← PDFs (local, não versionado)
├─ content/                  ← texto limpo (local, não versionado)
├─ src/pdf_tts/
│  ├─ cli.py, config.py, models.py
│  ├─ extract.py, clean.py, segment.py, normalize.py, chunking.py, lessons.py
│  ├─ tts/, build.py, state.py, assemble.py, verify.py, audio.py, doctor.py
│  ├─ discover.py, generic.py, api.py, jobs.py, launcher.py
│  └─ web/                    ← index.html, app.js, style.css
├─ tests/
├─ scripts/                   ← setup/doctor/run-all/make_test_pdf
├─ samples/                   ← amostras sintéticas de voz (versionadas)
├─ manifests/                 ← manifests de build (versionados, sem texto)
├─ packaging/                 ← builds portáteis, spec, LEIA-MEs
├─ DOCS/                      ← documentação
├─ output/                    ← áudio (local, não versionado)
├─ cache/                     ← chunks/estado/jobs (local, não versionado)
├─ dist/                      ← portáteis (local, não versionado)
└─ temp/                      ← arquivos do usuário (não versionar)
```

## 6. Fluxo resumido

### Setup

```powershell
cd "PDF TTS"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pdf_tts doctor
```

### Pipeline curado

```powershell
python -m pdf_tts extract --project all
python -m pdf_tts segment --project all
python -m pdf_tts samples
python -m pdf_tts build --project mkt120 --lesson S01
python -m pdf_tts all --project all
```

### App pelo código-fonte

```powershell
python -m pdf_tts gui
python -m pdf_tts serve --port 8899
python -m pdf_tts detect "input\Livro texto COM 150-1.pdf" --profile pathway
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode auto
```

### Portáteis

```powershell
# Principal: Python assinado (funciona com Smart App Control)
.\packaging\build_python_portable.ps1

# Alternativa: PyInstaller (menor, sem assinatura; pode ser bloqueada)
.\packaging\build_portable.ps1
```

Saídas:

```text
dist/Pathway PDF TTS/Pathway PDF TTS.exe
dist/Pathway-PDF-TTS-Windows.zip
dist/Pathway PDF TTS (PyInstaller)/Pathway PDF TTS.exe
dist/Pathway-PDF-TTS-Windows-PyInstaller.zip
```

### Testes

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests packaging
.\.venv\Scripts\python.exe -m pytest -q
```

## 7. App Pathway PDF TTS

### Modos de conteúdo

| Modo | `content_mode` | Comportamento |
|---|---|---|
| Automático | `auto` | Limpa bibliografia, créditos e boilerplate. |
| Tudo útil | `all` | Inclui referências/notas; remove cabeçalho, página, URL. |
| Tudo literal | `raw` | Inclui tudo extraído, inclusive cabeçalho/página/link. |

### Perfis

- `auto` — Pathway primeiro, depois outline, genérico e blocos.
- `pathway` — força Semana/S01–S07; se não achar, avisa e cai para genérico.
- `generic` — outline, títulos por fonte/padrões e blocos.

### Receitas da interface

- **Automático** = `auto` + capítulos automáticos.
- **Identificar capítulos** = `auto` + capítulos manuais/editáveis.
- **Tudo útil** = `all` + capítulos automáticos.
- **Tudo literal** = `raw` + capítulos automáticos.

### Robustez que não pode regredir

- upload em blocos, limite 500 MB, validação `%PDF-`;
- análise mostrando tempo e progresso do envio;
- `GET /api/health` e banner de conexão;
- instância única e confirmação ao fechar;
- reanálise por `POST /api/reanalyze`;
- logs em `logs/app.log`, `launcher.log`, `crash.log`;
- `run_hidden` para ffmpeg/ffprobe;
- uma fila SQLite (`cache/jobs.db`), um job por vez;
- `coverage.json` com páginas sem áudio e só imagem.

### Smart App Control

A versão principal usa uma cópia assinada do `pythonw.exe` da Python Software
Foundation, renomeada para `Pathway PDF TTS.exe`, com `Lib`, `DLLs`, `tcl`,
`site-packages`, `src`, `config` e FFmpeg locais. Isso evita o bloqueio de
“política de Controle de Aplicativo” que atinge o PyInstaller sem assinatura.

Não troque a versão principal por PyInstaller sem testar em máquina com Smart
App Control ativo.

## 8. Definition of Done

Uma tarefa só termina quando:

- o código roda sem erro no Python 3.11;
- os testes relevantes passam;
- a documentação da tarefa foi atualizada;
- os arquivos gerados foram validados (quando aplicável);
- o commit foi feito (ou o motivo de não ter sido registrado).

O projeto inteiro só termina quando `DOCS/11-VERIFICATION.md` estiver cumprido
e os dois livros tiverem MP3, M4B e SRT validados.
