# 01 — Arquitetura

## Visão em uma frase

O projeto tem dois caminhos que compartilham o mesmo núcleo:

```text
PDF → blocos classificados → aulas/seções → chunks falados → cache MP3 →
WAV concatenado → loudness → MP3 + M4B + SRT + manifest
```

- **Curado:** páginas das semanas fixadas em `config/projects.yaml` (MKT 120 e
  COM 150).
- **App Pathway PDF TTS:** detecção automática de capítulos, interface no
  navegador e fila local para qualquer PDF com texto.

## Diagrama do núcleo

```text
input/*.pdf
   │
   ▼
┌──────────────┐   content/<projeto>/blocks.jsonl
│  extract.py  │──▶ manuscript.md, structure.json, skipped.jsonl
│  (pdfplumber)│
└──────────────┘
   │
   ▼
┌──────────────┐   content/<projeto>/lessons/S01.json … Sxx.json
│  segment.py  │──▶ chunks com pausas e metadados de seção
│  + chunking  │
└──────────────┘
   │
   ▼
┌──────────────┐   cache/edge/<voz>/<rate>/<hash>.mp3
│  tts/edge.py │──▶ cache/wav/<hash>.wav
│  cache/resume│
└──────────────┘
   │
   ▼
┌──────────────┐   output/<SLUG>/S01.wav (temporário)
│  assemble.py │──▶ S01.mp3, S01.m4b, S01.srt
│  ffmpeg      │──▶ <SLUG>-completo.mp3/.m4b
└──────────────┘
   │
   ▼
manifests/<slug>.json + coverage.json + README.md
```

## Diagrama do app

```text
Pathway PDF TTS.exe
  └─ launcher.py (Tkinter + navegador + instância única + logs)
       └─ api.py (FastAPI em 127.0.0.1:8765+)
            └─ jobs.py (fila SQLite; um job por vez)
                 └─ generic.convert_pdf
                      ├─ discover.py (Pathway/genérico/blocos)
                      ├─ extract.py (content_mode auto/all/raw)
                      ├─ segment.py + lessons.py
                      ├─ build.py (Edge TTS, cache/resume)
                      ├─ assemble.py (MP3/M4B/SRT)
                      └─ verify.py
```

A interface `web/` conversa com a API por HTTP local. O `.exe` portátil
principal é o `pythonw.exe` assinado da PSF renomeado; `sitecustomize.py`
adiciona `src/` ao `sys.path`, ajusta o `PATH` e abre a GUI. A variante
PyInstaller usa o mesmo código.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `cli.py` | Comandos `doctor`, `extract`, `segment`, `build`, `assemble`, `samples`, `status`, `all`, `detect`, `convert`, `gui`, `serve` |
| `config.py` | Carrega `config/*.yaml`; separa `ROOT` (dados) de `RESOURCE_ROOT` (recursos no app congelado) |
| `models.py` | Dataclasses `Block`, `Section`, `Week`, `Lesson`, `Chunk` |
| `extract.py` | Lê o PDF com `pdfplumber`; agrupa linhas/blocos; tabelas; classificação e `content_mode` |
| `clean.py` | Ligaduras, PUA, URLs, cabeçalhos, hifenização, detecção de referência |
| `segment.py` | Atribui blocos a semanas/seções; gera `blocks.jsonl`, `structure.json`, `manuscript.md` |
| `normalize.py` | Converte texto para fala (números, datas, moedas, siglas, `S01`…) |
| `chunking.py` | Divide em sentenças com limites e pausas |
| `lessons.py` | Monta chunks por seção/aula e grava `lessons/Sxx.json` |
| `tts/base.py` | Protocolo `TTSBackend` |
| `tts/edge.py` | Edge TTS com cache por hash, retry, validação e concorrência |
| `build.py` | Orquestra síntese, cache, status e amostras; expõe `run_build_project` com callback de progresso |
| `state.py` | SQLite de status dos chunks (resume) |
| `assemble.py` | WAV, loudnorm, MP3/M4B, capítulos, capa, SRT, manifest; `run_assemble_project` com progresso |
| `verify.py` | Verifica MP3/M4B/SRT/capítulos/loudness/silêncios; `run_verify_project` |
| `audio.py` | Caminhos de ffmpeg/ffprobe, validação, `run_hidden()` sem console |
| `doctor.py` | Checagens de ambiente |
| `discover.py` | Detecção de capítulos Pathway/genérico, contagem de texto e fallback |
| `generic.py` | Projeto dinâmico, `ConvertOptions`, pipeline genérico, `coverage.json`, CLI `detect`/`convert` |
| `api.py` | API FastAPI local, upload em blocos, análise, reanálise, fila e saúde |
| `jobs.py` | Fila SQLite persistente; um job por vez; progresso e erros |
| `launcher.py` | Servidor uvicorn em thread, Tkinter, instância única, logs e abertura do navegador |
| `web/` | `index.html`, `app.js`, `style.css` — interface do app |
| `packaging/` | `build_python_portable.ps1`, `build_portable.ps1`, spec PyInstaller, entrypoint e LEIA-MEs |
| `scripts/` | Setup, doctor, run-all e gerador de PDF sintético |

## Modelo de dados atual

```python
@dataclass
class Block:
    id: str
    project: str
    page: int
    kind: str                  # paragraph|heading|section_heading|week_title|
                               # table|caption|option|list_item|reference
    text: str
    size: float
    fontname: str
    top: float
    x0: float
    level: int
    original_kind: str | None
    original_level: int | None
    section_id: str | None
    drop_reason: str | None    # None = entra no áudio
```

```python
@dataclass
class Chunk:
    id: str
    lesson_id: str             # "S01"
    section_id: str
    block_id: str
    kind: str
    text: str                  # exibição
    spoken: str                # fala normalizada
    gap_before_ms: int
    cache_key: str
```

## Fluxo de estados

```text
extracted → segmented → synthesized → assembled → verified
```

- `content/<projeto>/structure.json` guarda o resultado do `segment`.
- `cache/<projeto>/state.db` guarda o status de cada chunk:
  `pending`, `running`, `done`, `failed`, `invalid`.
- `cache/jobs.db` guarda os jobs do app: `queued`, `running`, `done`, `error`,
  `interrupted`.
- `manifests/<slug>.json` guarda o resultado final por aula.
- `output/<SLUG>/` guarda os arquivos finais.
- `output/<SLUG>/coverage.json` mostra páginas narradas/sem áudio/só imagem.

## Cache e idempotência

- Chave do chunk: `sha256(engine|voice|rate|volume|pitch|texto_falado)`.
- MP3 em `cache/edge/<voz>/<rate>/<hash>.mp3`; WAV em `cache/wav/<hash>.wav`.
- Se o texto mudar, o hash muda; o chunk antigo fica órfão até uma limpeza.
- O build pode ser interrompido e retomado sem perder trabalho.
- `--force` re-sintetiza apenas o escopo indicado.
- O app reusa o mesmo cache; fechar e reabrir não perde chunks concluídos.

## Concorrência

- `asyncio.Semaphore(concurrency)`, default 3 (máx. 4).
- Retry exponencial com jitter: 5 tentativas (2, 4, 8, 16, 32 s).
- Após 3 falhas consecutivas, reduz a concorrência pela metade.
- Após 6 falhas consecutivas, aborta e preserva o cache.
- Cada chunk é validado com `ffprobe` antes de `done`.
- A fila do app processa **um PDF por vez**; não rode dois builds Edge.

## Decisões estruturais

1. **Não usar PyMuPDF** (AGPL). `pdfplumber` (MIT) fornece texto, fonte e posição.
2. **Faixas de página explícitas** para o modo curado; detecção automática para
   o modo genérico.
3. **Texto revisável** (`manuscript.md`) antes de sintetizar.
4. **Cache por chunk**, não por aula; retomada granular.
5. **SRT por frase** baseado na duração real dos chunks.
6. **M4B com capítulos** gerado por ffmpeg a partir de `ffmetadata`.
7. **Áudio não versionado**; manifests versionados.
8. **Subprocessos sem console** (`run_hidden`) em qualquer app GUI.
9. **App com uma fila SQLite** e um job por vez.
10. **Empacotamento principal com Python assinado** para passar pelo Smart App
    Control; PyInstaller é alternativa.

## Limitações conhecidas

- Diagramas com texto dentro de imagem não são OCRizados; as legendas são.
- Tabelas complexas podem ser achatadas; revisar `manuscript.md`.
- O Edge TTS é um serviço não oficial; pode falhar/limitar.
- A qualidade da voz é ótima para pt-BR, mas termos em inglês podem ter sotaque.
- O alinhamento do SRT é por frase, não por palavra.
- PDFs escaneados sem camada de texto não são suportados na v1.
- A versão PyInstaller pode ser bloqueada pelo Smart App Control; a principal
  usa o Python assinado da PSF.

## Onde continuar

- Tarefas e estado: [`06-TASKS.md`](06-TASKS.md)
- Pipeline de PDF: [`03-PDF-PIPELINE.md`](03-PDF-PIPELINE.md)
- Pipeline de áudio: [`04-AUDIO-PIPELINE.md`](04-AUDIO-PIPELINE.md)
- Operação e troubleshooting: [`05-OPERATIONS.md`](05-OPERATIONS.md)
- App one-click: [`12-ONE-CLICK-APP.md`](12-ONE-CLICK-APP.md)
