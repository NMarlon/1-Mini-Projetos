# 12 — Aplicativo one-click (Pathway PDF TTS)

## Objetivo

Permitir que uma pessoa **sem programação** coloque um PDF e gere os áudios com
um botão, sem instalar Python, FFmpeg ou editar YAML.

O app foi feito para os **cursos do Pathway** (MKT 120, COM 150 e outros
materiais com Semanas/S01–S07), mas também converte PDFs comuns que tenham
camada de texto.

## Estado (2026-11-18)

- **Versão 0.3** implementada e testada no código-fonte.
- **Executável portátil Windows** em `dist/Pathway PDF TTS/` e
  `dist/Pathway-PDF-TTS-Windows.zip` (não versionados).
- Teste com o COM 150 real (52 MB, 220 páginas): upload → análise Pathway →
  8 capítulos (Abertura + Semanas 1–7).
- Teste com o MKT 120 real: 8 capítulos (Abertura + Semanas 1–7).
- Modo curado (MKT 120 / COM 150) continua funcionando e verificado.

## Decisões

| Tema | Decisão |
|---|---|
| Nome | **Pathway PDF TTS** (janela, `.exe`, pasta e ZIP) |
| Plataforma | Windows 10/11 |
| Entrega | Pasta portátil com `Pathway PDF TTS.exe` |
| Interface | Navegador local em `127.0.0.1` |
| PDFs | Com camada de texto na v1; OCR no backlog |
| Idioma | pt-BR |
| Perfil padrão | **Automático — Pathway primeiro** |
| Perfis | `auto` (Pathway → índice → genérico → blocos), `pathway`, `generic` |
| Modos de conteúdo | `auto`, `all` (tudo útil) e `raw` (tudo literal) |
| Capítulos | Automático, edição manual ou livro inteiro |
| Fallback | Sem capítulos: blocos de páginas; nunca falha por falta de estrutura |
| Instância | Uma só; abrir o `.exe` de novo foca a instância existente |

## Como usar (pessoa leiga)

1. Extraia `Pathway-PDF-TTS-Windows.zip`.
2. Dê duplo clique em `Pathway PDF TTS.exe`.
3. A interface abre no navegador.
4. Escolha o modo **antes** de enviar:
   - **Automático**: detecta capítulos e limpa bibliografia/boilerplate.
   - **Identificar capítulos**: analisa e deixa você revisar/editar.
   - **Tudo útil**: inclui referências/notas; remove cabeçalho, página e links.
   - **Tudo literal**: narra tudo extraído, inclusive páginas e links.
5. Arraste um PDF (ou clique em “escolha um arquivo”).
6. Confira os capítulos e clique em **Gerar áudios**.
7. Ao final, clique em **Abrir pasta dos áudios**.

**Mantenha a janelinha do Pathway PDF TTS aberta.** Se ela for fechada, o
navegador perde a conexão; o app mostra um aviso e um botão “Tentar novamente”.

Saída:

```text
output/<nome-do-pdf>/
  S01.mp3 … Sxx.mp3
  S01.m4b … Sxx.m4b
  S01.srt … Sxx.srt
  <nome>-completo.mp3/.m4b/.srt
  cover.jpg
  coverage.json
  manifest.json
  README.md
```

## Modos de conteúdo

| Modo | Comportamento |
|---|---|
| **Automático** (padrão) | Remove bibliografia, créditos de fonte, boilerplate e referências pequenas; mantém exercícios, quizzes, tarefas e conteúdo. |
| **Tudo útil** (`all`) | Mantém referências, notas, créditos e texto pequeno; remove apenas cabeçalho, rodapé, número de página, URLs e ícones. |
| **Tudo literal** (`raw`) | Narra tudo o que o extrator encontrou: referências, cabeçalhos repetidos, números de página, rodapés e links. O áudio fica mais repetitivo. |

O relatório `coverage.json` mostra:

- páginas totais, com texto e narradas;
- páginas sem texto (imagem);
- páginas com texto que ficaram sem áudio;
- blocos descartados por motivo;
- capítulos e chunks.

## Perfis de detecção

### `pathway`

Procura primeiro os títulos do material Pathway:

1. `Semana 1`…`Semana 7`;
2. `S01`…`S07`;
3. títulos de aula/unidade;
4. índice/bookmarks do PDF, se existir.

O sumário é ignorado como capítulo: o app compara as ocorrências, descarta as
de fonte menor e prefere a página real de início da semana. Se não encontrar
nada do Pathway, avisa e cai para a detecção genérica.

### `generic`

Para PDFs de outras origens:

1. outline/bookmarks;
2. títulos por tamanho de fonte;
3. palavras `Capítulo`, `Chapter`, `Parte`, `Part`, `Unidade`, `Unit`, `Aula`,
   `Lição`, `Lesson`, `Módulo`, `Module`;
4. fallback em blocos de 10 páginas;
5. se nada funcionar, um único capítulo “Livro completo”.

**Ele identifica PDFs fora do Pathway?** Sim, por essas heurísticas. Não é IA
semântica: se o PDF não tiver títulos reconhecíveis, o app não “entende” o
conteúdo; ele avisa e divide em blocos de páginas.

### `auto` (padrão)

Tenta Pathway primeiro; depois outline, depois genérico, depois blocos. É o
melhor padrão para quem só quer arrastar o PDF.

## Como usar pelo código-fonte

```powershell
# Interface one-click
python -m pdf_tts gui

# Apenas o servidor local (sem abrir a janelinha)
python -m pdf_tts serve --port 8899

# Detectar capítulos (perfil Pathway primeiro)
python -m pdf_tts detect "C:\caminho\livro.pdf"
python -m pdf_tts detect "C:\caminho\livro.pdf" --profile pathway

# Converter qualquer PDF
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode auto
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode all
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode raw

# Escolher capítulos manualmente via JSON
python -m pdf_tts convert "C:\caminho\livro.pdf" --chapters manual --chapter-file capitulos.json
```

Exemplo de `capitulos.json`:

```json
[
  {"title": "Abertura", "start_page": 1, "end_page": 5},
  {"title": "Capítulo 1", "start_page": 6, "end_page": 30}
]
```

Os capítulos manuais precisam começar na página 1, terminar na última página e
ser contínuos.

## Robustez da interface

- Upload em blocos de 1 MB, sem carregar o PDF inteiro na memória.
- Limite de 500 MB por PDF e checagem de espaço em disco.
- Progresso real do envio (`34% — 18 de 52 MB`) e tempo de análise.
- `GET /api/health` com identificador do app.
- Instância única: abrir o `.exe` novamente abre a instância que já está
  rodando, em vez de criar outra porta/aba.
- Aviso na janelinha para não fechá-la; confirmação ao sair.
- FFmpeg/ffprobe rodam com `CREATE_NO_WINDOW`: nenhuma janela de CMD pisca
  durante a conversão.
- Logs em `logs/app.log` (rotativo), `logs/launcher.log` e `logs/crash.log`.
- Se o navegador perder a conexão, mostra “O programa não está respondendo” e
  um botão **Tentar novamente**, em vez de “Failed to fetch”.
- Reanálise com outro perfil sem enviar o PDF de novo.

## Arquitetura

```text
Pathway PDF TTS.exe
  └─ launcher.py (Tkinter + navegador + instância única)
       └─ api.py (FastAPI local 127.0.0.1)
            └─ jobs.py (fila SQLite, um job por vez)
                 └─ generic.convert_pdf
                      ├─ discover.py (Pathway/genérico/blocos)
                      ├─ extract.py (pdfplumber, auto/all/raw)
                      ├─ segment.py/lessons.py
                      ├─ build.py (Edge TTS, cache/resume)
                      ├─ assemble.py (MP3/M4B/SRT)
                      └─ verify.py
```

## Empacotamento

Existem duas embalagens. A principal usa o Python assinado pela Python Software
Foundation e costuma passar pelo Smart App Control do Windows:

```powershell
.\packaging\build_python_portable.ps1
```

Gera:

```text
dist/Pathway PDF TTS/
  Pathway PDF TTS.exe     # cópia assinada do pythonw.exe
  Lib/ DLLs/ tcl/         # runtime Python + dependências
  src/ config/
  ffmpeg.exe ffprobe.exe
  LEIA-ME.txt
  PDFs/
  output/
  logs/
dist/Pathway-PDF-TTS-Windows.zip
```

A embalagem PyInstaller é menor, mas **não é assinada** e pode ser bloqueada
pelo Smart App Control:

```powershell
.\packaging\build_portable.ps1
```

Gera `dist/Pathway PDF TTS (PyInstaller)/` e
`dist/Pathway-PDF-TTS-Windows-PyInstaller.zip`.

- A versão principal é portátil: `pythonw.exe` renomeado como
  `Pathway PDF TTS.exe`, com `Lib`, `DLLs`, `tcl` e `site-packages` locais.
- `sitecustomize.py` adiciona `src/` ao `sys.path`, coloca a pasta no `PATH`
  (para achar ffmpeg) e abre a GUI quando o `.exe` é clicado sem argumentos.
- Na versão PyInstaller, `ffmpeg.exe`/`ffprobe.exe` ficam em `_internal/` e são
  encontrados pelo `find_tool`; `ROOT` é a pasta do `.exe` e `RESOURCE_ROOT` é
  `_internal`.
- `sys.stdout/stderr` são redirecionados para `logs/launcher.log`.

## Testes executados

- `pytest`: **59 testes** (descoberta, perfis, API, montagem, normalização).
- COM 150 real: análise Pathway em ~20 s (com cache de disco), 8 capítulos, sem erro.
- MKT 120 real: 8 capítulos Pathway.
- PDF sintético: modos `auto`/`all` removem cabeçalho/página/URL; `raw` mantém.
- Executável portátil: upload, análise, job completo e arquivos finais.
- MKT 120 e COM 150: verificação técnica continua OK.

## Limitações da v1

- PDFs escaneados/imagem: não há OCR; a interface avisa e lista as páginas.
- PDFs protegidos por senha: não suportados; desbloqueie antes.
- Layouts de duas colunas/tabelas complexas podem ficar fora de ordem.
- “Tudo literal” narra cabeçalhos e números de página; o áudio fica repetitivo.
- O Edge TTS exige internet e envia o texto à Microsoft.
- O `.exe` não é assinado; SmartScreen pode avisar.
- A fila processa um PDF por vez (proteção contra rate limit do Edge).

## Próximos passos (backlog)

- OCR para PDFs escaneados (Tesseract/OCRmyPDF) como componente opcional.
- Botão “Converter todos os PDFs da pasta PDFs”.
- Prévia de 30 s antes do build completo.
- Detecção de idioma + vozes en/es.
- Instalador com atalho e assinatura de código.
- Editor visual de pronúncia.
- Retomada automática de jobs interrompidos ao reabrir.
