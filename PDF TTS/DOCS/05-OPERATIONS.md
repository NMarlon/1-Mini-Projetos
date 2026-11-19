# 05 — Operações

## Pré-requisitos

- Windows 10/11 + PowerShell.
- Python **3.11** instalado (`py -3.11 --version`).
- FFmpeg e ffprobe no `PATH`; se não estiverem:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  Ou defina `FFMPEG_BIN`/`FFPROBE_BIN` para os executáveis.
- Internet para o Edge TTS.
- ~3 GB livres em disco (áudio + WAV temporário + cache).

## Setup inicial

```powershell
cd "PDF TTS"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pdf_tts doctor
```

> **Nunca use `python` 3.15.** O `py` padrão da máquina aponta para 3.15; sempre
> chame `py -3.11` ou ative o `.venv`.

## Verificação de ambiente

```powershell
python -m pdf_tts doctor
```

O `doctor` checa:

- versão do Python;
- `ffmpeg`/`ffprobe` e codecs `libmp3lame`/`aac`;
- `edge-tts` importável e vozes pt-BR;
- conectividade com o serviço do Edge;
- presença e SHA-256 dos PDFs;
- permissão de escrita em `content/`, `cache/`, `output/`;
- espaço em disco.

Se o `doctor` falhar, **não continue**; corrija e registre em
`08-ERRORS-AND-LESSONS.md`.

## Pipeline completo

```powershell
# 1) extrair e limpar
python -m pdf_tts extract --project all

# 2) revisar o texto
notepad "content\mkt120\manuscript.md"
notepad "content\com150\manuscript.md"

# 3) segmentar em aulas
python -m pdf_tts segment --project all

# 4) amostras de voz (opcional, mas recomendado)
python -m pdf_tts samples

# 5) primeira aula (teste ponta a ponta)
python -m pdf_tts build --project mkt120 --lesson S01

# 6) gerar tudo (pode levar 1–2 h; é retomável)
python -m pdf_tts all --project all --resume
```

## Comandos por etapa

### Extração

```powershell
python -m pdf_tts extract --project mkt120
python -m pdf_tts extract --project all
```

Saídas em `content/<projeto>/`:
`blocks.jsonl`, `skipped.jsonl`, `structure.json`, `manuscript.md`.

### Segmentação

```powershell
python -m pdf_tts segment --project mkt120
```

Saídas: `lessons/S01.json`…`S07.json` e `.txt`.

### Build (síntese + montagem)

```powershell
python -m pdf_tts build --project mkt120 --lesson S01
python -m pdf_tts build --project mkt120
python -m pdf_tts build --project all --resume
python -m pdf_tts build --project all --dry-run
```

Opções:

- `--lesson S01` — apenas uma aula;
- `--force` — re-sintetiza mesmo se o cache existir;
- `--concurrency N` — 1 a 4;
- `--no-assemble` — só sintetiza;
- `--voice` / `--rate` — mudança explícita (registrar no manifest).

### Montagem

```powershell
python -m pdf_tts assemble --project mkt120 --lesson S01
python -m pdf_tts assemble --project mkt120
python -m pdf_tts assemble --project all
```

Gera `output/<SLUG>/S01.mp3`, `.m4b`, `.srt`, `cover.jpg`, `manifest.json` e
`README.md`; sem `--lesson`, gera também o livro completo.

### Verificação

```powershell
python -m pdf_tts verify --project mkt120 --lesson S01
python -m pdf_tts verify --project all
```

Confere MP3/M4B, duração, capítulos, capa, SRT, loudness e silêncios > 5 s.
Use `--no-loudness`/`--no-silence` para acelerar.

### Status

```powershell
python -m pdf_tts status --project all
```

Mostra: chunks totais, done/failed/pending, duração estimada, arquivos
existentes.

### Pipeline completo

```powershell
python -m pdf_tts all --project all
```

Executa `extract` → `segment` → `build` → `assemble` → `verify`. É retomável
(os chunks em cache são reaproveitados).

## App one-click

```powershell
# Interface local (abre o navegador e uma janelinha de controle)
python -m pdf_tts gui

# Só o servidor, para debug
python -m pdf_tts serve --port 8899

# Detectar capítulos de um PDF (Pathway primeiro)
python -m pdf_tts detect "C:\caminho\livro.pdf"
python -m pdf_tts detect "C:\caminho\livro.pdf" --profile pathway
python -m pdf_tts detect "C:\caminho\livro.pdf" --profile generic

# Converter qualquer PDF com texto
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode auto
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode all
python -m pdf_tts convert "C:\caminho\livro.pdf" --mode raw
```

O modo `auto` limpa bibliografia/boilerplate; `all` inclui referências, notas e
créditos, mas remove cabeçalho/página/link; `raw` narra tudo o que foi extraído,
inclusive páginas e links. O perfil `auto` tenta Pathway → índice → genérico →
blocos. Sem capítulos detectados, divide em blocos de 10 páginas e avisa. O
relatório fica em `output/<slug>/coverage.json`.

## Gerar o portátil Windows

Versão principal (Python assinado, funciona com Smart App Control):

```powershell
.\packaging\build_python_portable.ps1
```

Saída: `dist/Pathway PDF TTS/Pathway PDF TTS.exe` +
`dist/Pathway-PDF-TTS-Windows.zip`.

Versão PyInstaller (menor, sem assinatura):

```powershell
.\packaging\build_portable.ps1
```

Saída: `dist/Pathway PDF TTS (PyInstaller)/` +
`dist/Pathway-PDF-TTS-Windows-PyInstaller.zip`. Se o Windows bloquear com
"política de Controle de Aplicativo", use a versão principal.

Guia completo: [`12-ONE-CLICK-APP.md`](12-ONE-CLICK-APP.md).

### App: portas, instância e dados

- O app escuta em `127.0.0.1:8765` e, se ocupado, tenta 8766…8794.
- Se já existe uma instância, abrir o `.exe` de novo apenas abre a interface
  existente; não cria outra fila.
- Dados do app ficam na pasta do `.exe`: `input/uploads/`, `cache/jobs.db`,
  `cache/uploads/`, `output/`, `logs/`.
- Logs: `logs/app.log` (rotativo), `logs/launcher.log`, `logs/crash.log`,
  `logs/launcher-error.log`.
- Para encerrar, use **Sair** na janelinha; fechar no X pede confirmação.
- `GET /api/health` retorna `{"ok": true, "app": "pathway-pdf-tts", "version": "0.3.0"}`.

### App: teste rápido do servidor

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/health"
Invoke-RestMethod "http://127.0.0.1:8765/api/defaults"
```

Se o primeiro comando falhar, o servidor não está rodando ou a porta é outra.

### App: “Failed to fetch”

“Failed to fetch” é o navegador sem conseguir falar com o servidor local, não
um erro de PDF. Verifique, nesta ordem:

1. A janelinha **Pathway PDF TTS está rodando** ainda está aberta?
2. A aba é da instância atual? Se o app foi reaberto em outra porta, use a aba
   nova; abrir o `.exe` de novo reutiliza a instância existente.
3. O log `logs/app.log` mostra o upload/análise?
4. Se a interface mostrou o banner vermelho, clique em **Tentar novamente**.
5. Se o processo morreu, abra o `.exe` novamente; os jobs interrompidos são
   marcados como `interrupted` e podem ser gerados de novo usando o cache.

O upload é feito em blocos de 1 MB, com limite de 500 MB. O COM 150 leva ~20 s
para analisar; a interface mostra o tempo decorrido.

### App: Windows bloqueou o `.exe`

Se aparecer **“Uma política de Controle de Aplicativo bloqueou este arquivo”**,
você está usando a versão PyInstaller em um PC com **Smart App Control** ativo.
Use a versão principal:

```text
dist/Pathway PDF TTS/Pathway PDF TTS.exe
```

Ela é uma cópia assinada do `pythonw.exe` da Python Software Foundation, com
runtime e dependências locais. Não é um `.exe` PyInstaller.

### App: janelas de CMD piscando

Isso não deve mais acontecer. `ffmpeg`/`ffprobe` são executados por
`pdf_tts.audio.run_hidden()` com `CREATE_NO_WINDOW`. Se voltar, procure
`subprocess.run` direto em `src/pdf_tts/` e troque por `run_hidden`.

### App: reportar um bug

O contato fica no card **“Encontrou um bug?”** e no rodapé:
**marlonrviana@gmail.com**.

Ao relatar, inclua:

- o que aconteceu e em qual passo;
- o nome do PDF;
- o ID do job, se houver;
- `logs/app.log` (e `logs/crash.log`, se existir).

O app não envia nada automaticamente; o link apenas abre o cliente de e-mail.

`mailto:` não permite anexar arquivos. Por isso o card tem:

- **Abrir log** — `/api/logs/app.log` no navegador, para copiar/colar;
- **Baixar log** — `/api/logs/app.log?download=1`, para anexar;
- **Copiar log** — copia o conteúdo para a área de transferência.

Os endpoints só servem arquivos da allowlist (`app.log`, `launcher.log`,
`crash.log`, `launcher-error.log`).

### App: reanalisar com outro perfil

Na tela de análise, troque **Perfil de detecção** ou clique em **Reanalisar**.
O app usa `POST /api/reanalyze` com o mesmo upload e não pede o PDF de novo.
Se você estiver no modo de edição manual, ele pede confirmação porque a
detecção será refeita.

### Amostras

```powershell
python -m pdf_tts samples
```

Gera `samples/francisca.mp3`, `antonio.mp3`, `thalita.mp3` e
`pronunciation-test.mp3` com texto sintético.

## Retomada

O build é idempotente:

- o cache de chunks fica em `cache/edge/...`;
- o estado fica em `cache/<projeto>/state.db`;
- um chunk `done` e válido é pulado;
- um chunk `failed`/`invalid` é tentado de novo.

Se a sessão cair, rode o mesmo comando com `--resume`.

## Limpeza

```powershell
# Apagar apenas artefatos de uma aula (cuidado)
Remove-Item "output\MKT-120\S01.*"

# Apagar cache de um projeto (força re-síntese)
Remove-Item -Recurse "cache\mkt120"

# Apagar todo o cache (mantém o áudio final)
Remove-Item -Recurse "cache"
```

> Não apague `content/` sem necessidade: ele é a fonte para re-renderizar sem
> re-extrair os PDFs.

## Clone novo (sem PDFs/texto)

Como o repositório não versiona PDFs nem texto:

1. Clone o repo.
2. Copie os PDFs para `input/` com os nomes exatos.
3. Confira os SHA-256 em `input/README.md`.
4. Crie o `.venv` e instale.
5. Rode `doctor`, `extract`, `segment`.
6. Rode `build --resume`.

Sem os PDFs, só é possível rodar testes e `doctor` (com aviso).

## Tempos estimados

| Etapa | Tempo |
|---|---|
| Extração dos 2 PDFs | 2–10 min |
| Segmentação | segundos |
| Síntese Edge (11 h de áudio) | 1–2 h (3 concorrentes) |
| Montagem/encode | 30–60 min |
| **Total** | **~2–4 h** |

O gargalo é a rede do Edge TTS e a montagem WAV.

## Disco

| Item | Tamanho |
|---|---|
| PDFs | 73 MB |
| Áudio final (MP3+M4B+SRT) | ~1,2 GB |
| Cache de chunks MP3 | ~400 MB |
| WAV temporário por aula | 100–400 MB |
| WAV de todas as aulas (se mantido) | ~5 GB |

O pipeline apaga WAVs temporários por aula após a montagem; se precisar manter,
use `--keep-work`.

## Troubleshooting

### `NoAudioReceived` / WebSocket 1006

- É intermitente. O retry resolve na maioria dos casos.
- Se persistir, reduza `--concurrency 1`.
- Verifique internet/proxy.
- O cache preserva o que já foi gerado.

### Arquivo de áudio vazio

- O CLI do edge-tts pode criar 0 bytes em caso de erro.
- O pipeline valida com `ffprobe` e trata como `invalid`.
- Se acontecer em massa, a voz pode ter saído do catálogo; rode
  `edge-tts --list-voices | Select-String pt-BR`.

### FFmpeg não encontrado

- `where.exe ffmpeg`
- Se estiver no winget, o caminho contém
  `...\Gyan.FFmpeg...\bin\ffmpeg.exe`.
- Defina `FFMPEG_BIN` e `FFPROBE_BIN` no `.env`/ambiente.

### Acentuação quebrada no console

- Use `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`.
- Os scripts PowerShell já configuram isso.
- Arquivos são sempre lidos/escritos com `encoding="utf-8"`.

### `.venv` não ativa

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### PDF não encontrado

- Confira `input/MKT 120.pdf` e `input/Livro texto COM 150-1.pdf`.
- Espaços e acentos fazem parte do nome.
- Rode `doctor` para ver o que falta.

### Texto estranho no áudio

1. Abra `content/<projeto>/manuscript.md` e localize a página.
2. Veja `skipped.jsonl` para saber se um bloco foi removido.
3. Corrija a regra em `src/pdf_tts/clean.py`, `src/pdf_tts/extract.py` ou o
   léxico.
4. Regenere `extract`/`segment` e o áudio da aula.
5. Registre em `08-ERRORS-AND-LESSONS.md`.

## Boas práticas

- Sempre rode `doctor` antes de um build longo.
- Sempre valide `S01` antes de `all`.
- Não edite `content/` à mão; corrija as regras.
- Não commite áudio/texto/PDF.
- Faça commit ao final de cada tarefa.
- Atualize `06-TASKS.md` antes de parar.
