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

## Receitas da interface

As quatro opções visíveis antes do upload são combinações de conteúdo/capítulos:

| Receita | `content_mode` | `chapter_mode` | Uso |
|---|---|---|---|
| **Automático** | `auto` | `auto` | Uso diário; limpa bibliografia/boilerplate. |
| **Identificar capítulos** | `auto` | `manual` | Revisar/editar capítulos antes de gerar. |
| **Tudo útil** | `all` | `auto` | Referências/notas/créditos, sem lixo de layout. |
| **Tudo literal** | `raw` | `auto` | “Tudo mesmo”; áudio repetitivo. |

O usuário ainda pode mudar o perfil de detecção e, em “Avançado”, escolher
capítulos automáticos, edição manual ou livro inteiro.

## API local

| Método | Rota | Uso |
|---|---|---|
| GET | `/api/health` | `{"ok": true, "app": "pathway-pdf-tts", "version": "0.3.0"}` |
| GET | `/api/defaults` | Voz, ritmo, tamanho de bloco e perfil padrão. |
| POST | `/api/analyze` | Multipart: `file`, `chapter_mode`, `chapter_size`, `profile`; salva upload e devolve `upload_id` + `discovery`. |
| POST | `/api/reanalyze` | JSON `upload_id`, `profile`; refaz a detecção sem novo upload. |
| POST | `/api/jobs` | JSON `upload_id`, `chapter_mode`, `chapters`, `content_mode`, `profile`, `voice`, `rate`. |
| GET | `/api/jobs/{id}` | Status, progresso, `coverage`, arquivos e pasta. |
| GET | `/api/jobs` | Últimos jobs (máx. 50). |
| POST | `/api/open-folder` | Abre a pasta de saída validada no Windows. |
| GET | `/api/voices` | Vozes pt-BR do Edge TTS. |

Upload: blocos de 1 MB, limite de 500 MB, exige cabeçalho `%PDF-` e checa
espaço livre. A análise roda em threadpool; o job roda em uma thread de fila
SQLite, um por vez.

## Arquivos e dados do app

```text
<portátil>/
├─ Pathway PDF TTS.exe     # principal: pythonw.exe assinado pela PSF
├─ Lib/ DLLs/ tcl/         # runtime Python local
├─ src/                    # código pdf_tts
├─ config/                 # projects.yaml, structure.yaml, pronunciation
├─ ffmpeg.exe ffprobe.exe
├─ input/uploads/          # PDFs enviados (local)
├─ cache/jobs.db           # fila SQLite
├─ cache/uploads/          # análise JSON por upload
├─ output/<slug>/          # MP3/M4B/SRT/coverage/manifest
├─ logs/app.log            # upload, análise, jobs
├─ logs/launcher.log       # stdout/stderr do app sem console
└─ logs/crash.log          # faulthandler
```

No código-fonte, os mesmos dados ficam na raiz do projeto (`ROOT`), e
`config/`/`web/` são recursos (`RESOURCE_ROOT`). No PyInstaller congelado,
`ROOT` é a pasta do `.exe` e `RESOURCE_ROOT` é `_internal`.

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
- Tamanhos medidos em 2026-11-18: pasta principal ~428 MB / ZIP ~150 MB;
  PyInstaller ~277 MB / ZIP ~130 MB.

Nada disso é versionado: `dist/` e `build/` estão no `.gitignore`. O código e
os scripts de build são versionados; o executável é regenerado.

## Testes executados

- `pytest`: **59 testes** (descoberta, perfis, API, montagem, normalização).
- `ruff check src tests packaging`: limpo.

| Teste | Resultado |
|---|---|
| MKT 120, perfil Pathway | 8 capítulos (Abertura + Semanas 1–7) |
| COM 150, perfil Pathway | 8 capítulos (Abertura + Semanas 1–7), ~20 s |
| COM 150, perfil Genérico | 8 capítulos por título |
| PDF sintético, `auto`/`all` | remove cabeçalho, número de página e URL |
| PDF sintético, `raw` | mantém cabeçalho, número de página e URL |
| Job sintético `raw` | 15 arquivos (MP3/M4B/SRT + completo + capa + JSON) |
| `.exe` principal | health `pathway-pdf-tts` v0.3.0 |
| ZIP principal extraído | abriu e respondeu ao health |
| `run_hidden` (10 chamadas ffmpeg) | nenhum `cmd.exe`/`conhost.exe` novo |
| PyInstaller | build OK, mas bloqueado nesta máquina pelo Smart App Control |

## Suporte e relato de bugs

O app mostra o contato em dois lugares:

- card **“Encontrou um bug?”**, no fim da página;
- rodapé de todas as telas.

E-mail: **marlonrviana@gmail.com**

O link usa `mailto:` com assunto preenchido. Quando um job falha, o app mostra
um link **“envie um e-mail”** que já inclui:

- ID do job;
- etapa;
- mensagem de erro.

Peça ao usuário que anexe `logs/app.log` e informe o nome do PDF. Não há
telemetria automática; nada é enviado sem o usuário clicar.

## Diagnóstico rápido

### “Failed to fetch”

1. A janelinha do app está aberta?
2. A aba é da instância/porta atual?
3. `logs/app.log` registra o upload?
4. Clique em **Tentar novamente** no banner de conexão.
5. Se o processo morreu, abra o `.exe`; jobs ficam `interrupted` e o cache é
   reaproveitado.

### O `.exe` foi bloqueado pelo Windows

Use a versão principal (`dist/Pathway PDF TTS/`), que usa o `pythonw.exe`
assinado pela PSF. A versão PyInstaller não tem assinatura e pode ser bloqueada
pelo Smart App Control.

### Janelas de CMD piscando

Não deve ocorrer. Se voltar, procure `subprocess.run` direto em `src/pdf_tts/`
e troque por `pdf_tts.audio.run_hidden`.

### Análise demorada

O COM 150 leva ~20 s. A interface mostra o tempo decorrido; não feche a
janelinha nem recarregue a aba. Se o PDF tiver mais de 500 MB, divida antes.

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
