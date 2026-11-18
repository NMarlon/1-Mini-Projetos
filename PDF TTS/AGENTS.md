# AGENTS.md — PDF TTS

Este arquivo é a **porta de entrada** para qualquer agente de IA que for
continuar este projeto. Leia até o fim antes de alterar código, executar builds
ou fazer commits.

## 1. Objetivo

Transformar os dois PDFs do curso em audiolivros em português brasileiro:

- `input/MKT 120.pdf` → `output/MKT-120/`
- `input/Livro texto COM 150-1.pdf` → `output/COM-150/`

Cada livro é dividido em 7 aulas/semanas (`S01`…`S07`), com:

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
4. [`DOCS/01-ARCHITECTURE.md`](DOCS/01-ARCHITECTURE.md) — módulos e fluxo
5. [`DOCS/03-PDF-PIPELINE.md`](DOCS/03-PDF-PIPELINE.md) — extração e limpeza
6. [`DOCS/04-AUDIO-PIPELINE.md`](DOCS/04-AUDIO-PIPELINE.md) — TTS e montagem
7. [`DOCS/05-OPERATIONS.md`](DOCS/05-OPERATIONS.md) — comandos e troubleshooting
8. [`DOCS/08-ERRORS-AND-LESSONS.md`](DOCS/08-ERRORS-AND-LESSONS.md) — erros já cometidos
9. [`DOCS/09-DECISIONS.md`](DOCS/09-DECISIONS.md) — decisões arquiteturais
10. [`DOCS/10-VOICE-AND-PRONUNCIATION.md`](DOCS/10-VOICE-AND-PRONUNCIATION.md)
11. [`DOCS/11-VERIFICATION.md`](DOCS/11-VERIFICATION.md) — critérios de aceite
12. [`DOCS/12-ONE-CLICK-APP.md`](DOCS/12-ONE-CLICK-APP.md) — app one-click,
    detecção genérica, interface, empacotamento e limitações

## 3. Estado atual

Leia sempre a seção **“Estado atual”** no topo de
[`DOCS/06-TASKS.md`](DOCS/06-TASKS.md). Ela diz exatamente em qual tarefa o
projeto parou e qual é o próximo comando.

## 4. Regras rígidas (o que você DEVE e o que NÃO DEVE fazer)

### 4.1 Perguntar antes de assumir

**Pare e pergunte** ao usuário quando houver:

- dúvida sobre escopo do conteúdo (o que entra ou não no áudio);
- mudança de voz, motor de TTS ou ritmo;
- necessidade de credencial/conta (Google Cloud, Azure, Hugging Face);
- conflito entre documentação e código;
- risco de apagar `cache/`, `content/`, `output/` ou PDFs;
- dúvida sobre licença/copyright;
- qualquer ação destrutiva (`git reset --hard`, `git clean`, apagar arquivos).

Não invente resposta. Registre a dúvida em `DOCS/06-TASKS.md` se precisar parar.

### 4.2 Autonomia

O usuário pediu **autonomia máxima**. Continue sem pedir confirmação para:

- criar/editar arquivos do projeto;
- instalar dependências no `.venv`;
- rodar extração, testes e builds;
- gerar áudio em `output/`;
- fazer commits locais ao final de cada tarefa.

Só interrompa por: ambiguidade real, credencial ausente, ação destrutiva,
mudança de escopo/voz ou risco de perda de dados.

### 4.3 Commits

- Faça **um commit ao final de cada tarefa** concluída.
- Use mensagens convencionais, por exemplo:
  - `chore(pdf-tts): scaffold, documentação e regras`
  - `feat(pdf-tts): extração e estruturação dos PDFs`
  - `fix(pdf-tts): validação de chunks vazios`
- Antes de commitar, rode `git status` e confira se só há arquivos deste
  projeto. **Não** inclua alterações de outros projetos.
- **Nunca** commite:
  - `input/*.pdf` (direitos autorais);
  - `content/` (texto extraído, direitos autorais);
  - `output/` (áudio, ~1,2 GB);
  - `cache/` (chunks e estado);
  - `dist/` e `build/` (executável e artefatos do PyInstaller);
  - `manifests/AUTO-*.json` (PDFs arbitrários do usuário);
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
  regenere. Exceções manuais devem ser registradas em
  `config/structure.yaml` ou no léxico.

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
  Edge simultâneos. O modo genérico deve sempre avisar quando uma página com
  texto ficar sem áudio e nunca descartar páginas silenciosamente.

### 4.6 Ambiente

- Use **Python 3.11** (`.venv`). O `py` padrão é 3.15 e pode quebrar
  dependências.
- Windows + PowerShell. Use `pathlib` e UTF-8 em todos os arquivos.
- FFmpeg/ffprobe precisam estar no `PATH`; `doctor` valida.
- Não use PyMuPDF (AGPL). A extração é feita com `pdfplumber` (MIT).
- Não adicione dependências pesadas (torch, kokoro, etc.) sem aprovação; o
  fallback local está no backlog.

### 4.7 Documentação viva

Ao final de **toda** tarefa, atualize:

- `DOCS/06-TASKS.md` — status, data, próximo passo;
- `DOCS/08-ERRORS-AND-LESSONS.md` — erros e aprendizados;
- `DOCS/09-DECISIONS.md` — novas decisões;
- `DOCS/11-VERIFICATION.md` — se mudou critério de aceite;
- `manifests/` — se gerou áudio.

Se você parar no meio de uma tarefa, deixe o comando exato para continuar.

## 5. Estrutura do repositório

```text
PDF TTS/
├─ AGENTS.md                 ← este arquivo
├─ README.md                 ← início rápido
├─ pyproject.toml
├─ config/
│  ├─ projects.yaml          ← projetos, páginas das semanas, voz/rate
│  ├─ structure.yaml         ← regras de detecção de títulos/seções
│  └─ pronunciation.pt-BR.yaml
├─ input/                    ← PDFs (local, não versionado)
├─ content/                  ← texto limpo (local, não versionado)
├─ src/pdf_tts/              ← código
├─ tests/
├─ scripts/                  ← setup/doctor/run-all
├─ samples/                  ← amostras sintéticas de voz (versionadas)
├─ manifests/                ← manifests de build (versionados, sem texto)
├─ DOCS/                     ← documentação
├─ output/                   ← áudio (local, não versionado)
└─ cache/                    ← chunks/estado (local, não versionado)
```

## 6. Fluxo resumido

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pdf_tts doctor
python -m pdf_tts extract --project all
python -m pdf_tts segment --project all
python -m pdf_tts samples
python -m pdf_tts build --project mkt120 --lesson S01
python -m pdf_tts all --project all
```

O estado final (2026-11-17) está em `DOCS/06-TASKS.md`: MKT 120 (3:39:26) e
COM 150 (7:50:42) montados e verificados. Áudios em `output/` (não versionados).

Em 2026-11-18 foi adicionado o **modo genérico one-click** (PDF TTS Studio):
`python -m pdf_tts gui`, ou o portátil `dist/PDF TTS/PDF TTS.exe` gerado por
`packaging/build_portable.ps1`. Ele detecta capítulos, aceita PDFs arbitrários
com texto, tem modo “Automático” e “Tudo” e cai para blocos de páginas quando
não encontra estrutura. Detalhes em `DOCS/12-ONE-CLICK-APP.md`.

Detalhes em [`DOCS/05-OPERATIONS.md`](DOCS/05-OPERATIONS.md).

## 7. Definition of Done

Uma tarefa só termina quando:

- o código roda sem erro no Python 3.11;
- os testes relevantes passam;
- a documentação da tarefa foi atualizada;
- os arquivos gerados foram validados (quando aplicável);
- o commit foi feito (ou o motivo de não ter sido registrado).

O projeto inteiro só termina quando `DOCS/11-VERIFICATION.md` estiver cumprido
e os dois livros tiverem MP3, M4B e SRT validados.
