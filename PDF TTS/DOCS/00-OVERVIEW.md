# 00 — Visão geral

## Objetivo

Converter os PDFs do Pathway em audiolivros narrados em português brasileiro,
com qualidade natural, custo zero e processamento local/na nuvem gratuita.

O resultado deve permitir que o usuário estude ouvindo o conteúdo, no carro, na
academia ou enquanto caminha, com a possibilidade de pular direto para a aula
da semana (`S01`…`S07`). O mesmo pipeline também aceita PDFs de outras origens
que tenham camada de texto.

## Dois modos de uso

| Modo | Entrada | Como funciona |
|---|---|---|
| **Curado** | `input/MKT 120.pdf` e `input/Livro texto COM 150-1.pdf` | Páginas das semanas definidas em `config/projects.yaml`; pipeline `extract` → `segment` → `build` → `assemble` → `verify`. |
| **App Pathway PDF TTS** | Qualquer PDF com texto | Interface no navegador, perfil Pathway ou genérico, fila local, modos de conteúdo e edição de capítulos. |

O modo curado é a fonte dos dois audiolivros já entregues. O app é a entrada
para o usuário leigo e para PDFs novos.

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
├─ coverage.json              # páginas narradas, sem áudio, só imagem e blocos descartados
├─ manifest.json
└─ README.md                  # tracklist e durações
```

Além disso:

- `content/<projeto>/` — texto extraído, limpo e revisável (local, não versionado);
- `manifests/<slug>.json` — registro do build (versionado, sem texto);
- `manifests/AUTO-*.json` — builds de PDFs arbitrários (local, não versionado);
- `samples/` — amostras de voz (versionadas, texto sintético);
- `dist/Pathway PDF TTS/` — app portátil principal (não versionado);
- `dist/Pathway PDF TTS (PyInstaller)/` — alternativa menor (não versionada).

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

No app, o usuário escolhe entre três comportamentos de conteúdo:

| Modo | O que entra |
|---|---|
| **Automático** | Conteúdo didático; remove bibliografia, créditos e boilerplate. |
| **Tudo útil** (`all`) | Conteúdo + referências/notas/créditos; remove cabeçalho, rodapé, número de página, URL e ícone. |
| **Tudo literal** (`raw`) | Tudo o que o extrator encontrou, inclusive cabeçalho, rodapé, número de página e link. |

O escopo curado acima corresponde ao modo **Automático**. Os modos `all` e
`raw` existem para quem quiser ouvir o material sem limpeza editorial.

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
- FFmpeg/ffprobe no `PATH` no modo curado; o app portátil leva FFmpeg junto.
- ~1,2 GB de áudio; ~2,7 GB de WAV temporário durante a montagem.
- Áudio e texto **não** são versionados (direitos autorais + tamanho).
- O app portátil não exige Python nem FFmpeg instalados.

## Não-objetivos (por enquanto)

- Clonagem de voz.
- Tradução para outro idioma.
- OCR de diagramas/imagens.
- Sincronização palavra-a-palavra (karaokê).
- Publicação/distribuição do áudio.
- Provider Google/Azure (backlog).
- Assinatura digital própria do `.exe` (hoje a versão principal usa o Python
  assinado da PSF; ver [`12-ONE-CLICK-APP.md`](12-ONE-CLICK-APP.md)).

## Critérios de sucesso

1. 14 MP3 (7 por livro) com duração > 90% da estimativa e sem falhas audíveis.
2. 14 M4B (ou 2 M4B completos) com capítulos navegáveis.
3. 14 SRT sincronizados.
4. Nenhum chunk vazio ou com duração zero.
5. Conteúdo conferido contra o `manuscript.md` (cobertura de blocos).
6. App portátil abre, analisa PDFs Pathway/genéricos e gera os arquivos.
7. Documentação e manifests atualizados.
8. Commits ao final de cada tarefa, sem PDFs/texto/áudio.

Checklist detalhado em [`11-VERIFICATION.md`](11-VERIFICATION.md).

## Estado atual

**T00–T19 concluídas; 59 testes passando.** O modo curado entregou MKT 120 e
COM 150; o app Pathway PDF TTS está implementado e empacotado; o tutorial de
download está em DOCS/13, o protocolo em DOCS/14 e o suporte por e-mail está na
interface. Ver
[`06-TASKS.md`](06-TASKS.md) para o estado detalhado e o próximo passo. Este
documento descreve o **alvo**; as tarefas descrevem **onde estamos**.
