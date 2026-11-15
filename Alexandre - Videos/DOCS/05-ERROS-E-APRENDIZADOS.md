# 05 — Erros e Aprendizados

> Registre AQUI todo erro encontrado e a solução. Próxima IA: leia antes de tentar algo.

---

## [2026-05] Whisper `small` ALUCINA em vídeo com áudio misto/música

- **Erro:** transcrição com modelo `small` gerou frases sem sentido
  (ex.: "摩托们台风最可怕了" para áudio que não corresponde) — clássica alucinação
  do Whisper em trechos com música/ruído ou idioma trocado no meio.
- **Diagnóstico:** o vídeo tem áudio **misto pt-br + chinês**; o Whisper detecta
  apenas UM idioma por chamada (`zh` com prob 0.88–0.89) e força tudo no idioma detectado.
- **Solução:** (1) usar modelo **`medium`** (muito mais robusto); (2) rodar **duas passadas**
  com `language='pt'` e `language='zh'` e mesclar por timestamps; (3) conferir com frames
  do vídeo (contexto visual) antes de traduzir.
- **Aprendizado:** NUNCA confiar cegamente na 1ª transcrição — validar com o vídeo e
  comparar modelos. Ver `04-TAREFAS.md`.

---

## [2026-05] Download do modelo Whisper TRAVOU a 976 MB (0 bytes/30s)

- **Erro:** `hf_hub_download` parou de receber dados (976,6 MB de ~1500 MB, +0 em 30s,
  CPU ociosa), mas o processo ficava "vivo" e não morria sozinho → 30+ min parado.
- **Diagnóstico:** medir tamanho do `.incomplete` em duas janelas + CPU do processo;
  testar conectividade `https://huggingface.co` (HTTP 200 = rede ok = download morto).
- **Solução:** matar o processo e rodar `scripts/download_model.py` — loop de até 30
  tentativas que **retoma** o `.incomplete` (nada do que já baixou se perde) e registra
  progresso por tentativa. Completou na 1ª tentativa do loop.
- **Aprendizado:** download longo do HF pode morrer sem erro; SEMPRE usar retomada com
  retry. `HF_HUB_ETAG_TIMEOUT`/`HF_HUB_DOWNLOAD_TIMEOUT` evitam conexões mortas.

---

## [2026-05] faster-whisper × lib `srt`: TypeError float vs timedelta

- **Erro:** `TypeError: '<' not supported between instances of 'float' and 'datetime.timedelta'`
  ao salvar o `.srt` — `srt.Subtitle(start=..., end=...)` exige `datetime.timedelta`,
  mas `faster-whisper` retorna **float (segundos)**.
- **Solução:** converter com `timedelta(seconds=float)` — helper `td()` em `scripts/transcribe.py`.
- **Aprendizado:** conferir tipos das libs de terceiros; o Whisper rodou ok antes do erro
  (idioma detectado: **zh, prob 0.89** — o vídeo é chinês).

---

## [2026-05] FFmpeg instalado via winget mas `ffmpeg` não roda no shell atual

- **Erro:** `Get-Command ffmpeg` → NAO, logo após `winget install Gyan.FFmpeg`.
- **Causa:** winget altera o PATH, mas shells já abertos não herdam a mudança
  ("Path environment variable modified; restart your shell").
- **Solução:** usar caminho completo do binário:
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe`
  (evitar a pasta `Gyan.FFmpeg.Essentials_*` — há DUAS instalações; usar a **full_build 9.0.2**).
- **Aprendizado:** em scripts, resolver o caminho do ffmpeg dinamicamente (procurar no
  WinGet Packages) em vez de assumir PATH.

---

## [2026-05] Python `round(x/1MB,1)` → SyntaxError

- **Erro:** `1MB` não é literal válido em Python (`invalid decimal literal`).
- **Solução:** usar `1024*1024`.
- **Aprendizado:** nunca literais com sufixo de unidade em Python.

---

## [2026-05] Leitura de duração MP4

- **Erro:** não havia ffprobe no início.
- **Solução:** parser manual do átomo `mvhd` (offset varia conforme versão 0/1) —
  ver script `scripts/mp4_info.py`. Com ffprobe disponível, preferir:
  `ffprobe -v error -show_entries format=duration -of csv=p=0 arquivo.mp4`.

---
