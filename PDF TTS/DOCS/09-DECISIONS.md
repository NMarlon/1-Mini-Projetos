# 09 — Decisões arquiteturais (ADRs)

Registro das decisões importantes e do porquê. Se você for mudar uma delas,
leia o contexto e registre a nova decisão.

---

## D001 — Edge TTS como motor principal

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** precisamos de voz natural em pt-BR, gratuita, para ~600 mil
caracteres, sem GPU.

**Decisão:** usar `edge-tts` com a voz `pt-BR-FranciscaNeural`.

**Alternativas:** Google Chirp 3 HD (melhor, mas exige billing), Azure DragonHD
(melhor, exige conta), Phonon 40m PT (ótimo local, CC BY-NC e gate), Pocket TTS
(MIT, mas qualidade/1 voz), Kokoro (fraco em pt-BR), Piper (robótico).

**Consequências:**
- Dependência de serviço não oficial e de internet.
- Falhas intermitentes exigem retry/cache.
- Texto sai da máquina (privacidade).
- Custo zero e qualidade alta.

---

## D002 — Voz Francisca

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** 3 vozes pt-BR listadas; Francisca é a mais natural e rápida.

**Decisão:** `pt-BR-FranciscaNeural`, ritmo `-5%`.

**Consequências:**
- ~149 palavras/min, boa para estudo.
- Termos em inglês (MKT) terão sotaque brasileiro.
- Se o usuário preferir Antonio/Thalita, é possível re-renderizar.

---

## D003 — Pipeline próprio em vez de ebook2audiobook

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** existem ferramentas prontas (ebook2audiobook, epub2tts,
Audiblez), mas são focadas em EPUB/Kokoro/XTTS e têm pouca granularidade.

**Decisão:** pipeline Python próprio com Edge TTS, `pdfplumber`, cache por
chunk e montagem FFmpeg.

**Consequências:**
- Mais código para manter.
- Controle total sobre limpeza, divisão S01–S07, capítulos e retomada.
- Dependências leves (sem torch).

---

## D004 — Faixas de página explícitas para as semanas

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** os PDFs não têm outline; a página 12 do MKT lista todas as
semanas e enganaria uma detecção só por regex.

**Decisão:** `config/projects.yaml` contém `start_page`/`end_page` de cada
semana. A detecção por fonte é usada para títulos de seção, não para decidir a
semana.

**Consequências:**
- Se o PDF mudar, os hashes e as páginas precisam ser revistos.
- Estrutura determinística e testável.

---

## D005 — `pdfplumber`, não PyMuPDF

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** PyMuPDF é mais fácil/rápido, mas é AGPL.

**Decisão:** `pdfplumber` (MIT) para texto/fonte/tabelas; `pypdfium2` para a
capa.

**Consequências:**
- Extração mais lenta, mas suficiente (113/220 páginas).
- Sem contaminação de licença.

---

## D006 — Áudio não versionado

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** ~1,2 GB de áudio e ~400 MB de cache.

**Decisão:** `output/` e `cache/` no `.gitignore`; `manifests/` versionados.

**Consequências:**
- O repo não cresce; o áudio é regenerável.
- O manifest registra o que existia.

---

## D007 — PDFs e texto não versionados (repo público)

**Data:** 2026-11-17
**Status:** aceita (decisão do usuário)

**Contexto:** o repo `NMarlon/1-Mini-Projetos` é público; os PDFs são material
didático possivelmente protegido.

**Decisão:** `input/` e `content/` no `.gitignore`; commitar apenas código,
config, docs, testes, amostras sintéticas e manifests sem texto.

**Consequências:**
- Um clone novo precisa dos PDFs locais.
- `input/README.md` traz SHA-256 e instruções.
- O código é reproduzível; o conteúdo não é redistribuído.

---

## D008 — Incluir exercícios e quizzes

**Data:** 2026-11-17
**Status:** aceita (decisão do usuário)

**Contexto:** o usuário quer “tudo, inclusive exercícios/quiz”.

**Decisão:** incluir exercícios, quizzes, opções e lacunas; lacunas viram
“lacuna”; opções viram “Opção: …”.

**Consequências:**
- Áudio mais longo e com trechos menos fluídos.
- Nada do conteúdo didático fica de fora.

---

## D009 — Excluir bibliografia/referências

**Data:** 2026-11-17
**Status:** aceita (decisão do usuário)

**Contexto:** listas de citações são longas e ruins de ouvir.

**Decisão:** remover blocos de referência por heurística (fonte menor + score de
citação), mantendo exercícios que estejam na mesma página.

**Consequências:**
- Pode ser necessário revisar páginas mistas (COM 21/158).
- `skipped.jsonl` registra o que foi removido.

---

## D010 — Cache por chunk com hash

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** o Edge TTS falha e o build é longo.

**Decisão:** chave `sha256(engine|voice|rate|volume|pitch|texto)`; MP3 atômico;
SQLite de status.

**Consequências:**
- Retomada granular.
- Cache cresce, mas é limpo no futuro (`clean-cache`).

---

## D011 — Concatenação em WAV, não em MP3

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** concatenar MP3 pode gerar gaps/artefatos.

**Decisão:** decodificar cada chunk para WAV PCM 24 kHz mono e concatenar com
silêncio por amostra; codificar uma vez no final.

**Consequências:**
- Mais disco/time, mas qualidade e sincronização melhores.
- SRT/capítulos com offsets precisos.

---

## D012 — SRT por frase, não por palavra

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** word boundaries do Edge podem variar e exigem mais complexidade.

**Decisão:** uma cue por chunk (frase), com duração real do áudio.

**Consequências:**
- Legendas boas para leitura, não para karaokê.
- Simples e robusto.

---

## D013 — Não misturar vozes automaticamente

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** se o Edge falhar em alguns chunks, trocar de voz criaria
inconsistência.

**Decisão:** falhar e preservar o cache; nunca trocar de motor/voz no meio sem
decisão explícita.

**Consequências:**
- Build pode parar; o usuário/IA retoma depois.
- Consistência de timbre no livro inteiro.

---

## D014 — Commits locais, sem push automático

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** o repo é público e o usuário quer commits para rollback.

**Decisão:** commitar ao final de cada tarefa; não fazer `push` sem pedido.

**Consequências:**
- O histórico local protege o trabalho.
- O usuário controla quando publicar.

---

## D015 — Python 3.11

**Data:** 2026-11-17
**Status:** aceita

**Contexto:** a máquina tem 3.11 e 3.15; dependências (pdfplumber/pypdfium2/
edge-tts) são mais testadas em 3.11.

**Decisão:** usar `.venv` com 3.11.

**Consequências:**
- Evita surpresas de compatibilidade.
- `doctor` valida a versão.

---

## D016 — App com identidade Pathway e perfil próprio

**Data:** 2026-11-18
**Status:** aceita (decisão do usuário)

**Contexto:** o app é usado principalmente nos cursos Pathway, mas também deve
aceitar PDFs de outras origens.

**Decisão:**
- renomear o app para **Pathway PDF TTS**;
- perfil padrão `auto` tenta Pathway primeiro (`Semana N`, `S01`–`S07`);
- perfil `generic` cobre outros PDFs por outline/títulos/padrões;
- se nada for encontrado, fallback em blocos de páginas, com aviso.

**Consequências:**
- A interface deixa claro para que serve e como editar capítulos.
- PDFs fora do Pathway continuam suportados, mas sem promessa de semântica.

---

## D017 — Três modos de conteúdo

**Data:** 2026-11-18
**Status:** aceita (decisão do usuário)

**Contexto:** “Tudo” estava ambíguo: incluía referências mas removia
cabeçalho/página/link.

**Decisão:**
- `auto` — limpa bibliografia/boilerplate;
- `all` — tudo útil: referências/notas/créditos, sem cabeçalho/página/link;
- `raw` — tudo literal: inclusive cabeçalho, número de página, rodapé e link.

**Consequências:**
- `raw` gera áudio mais repetitivo; a interface avisa.
- O relatório `coverage.json` continua valendo para todos.

---

## D018 — Embalagem principal com Python assinado

**Data:** 2026-11-18
**Status:** aceita

**Contexto:** o Smart App Control do Windows bloqueou o `.exe` recém-gerado
pelo PyInstaller (“política de Controle de Aplicativo bloqueou este arquivo”).
O usuário não tem certificado de code signing.

**Decisão:** distribuir como versão principal uma pasta com o `pythonw.exe`
assinado pela Python Software Foundation, renomeado para `Pathway PDF TTS.exe`,
mais `Lib`, `DLLs`, `tcl`, `site-packages`, `src` e FFmpeg locais. Um
`sitecustomize.py` adiciona o código ao `sys.path`, ajusta o `PATH` e abre a GUI
quando o executável é iniciado sem argumentos.

**Consequências:**
- O `.exe` tem assinatura válida da PSF e passa pelo Smart App Control.
- A pasta é maior (~428 MB) que a versão PyInstaller (~277 MB).
- A versão PyInstaller continua disponível como alternativa menor.
- Não é um `.exe` único; é uma pasta portátil com um `.exe` assinado.
