# 12 — Aplicativo one-click (PDF TTS Studio)

## Objetivo

Permitir que uma pessoa **sem programação** coloque um PDF e gere os áudios com
um botão, sem instalar Python, FFmpeg ou editar YAML.

## Estado (2026-11-18)

- **MVP implementado e testado** no código-fonte.
- **Executável portátil Windows** gerado em `dist/PDF TTS/` e
  `dist/PDF-TTS-Windows.zip` (não versionados).
- Teste ponta a ponta com PDF sintético: análise → 4 capítulos → síntese → MP3
  por capítulo, M4B, SRT e livro completo.
- Modo curado (MKT 120 / COM 150) continua funcionando e verificado.

## Decisões

| Tema | Decisão |
|---|---|
| Plataforma | Windows 10/11 |
| Entrega | Pasta portátil com `PDF TTS.exe` |
| Interface | Navegador local em `127.0.0.1` |
| PDFs | Com camada de texto na v1; OCR no backlog |
| Idioma | pt-BR |
| Modos | Curado (MKT/COM) + genérico automático |
| Conteúdo padrão | **Automático** (limpa bibliografia/boilerplate) |
| Opção “Tudo” | Narra referências, notas e créditos; remove só lixo de layout |
| Capítulos | Automático, manual ou livro inteiro |
| Fallback | Sem capítulos: blocos de páginas; nunca falha por falta de estrutura |

## Como usar (pessoa leiga)

1. Extraia `PDF-TTS-Windows.zip`.
2. Dê duplo clique em `PDF TTS.exe`.
3. A interface abre no navegador.
4. Arraste um PDF (ou clique em “escolha um arquivo”).
5. Confira os capítulos. Se quiser, escolha:
   - **Conteúdo**: Automático ou Tudo.
   - **Capítulos**: Detectar automaticamente, Editar capítulos ou Livro inteiro.
6. Escolha a voz e o ritmo.
7. Clique em **Gerar áudios**.
8. Ao final, clique em **Abrir pasta dos áudios**.

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

## Como usar pelo código-fonte

```powershell
# Interface one-click
python -m pdf_tts gui

# Apenas o servidor local (sem abrir a janelinha)
python -m pdf_tts serve --port 8899

# Detectar capítulos de um PDF
python -m pdf_tts detect "C:\caminho\livro.pdf"

# Converter direto pela linha de comando
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode auto

# Forçar narração de tudo (referências incluídas)
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode all

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

## Detecção automática

Ordem:

1. **Outline/bookmarks** do PDF.
2. **Títulos por fonte**: corpo = tamanho mais comum; título = ≥ 1,15× o corpo.
3. **Padrões**: `Capítulo`, `Chapter`, `Parte`, `Part`, `Unidade`, `Unit`,
   `Aula`, `Semana`, `Lição`, `Lesson`, `Módulo`, `Module`.
4. **Fallback**: blocos de 10 páginas (configurável).
5. **Nenhum**: um único capítulo “Livro completo”.

Cuidados implementados:

- Páginas iniciais com muitos títulos (sumário) são ignoradas como capítulos.
- Títulos `S01`, `S02` são tratados como subseção, não como capítulo, quando há
  títulos fortes (`Semana`, `Capítulo`…).
- Capítulos são contínuos, sem lacunas ou sobreposição.
- Primeira página de capa/sumário vira “Abertura” (e pode ser removida no modo
  manual).
- Título genérico de metadados (`(anonymous)`, hash) cai para o nome do arquivo.

## Modos de conteúdo

| Modo | Comportamento |
|---|---|
| **Automático** (padrão) | Remove bibliografia, créditos de fonte, boilerplate e referências pequenas; mantém exercícios, quizzes, tarefas e conteúdo. |
| **Tudo (fiel)** | Mantém referências, notas, créditos e texto pequeno; remove apenas cabeçalhos/rodapés, números de página, URLs e ícones. |

O relatório `coverage.json` mostra:

- páginas totais, com texto e narradas;
- páginas sem texto (imagem);
- páginas com texto que ficaram sem áudio;
- blocos descartados por motivo;
- capítulos e chunks.

Se uma página com texto ficar sem áudio no modo automático, a interface avisa;
o usuário pode trocar para “Tudo” ou editar os capítulos.

## Arquitetura

```text
PDF TTS.exe
  └─ launcher.py (Tkinter + navegador)
       └─ api.py (FastAPI local 127.0.0.1)
            └─ jobs.py (fila SQLite, um job por vez)
                 └─ generic.convert_pdf
                      ├─ discover.py (capítulos/texto)
                      ├─ extract.py (pdfplumber, content_mode)
                      ├─ segment.py/lessons.py
                      ├─ build.py (Edge TTS, cache/resume)
                      ├─ assemble.py (MP3/M4B/SRT)
                      └─ verify.py
```

Arquivos novos:

- `discover.py` — detecção genérica;
- `generic.py` — projeto dinâmico + pipeline;
- `jobs.py` — fila persistente;
- `api.py` — API local;
- `web/` — interface;
- `launcher.py` — servidor + janela;
- `packaging/` — spec PyInstaller, entrypoint, LEIAME, build.

## Empacotamento

```powershell
.\packaging\build_portable.ps1
```

Gera:

```text
dist/PDF TTS/
  PDF TTS.exe
  _internal/            # Python, libs, config, web
  ffmpeg.exe
  ffprobe.exe
  LEIA-ME.txt
  PDFs/
  output/
dist/PDF-TTS-Windows.zip
```

- PyInstaller `--onedir` (sem `--onefile`).
- `ffmpeg.exe`/`ffprobe.exe` são copiados para junto do `.exe`.
- `config/` e `web/` vão para `_internal/`.
- `ROOT` em modo congelado é a pasta do `.exe`; `RESOURCE_ROOT` é `_internal`.
- `sys.stdout/stderr` são redirecionados para `logs/launcher.log` quando não há
  console.

## Testes executados

- `pytest`: **52 testes** (inclui descoberta, API, montagem, normalização).
- PDF sintético de 4 páginas: detectou 4 capítulos, gerou 15 arquivos.
- Executável portátil: `/api/health`, `/api/defaults`, upload, job completo e
  arquivos finais validados.
- MKT 120 e COM 150: verificação técnica continua OK.

## Limitações da v1

- PDFs escaneados/imagem: não há OCR; a interface avisa e lista as páginas.
- PDFs protegidos por senha: não suportados; desbloqueie antes.
- Layouts de duas colunas/tabelas complexas podem ficar fora de ordem; o modo
  manual de capítulos não corrige ordem interna, só divisão.
- Não há edição visual do texto; para pronúncia, use o léxico.
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
