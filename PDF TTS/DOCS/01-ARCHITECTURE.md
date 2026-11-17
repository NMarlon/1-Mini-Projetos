# 01 — Arquitetura

## Visão em uma frase

`PDF → blocos de texto classificados → aulas/seções → chunks falados → MP3 em
cache → montagem com silêncio/loudness → MP3 + M4B + SRT + manifest`.

## Diagrama

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
┌──────────────┐   content/<projeto>/lessons/S01.json … S07.json
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
manifests/<slug>.json
```

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `cli.py` | Comandos `doctor`, `extract`, `segment`, `build`, `assemble`, `samples`, `status`, `all` |
| `config.py` | Carrega `config/projects.yaml`, `structure.yaml`, `pronunciation.pt-BR.yaml`; resolve caminhos |
| `models.py` | Dataclasses `Block`, `Section`, `Lesson`, `Chunk`, `TimelineEntry` |
| `extract.py` | Lê o PDF com `pdfplumber`; agrupa palavras em linhas/blocos; tabelas |
| `classify.py` | Decide `kind` (título, parágrafo, lista, referência, cabeçalho…) e nível |
| `clean.py` | Ligaduras, PUA, cabeçalhos, URLs, hifenização, espaços |
| `segment.py` | Atribui blocos a semanas/seções; gera `structure.json` e `manuscript.md` |
| `normalize.py` | Converte texto para fala (números, abreviações, siglas, `S01`…) |
| `chunking.py` | Divide em sentenças com limites de tamanho e pausas |
| `tts/base.py` | Protocolo `TTSBackend` |
| `tts/edge.py` | Edge TTS com cache por hash, retry, validação e concorrência |
| `tts/fake.py` | Backend de teste (gera WAV sintético, sem rede) |
| `audio.py` | `ffprobe`, silêncio WAV, concatenação, loudnorm, encode |
| `chapters.py` | Metadados de capítulos (ffmetadata) para M4B |
| `srt.py` | Geração de SRT a partir da timeline |
| `manifest.py` | Lê/escreve manifests e calcula hashes |
| `state.py` | SQLite de status dos chunks (resume) |
| `doctor.py` | Checagens de ambiente |

## Modelo de dados

```python
@dataclass
class Block:
    id: str                 # "p0014-b012"
    page: int
    kind: str               # title|heading|paragraph|list_item|table_row|caption|reference|header|footer|...
    text: str               # limpo, para exibição/manuscript
    spoken: str             # normalizado para TTS
    level: int              # 0=corpo, 1=seção, 2=subseção
    section_id: str | None
    bbox: tuple[float, float, float, float]
    size: float
    drop_reason: str | None
```

```python
@dataclass
class Chunk:
    id: str                 # "s01-c0001"
    block_id: str
    section_id: str
    lesson_id: str          # "S01"
    text: str               # exibição
    spoken: str             # fala
    kind: str
    gap_before_ms: int
    cache_key: str
```

## Fluxo de estados

```text
extracted → segmented → synthesized → assembled → verified
```

- `content/<projeto>/structure.json` guarda o resultado do `segment`.
- `cache/<projeto>/state.db` (SQLite) guarda o status de cada chunk:
  `pending`, `running`, `done`, `failed`, `invalid`.
- `manifests/<slug>.json` guarda o resultado final por aula.
- `output/<SLUG>/` guarda os arquivos finais.

## Cache e idempotência

- A chave do chunk é `sha256(engine|voice|rate|volume|pitch|texto_falado)`.
- O MP3 fica em `cache/edge/<voz>/<rate>/<hash>.mp3`.
- O WAV decodificado fica em `cache/wav/<hash>.wav`.
- Se o texto mudar, o hash muda e um novo chunk é gerado; o antigo permanece
  até um `clean-cache` (futuro).
- O build pode ser interrompido e retomado sem perder trabalho.
- `--force` re-sintetiza apenas o escopo indicado (`--lesson`, `--project`).

## Concorrência

- `asyncio.Semaphore(concurrency)` com default 3 (máx. 4).
- Retry exponencial com jitter: 5 tentativas (2, 4, 8, 16, 32 s).
- Após 3 falhas consecutivas, reduz a concorrência pela metade.
- Após 6 falhas consecutivas, aborta com mensagem clara e preserva o cache.
- Cada chunk é validado com `ffprobe` antes de ser marcado como `done`.

## Decisões estruturais

1. **Não usar PyMuPDF** (AGPL). `pdfplumber` (MIT) fornece texto, fonte e posição.
2. **Faixas de página explícitas** em `config/projects.yaml` como fallback
   determinístico; a detecção por fonte é a primeira tentativa.
3. **Texto revisável** (`manuscript.md`) antes de sintetizar.
4. **Cache por chunk**, não por aula; retomada granular.
5. **SRT por frase** baseado na duração real dos chunks, não em word boundaries.
6. **M4B com capítulos** gerado por ffmpeg a partir de um arquivo `ffmetadata`.
7. **Áudio não versionado**; manifests versionados.

## Limitações conhecidas

- Diagramas com texto dentro de imagem não são OCRizados; as legendas são.
- Tabelas complexas podem ser achatadas em linhas; revisar `manuscript.md`.
- O Edge TTS é um serviço não oficial; pode falhar/limitar.
- A qualidade da voz é ótima para pt-BR, mas termos em inglês podem ter sotaque.
- O alinhamento do SRT é por frase, não por palavra.

## Onde continuar

- Tarefas: [`06-TASKS.md`](06-TASKS.md)
- Pipeline de PDF: [`03-PDF-PIPELINE.md`](03-PDF-PIPELINE.md)
- Pipeline de áudio: [`04-AUDIO-PIPELINE.md`](04-AUDIO-PIPELINE.md)
- Operação: [`05-OPERATIONS.md`](05-OPERATIONS.md)
