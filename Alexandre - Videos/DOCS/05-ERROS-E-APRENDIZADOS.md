# 05 — Erros e Aprendizados

> Registre AQUI todo erro encontrado e a solução. Próxima IA: leia antes de tentar algo.

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
