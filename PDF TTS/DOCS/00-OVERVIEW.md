# 00 — Visão geral

## Objetivo

Converter os dois PDFs do curso em audiolivros narrados em português brasileiro,
com qualidade natural, custo zero e processamento local/na nuvem gratuita.

O resultado deve permitir que o usuário estude ouvindo o conteúdo, no carro, na
academia ou enquanto caminha, com a possibilidade de pular direto para a aula
da semana (`S01`…`S07`).

## Entradas

| Projeto | PDF | Páginas | Semanas |
|---|---|---|---|
| `mkt120` | `input/MKT 120.pdf` | 113 | 1–7 |
| `com150` | `input/Livro texto COM 150-1.pdf` | 220 | 1–7 |

Os PDFs têm camada de texto; **não é necessário OCR**.

## Saídas

Para cada projeto:

```text
output/<SLUG>/
├─ S01.mp3 … S07.mp3          # uma aula por arquivo
├─ S01.m4b … S07.m4b          # mesma aula com capítulos internos
├─ S01.srt … S07.srt          # legendas por frase
├─ <SLUG>-completo.mp3        # livro inteiro
├─ <SLUG>-completo.m4b        # livro inteiro com capítulos
├─ cover.jpg
├─ manifest.json
└─ README.md                  # tracklist e durações
```

Além disso:

- `content/<projeto>/` — texto extraído, limpo e revisável (local, não versionado);
- `manifests/<slug>.json` — registro do build (versionado, sem texto);
- `samples/` — amostras de voz (versionadas, texto sintético).

## Escopo de conteúdo (decisão do usuário)

**Entra no áudio:**

- capítulos, introduções, conclusões e resumos;
- quadros espirituais (“A Mão do Senhor”, “Mantenha o Ímpeto Espiritual”);
- listas de vocabulário/glossário e dicas de estudo;
- exercícios, quizzes, opções de resposta e lacunas;
- tarefas, estudos de caso, discussões e projeto final.

**Não entra no áudio:**

- capa, sumário, página de agradecimentos/copyright;
- cabeçalhos e rodapés repetidos, números de página;
- URLs e e-mails;
- bibliografia/listas de referências;
- linhas de UI do PDF (“This publication is currently unlisted”,
  “Filter content”).

Sublinhados de exercício (`________`) são falados como **“lacuna”**. Opções de
múltipla escolha são faladas como **“Opção: …”**.

## Voz e ritmo (decisão do usuário)

- Motor: **Edge TTS** (`edge-tts`), sem conta/API key.
- Voz: **`pt-BR-FranciscaNeural`**.
- Ritmo: **`-5%`** (~149 palavras/min).
- Formato: MP3 24 kHz mono 64 kbps; M4B AAC 24 kHz mono 64 kbps.

Justificativa e alternativas em [`02-RESEARCH-TTS.md`](02-RESEARCH-TTS.md).

## Restrições

- Windows 10/11, PowerShell.
- Python **3.11** (o `py` padrão da máquina é 3.15; não usar).
- CPU-only (Intel i5-1345U, 16 GB RAM, sem GPU NVIDIA).
- Internet necessária para o Edge TTS.
- FFmpeg/ffprobe no `PATH`.
- ~1,2 GB de áudio; ~2,7 GB de WAV temporário durante a montagem.
- Áudio e texto **não** são versionados (direitos autorais + tamanho).

## Não-objetivos (por enquanto)

- Interface gráfica/web.
- Clonagem de voz.
- Tradução para outro idioma.
- OCR de diagramas/imagens.
- Sincronização palavra-a-palavra (karaokê).
- Publicação/distribuição do áudio.
- Provider Google/Azure (backlog).

## Critérios de sucesso

1. 14 MP3 (7 por livro) com duração > 90% da estimativa e sem falhas audíveis.
2. 14 M4B (ou 2 M4B completos) com capítulos navegáveis.
3. 14 SRT sincronizados.
4. Nenhum chunk vazio ou com duração zero.
5. Conteúdo conferido contra o `manuscript.md` (cobertura de blocos).
6. Documentação e manifests atualizados.
7. Commits ao final de cada tarefa, sem PDFs/texto/áudio.

Checklist detalhado em [`11-VERIFICATION.md`](11-VERIFICATION.md).

## Estado atual

Ver [`06-TASKS.md`](06-TASKS.md). Este documento descreve o **alvo**; as tarefas
descrevem **onde estamos**.
