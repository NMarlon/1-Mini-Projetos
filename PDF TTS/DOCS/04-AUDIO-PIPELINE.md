# 04 — Pipeline de áudio

## Visão

Chunks de texto → MP3 em cache → WAV concatenado → loudness → MP3/M4B/SRT →
manifest.

## Configuração padrão

| Item | Valor |
|---|---|
| Motor | `edge` |
| Voz | `pt-BR-FranciscaNeural` |
| Rate | `-5%` |
| Volume | `+0%` |
| Pitch | `+0Hz` |
| Sample rate | 24.000 Hz |
| Canais | 1 (mono) |
| MP3 | 64 kbps |
| AAC/M4B | 64 kbps |
| Loudness | -16 LUFS, true peak -1,5 dB, LRA 11 |
| Concorrência | 3 (máx. 4) |
| Pausa entre parágrafos | 350 ms |
| Pausa antes de título | 700 ms |
| Pausa antes de seção | 1.200 ms |
| Pausa antes de semana/livro | 1.800 / 2.000 ms |

## Chunking

1. Cada bloco é dividido em sentenças.
2. Sentenças muito curtas (< 80 chars) são agrupadas com a próxima.
3. Sentenças muito longas (> 1.200 chars) são divididas em `;`, `:` ou `,`
   próximos do meio, ou em limite de palavra.
4. Títulos são chunks próprios; não são agrupados.
5. Não se adiciona silêncio entre sentenças do mesmo parágrafo; a pontuação do
   TTS já cria pausas naturais.
6. Silêncio é inserido entre blocos, conforme a tabela acima.

## Cache

```text
cache/
├─ edge/
│  └─ pt-BR-FranciscaNeural/
│     └─ -5%/
│        ├─ <hash>.mp3
│        └─ <hash>.json     # duração, texto? não; só metadados
├─ wav/
│  └─ <hash>.wav
├─ silence/
│  └─ 350ms_24000_1.wav
└─ <projeto>/
   └─ state.db
```

- Hash: `sha256(engine|voice|rate|volume|pitch|texto_falado)`.
- O MP3 é escrito em `.part` e renomeado no final (atômico).
- Se o MP3 existir e for válido, não há chamada de rede.
- Se o texto mudar, o hash muda; o chunk antigo fica órfão até uma limpeza.
- O WAV é derivado do MP3 (`ffmpeg -i chunk.mp3 -ar 24000 -ac 1 chunk.wav`).

## Validação de chunk

Antes de marcar como `done`:

1. Arquivo existe e tem > 500 bytes.
2. `ffprobe` retorna duração > 0,2 s.
3. Duração não é absurda para o texto (ex.: > 3× o esperado).
4. Se falhar, apagar o arquivo, marcar `invalid` e tentar de novo.

> **Aprendizado:** o CLI do `edge-tts` pode criar um arquivo de 0 bytes quando a
> voz é inválida e ainda assim sair com código 0. Nunca confie apenas no
> exit code.

## Retry e concorrência

- 5 tentativas por chunk: 2, 4, 8, 16, 32 s + jitter.
- 3 concorrentes por padrão.
- Após 3 falhas consecutivas, reduzir para 1.
- Após 6 falhas consecutivas, abortar com mensagem clara.
- Salvar o estado no SQLite a cada chunk.
- `--resume` (padrão) pula chunks `done` válidos.
- `--force` re-sintetiza o escopo indicado.

## Montagem de uma aula

1. Ordenar chunks da aula.
2. Para cada chunk:
   - decodificar o MP3 para WAV (cache);
   - inserir silêncio `gap_before_ms`;
   - concatenar PCM 16-bit 24 kHz mono.
3. Gerar `output/<SLUG>/.work/S01.wav`.
4. Aplicar loudnorm em duas passadas (se possível):
   - pass 1: medir `I`, `TP`, `LRA`, `thresh`, `offset`;
   - pass 2: aplicar com os valores medidos.
5. Opcional: suavizar o começo/fim com 50 ms de fade para evitar clique.
6. Codificar MP3 e M4B a partir do WAV normalizado.

### Por que WAV concatenado e não concat de MP3

Concatenar MP3 diretamente pode gerar gaps/artefatos por causa do encoder
delay/padding. Decodificar para PCM e concatenar é determinístico e permite
inserir silêncio com precisão de amostra.

## Loudness

- Alvo: **-16 LUFS** (padrão de podcast/audiolivro), true peak **-1,5 dBTP**.
- Duas passadas de `loudnorm` para precisão.
- Se a medição falhar, usar uma passada e registrar aviso.
- Não usar `dynaudnorm` (pode “bombear” a voz).

## MP3 por aula

```powershell
ffmpeg -y -i S01_norm.wav -c:a libmp3lame -b:a 64k -ar 24000 -ac 1 `
  -metadata title="Semana 1 — Noções Básicas de Marketing" `
  -metadata artist="PDF TTS (voz sintética)" `
  -metadata album="Fundamentos de Marketing" `
  -metadata track="1/7" `
  -metadata genre="Audiobook" `
  output/MKT-120/S01.mp3
```

## M4B com capítulos

### Arquivo de capítulos (`ffmetadata`)

```text
;FFMETADATA1
title=Fundamentos de Marketing — Semana 1
artist=PDF TTS
album=Fundamentos de Marketing
genre=Audiobook
[CHAPTER]
TIMEBASE=1/1000
START=0
END=180000
title=Semana 1 — Noções Básicas de Marketing
[CHAPTER]
TIMEBASE=1/1000
START=180000
END=420000
title=S01 Participação
```

### Comando

```powershell
ffmpeg -y -i S01_norm.wav -i cover.jpg -i chapters.txt `
  -map 0:a -map 1:v -map_metadata 2 -map_chapters 2 `
  -c:a aac -b:a 64k -ar 24000 -ac 1 `
  -c:v mjpeg -disposition:v attached_pic `
  -movflags +faststart output/MKT-120/S01.m4b
```

- Capa: página 1 do PDF renderizada com `pypdfium2` em ~1200 px de altura.
- Capítulos: semana + cada seção (`S01 Participação`, `Conclusão`, etc.).
- O M4B completo concatena as aulas com 2 s de silêncio e recalcula os offsets.

## SRT

- Uma cue por chunk (frase).
- Início/fim derivados da timeline (incluindo silêncios).
- Texto: `display_text` (limpo), não o texto normalizado.
- Formato:

```text
1
00:00:00,000 --> 00:00:04,250
Texto da frase.

2
00:00:04,250 --> 00:00:09,800
Próxima frase.
```

- Se um chunk tiver duração 0, ele é omitido.

## Manifest

`manifests/<slug>.json`:

```json
{
  "project": "mkt120",
  "title": "Fundamentos de Marketing",
  "slug": "MKT-120",
  "source_pdf": "input/MKT 120.pdf",
  "source_sha256": "EA08…",
  "engine": "edge",
  "voice": "pt-BR-FranciscaNeural",
  "rate": "-5%",
  "generated_at": "2026-11-17T12:00:00-03:00",
  "total_duration_s": 12345.6,
  "lessons": [
    {
      "id": "S01",
      "title": "Noções Básicas de Marketing",
      "start_page": 6,
      "end_page": 17,
      "duration_s": 1945.2,
      "chunks": 42,
      "files": {
        "mp3": "output/MKT-120/S01.mp3",
        "m4b": "output/MKT-120/S01.m4b",
        "srt": "output/MKT-120/S01.srt",
        "sha256_mp3": "…",
        "sha256_m4b": "…"
      },
      "sections": [
        {"title": "Semana 1 — Noções Básicas de Marketing", "start_s": 0.0},
        {"title": "S01 Participação", "start_s": 245.3}
      ]
    }
  ]
}
```

## Verificação automatizada

- `ffprobe` em todos os MP3/M4B: codec, sample rate, canais, duração.
- Duração da aula > 90% da estimativa (`chars / 15,5`).
- Nenhum chunk `failed`/`invalid` no SQLite.
- Capítulos monotônicos e dentro da duração.
- Última cue do SRT <= duração do áudio.
- Loudness dentro de ±1 LUFS do alvo (medir uma amostra ou todas as aulas).
- Hashes dos arquivos no manifest.

## Comandos

```powershell
# gerar uma aula
python -m pdf_tts build --project mkt120 --lesson S01

# gerar tudo, retomando
python -m pdf_tts build --project all --resume

# só montar (sem sintetizar)
python -m pdf_tts assemble --project mkt120

# status
python -m pdf_tts status --project all
```

## Limitações

- O Edge TTS pode falhar; o cache é a salvação.
- O M4B depende do FFmpeg com AAC.
- O cover depende de `pypdfium2`.
- O SRT é por frase, não palavra.
- O loudness pode variar levemente entre aulas; o alvo é consistente.
