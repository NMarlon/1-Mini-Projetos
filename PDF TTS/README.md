# Pathway PDF TTS — curso em áudio

Pipeline local que transforma os PDFs do Pathway em audiolivros narrados em
português brasileiro, divididos por semana/aula (`S01`…`S07`), com capítulos,
legendas e um arquivo M4B pronto para players de audiolivro. Também converte
outros PDFs com camada de texto.

## Estado atual

**T00–T16 concluídas.** Os dois livros estão montados e verificados; o app
Pathway PDF TTS está implementado e empacotado.

| Livro | Aulas | Duração | Capítulos | Cues SRT | Tamanho |
|---|---|---|---|---|---|
| `MKT 120` | S01–S07 | 03:39:26 | 68 | 1.473 | ~425 MB |
| `COM 150` | S01–S07 | 07:50:42 | 92 | 3.457 | ~910 MB |
| **Total** | **14** | **11:30:08** | **160** | **4.930** | **1,335 GB** |

- 59 testes automatizados passando.
- `verify --project all`: MP3/M4B/SRT/capítulos/capa/loudness **OK**; nenhum
  silêncio > 5 s.
- Áudios em `output/MKT-120/` e `output/COM-150/` (não versionados).
- Comece ouvindo `samples/francisca.mp3` e `output/MKT-120/S01.m4b`.

O plano completo, as tarefas e o estado de cada etapa estão em
[`DOCS/06-TASKS.md`](DOCS/06-TASKS.md).

## App one-click (Pathway PDF TTS)

Além da CLI, existe um app local:

```powershell
python -m pdf_tts gui
```

Ele abre uma interface no navegador onde qualquer pessoa pode arrastar um PDF,
escolher o modo, revisar os capítulos e clicar em **Gerar áudios**.

O portátil Windows principal usa o Python assinado da Python Software
Foundation, para funcionar também com o Smart App Control ativo:

```powershell
.\packaging\build_python_portable.ps1
```

Resultado: `dist/Pathway PDF TTS/Pathway PDF TTS.exe` e
`dist/Pathway-PDF-TTS-Windows.zip` (não versionados). O app não exige
Python/FFmpeg instalados.

Há também uma embalagem PyInstaller, menor mas sem assinatura:

```powershell
.\packaging\build_portable.ps1
```

Resultado: `dist/Pathway PDF TTS (PyInstaller)/` e
`dist/Pathway-PDF-TTS-Windows-PyInstaller.zip`. Se o Windows bloquear por
“política de Controle de Aplicativo”, use a versão principal.

**Feito para o Pathway:**
- Perfil padrão **Automático — Pathway primeiro**: procura Semanas 1–7 e
  S01–S07. Se não achar, tenta índice, títulos genéricos e blocos de páginas.
- Também aceita PDFs de outras origens no perfil **Genérico**.

**Modos do app:**
- **Automático** (padrão): limpa bibliografia/boilerplate.
- **Identificar capítulos**: analisa e deixa revisar/editar antes de gerar.
- **Tudo útil**: narra referências, notas e créditos; remove cabeçalho, página e links.
- **Tudo literal**: narra tudo extraído, inclusive páginas e links.
- Sem estrutura detectada: avisa e divide em blocos de 10 páginas; **não perde
  o texto**.
- Páginas só de imagem são listadas; OCR fica para a próxima versão.

Detalhes completos em [`DOCS/12-ONE-CLICK-APP.md`](DOCS/12-ONE-CLICK-APP.md).

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

Os áudios ficam em `output/<SLUG>/`:

- `S01.mp3`…`S07.mp3` — uma aula por arquivo;
- `S01.m4b`…`S07.m4b` — capítulos por seção, capa embutida;
- `S01.srt`…`S07.srt` — legendas;
- `<SLUG>-completo.mp3/.m4b/.srt` — livro inteiro;
- `cover.jpg`, `manifest.json`, `README.md`.

O áudio **não é versionado**; os manifests em `manifests/` registram o que foi
gerado, com durações e hashes.

## Documentação

Comece por [`AGENTS.md`](AGENTS.md) e siga a ordem de leitura indicada nele.
Toda a documentação está em [`DOCS/`](DOCS/).

## Licença e uso

Uso pessoal e educacional. O conteúdo dos PDFs pertence aos seus autores. Não
redistribua o texto nem o áudio gerado. O Edge TTS é um serviço não oficial da
Microsoft; consulte os termos antes de usar comercialmente.
