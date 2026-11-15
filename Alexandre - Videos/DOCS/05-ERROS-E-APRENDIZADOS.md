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

## [2026-05] avg_logprob NÃO discrimina idioma por segmento (faster-whisper)

- **Erro:** `scripts/compare_passes.py` esperava usar `avg_logprob` p/ escolher o idioma
  real por trecho; veio **idêntico para todos os segmentos** da mesma passada
  (-0.378 zh / -0.804 pt) → inútil p/ decisão segmento a segmento.
- **Achado útil:** mesmo assim, **zh (-0.378) > pt (-0.804)** no geral → áudio real é
  chinês; a passada `pt` estava **traduzindo** frases do chinês (espelho semântico:
  "树都倒了" × "A árvore está caindo").
- **Solução correta p/ áudio misto:** janelas em **modo AUTO** (`language=None`) —
  o modelo escolhe o idioma por janela e transcreve nativamente → `scripts/lang_probe.py`.
  O `lang_map.py` só dá o idioma (prob.), o `lang_probe.py` dá idioma + TEXTO real.
- **Aprendizado:** nunca confiar em passada FORÇADA p/ idiom a que não é o do áudio —
  o Whisper "encaixa" ou traduz. Sempre cruzar com modo auto por janela.

---

## [2026-05] UnicodeEncodeError no console Windows (cp1252) ao imprimir chinês

- **Erro:** `print()` de texto chinês em console cp1252 → `UnicodeEncodeError` no final
  do script (o ARQUIVO já estava gravado em UTF-8 — só o print falhou).
- **Solução:** rodar com `$env:PYTHONIOENCODING="utf-8"` (ou escrever sempre em arquivo
  e ler depois). Scripts novos já gravam resultado em `.txt` UTF-8.
- **Aprendizado:** em Windows, nunca depender do print p/ entregar resultado de
  transcrição — gravar em arquivo UTF-8 e ler com a ferramenta de leitura.

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

## [2026-11] `split` não serve para áudio — usar `asplit`

- **Erro:** `Media type mismatch between 'concat' output (audio) and 'split' input (video)`
  ao montar o filter_complex do render.
- **Causa:** em ffmpeg, `split` é só de vídeo; áudio usa **`asplit`**.
- **Solução:** trocar `[acat]split=2[...]` por `[acat]asplit=2[...]` em
  `scripts/render_short.py`.
- **Aprendizado:** conferir o tipo (v/a) de cada pad antes de ligar; o erro aparece
  na hora, na construção do grafo.

---

## [2026-11] `zoompan` NÃO tem a variável `t`

- **Erro:** `Undefined constant or missing '(' ...` ao avaliar a expressão de zoom
  com `if(lt(t,10.6),...)`.
- **Causa:** `zoompan` expõe `on` (índice do frame de saída), `in`, `x/y/z`, `iw/ih`
  etc., mas **não `t`**.
- **Solução:** usar `(on/<fps>)` como tempo — `if(lt((on/30),10.6),...)`.
- **Aprendizado:** expressões de tempo dependem do filtro; `crop`/`overlay` aceitam
  `t`, `zoompan` usa `on`. Testar sempre com um render curto (`--so-video`) antes
  do render completo.

---

## [2026-11] `-map [rotulo]` precisa bater com o label FINAL do filter_complex

- **Erro:** `Output with label 'a' does not exist in any defined filter graph`.
- **Causa:** o grafo terminava em `[aout]`, mas o `-map` pedia `[a]`.
- **Solução:** mapear exatamente o label produzido (`-map [v] -map [aout]`).
- **Aprendizado:** o ffmpeg valida os labels na abertura do arquivo de saída —
  sempre reler o fim das cadeias antes de rodar.

---

## [2026-11] `legendar.py --start X` devolve tempos RELATIVOS, não absolutos

- **Erro:** `montar_srt.py --seg 702:714.5,...` gerou **0 legendas** (devia gerar 4).
- **Causa:** ao extrair o áudio com `-ss X`, o Whisper zera o tempo — o `.srt` sai
  contando a partir de 0, mas a receita usa tempos do bruto (702, 718…).
- **Solução:** usar no `--seg` os tempos **relativos ao `--start`** da transcrição
  (ex.: `2:14.5,18:24,25:30` para segmentos 702, 718, 725 com `--start 700`).
- **Aprendizado:** anotar sempre o `--start` usado; conferir a 1ª legenda do `.srt`
  antes de montar o timeline do short.

---

## [2026-05] Leitura de duração MP4
---

## [2026-11] Whisper `--sem-vad` ALUCINA por repetição

- **Erro:** transcrição de 8:55–9:55 devolveu a MESMA frase 3× ("Você está atrás
  dessa parede vou atirar nela") — e "chocolate branco" repetido no bruto inteiro.
- **Causa:** sem VAD, o modelo tenta transcrever música/fundo e cai no loop de
  repetição clássico.
- **Solução:** usar VAD (padrão) para varredura; `--sem-vad` só para confirmar fala
  real em trechos curtos e **validar no vídeo** (frames) antes de usar como legenda.
- **Aprendizado:** frase repetida 2–3× seguidas = quase certamente alucinação.
  NUNCA queimar legenda sem bater com a imagem/fala real.

---


- **Erro:** não havia ffprobe no início.
- **Solução:** parser manual do átomo `mvhd` (offset varia conforme versão 0/1) —
  ver script `scripts/mp4_info.py`. Com ffprobe disponível, preferir:
  `ffprobe -v error -show_entries format=duration -of csv=p=0 arquivo.mp4`.

---
