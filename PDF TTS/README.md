# PDF TTS — curso em áudio

Pipeline local que transforma os PDFs do curso em audiolivros narrados em
português brasileiro, divididos por semana/aula (`S01`…`S07`), com capítulos,
legendas e um arquivo M4B pronto para players de audiolivro.

## Estado atual

- T00–T07 concluídas.
- `MKT 120`: aula **S01** pronta (MP3/M4B/SRT, 23:05, 11 capítulos); build das
  S02–S07 em andamento.
- `COM 150`: extração/segmentação prontas; síntese pendente.
- 43 testes automatizados passando.

O plano completo, as tarefas e o estado de cada etapa estão em
[`DOCS/06-TASKS.md`](DOCS/06-TASKS.md).

## Fonte dos PDFs

Por questão de direitos autorais, os PDFs **não são versionados**. Coloque-os
manualmente em `input/` com os nomes exatos listados em
[`input/README.md`](input/README.md). O texto extraído também fica fora do Git
(`content/`).

## Requisitos

- Windows 10/11 (o projeto é desenvolvido nesse ambiente)
- Python **3.11** (não use 3.15; há incompatibilidades em dependências)
- FFmpeg no `PATH` (ou defina `FFMPEG_BIN`)
- Internet para o Edge TTS

## Instalação rápida

```powershell
cd "PDF TTS"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pdf_tts doctor
```

## Comandos principais

```powershell
# Verifica ambiente, PDFs, FFmpeg e rede
python -m pdf_tts doctor

# Extrai e limpa o texto (gera content/, que não é versionado)
python -m pdf_tts extract --project all

# Normaliza e divide em aulas S01..S07
python -m pdf_tts segment --project all

# Gera as amostras de voz
python -m pdf_tts samples

# Gera o áudio de uma aula (primeiro teste)
python -m pdf_tts build --project mkt120 --lesson S01

# Monta uma aula/livro a partir dos chunks já sintetizados
python -m pdf_tts assemble --project mkt120 --lesson S01
python -m pdf_tts assemble --project mkt120

# Verifica MP3/M4B/SRT/capítulos/loudness
python -m pdf_tts verify --project mkt120 --lesson S01

# Gera tudo (pode rodar por horas; é retomável)
python -m pdf_tts all --project all
```

Os áudios ficam em `output/<SLUG>/`. O áudio **não é versionado**; os manifests
em `manifests/` registram o que foi gerado, com durações e hashes.

## Documentação

Comece por [`AGENTS.md`](AGENTS.md) e siga a ordem de leitura indicada nele.
Toda a documentação está em [`DOCS/`](DOCS/).

## Licença e uso

Uso pessoal e educacional. O conteúdo dos PDFs pertence aos seus autores. Não
redistribua o texto nem o áudio gerado. O Edge TTS é um serviço não oficial da
Microsoft; consulte os termos antes de usar comercialmente.
