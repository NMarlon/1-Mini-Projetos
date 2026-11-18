# 08 — Erros e aprendizados

Registro vivo. Toda vez que algo der errado, anote aqui **o erro**, **a causa**,
**a solução** e **como evitar**. A próxima IA não deve cair nos mesmos buracos.

---

## E001 — `py --version` aponta para Python 3.15

**Erro:** `py --version` retornou 3.15.2, mas o projeto precisa de 3.11.
**Causa:** o launcher `py` escolhe a versão mais nova por padrão.
**Solução:** usar sempre `py -3.11 -m venv .venv` e ativar o `.venv`.
**Evitar:** `doctor` valida `sys.version_info` e avisa se não for 3.11.

---

## E002 — Console PowerShell quebra acentos (cp1252)

**Erro:** `UnicodeEncodeError: 'charmap' codec can't encode character`.
**Causa:** encoding padrão do console Windows.
**Solução:** definir `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`; escrever arquivos
com `encoding="utf-8"`.
**Evitar:** scripts PowerShell e `doctor` configuram as variáveis.

---

## E003 — PDFs com ligaduras tipográficas

**Erro:** texto extraído contém `ﬁ`, `ﬂ`, `ﬀ`, `ﬃ`, `ﬄ`.
**Causa:** fontes do PDF usam ligaduras.
**Solução:** mapa de substituição em `clean.py`.
**Evitar:** teste `test_clean_ligatures` e assert de que nenhum bloco contém
U+FB00–U+FB06.

---

## E004 — Ícones em Private Use Area viram lixo

**Erro:** caracteres `\uf584`, `\uf6b0` etc. no texto.
**Causa:** ícones/checkboxes do layout do PDF.
**Solução:** remover faixas PUA; `\uf584` marca opções de quiz e pode virar
“Opção:”.
**Evitar:** assert de que nenhum bloco contém U+E000–U+F8FF.

---

## E005 — Falso positivo de “Semana N” no sumário

**Erro:** a página 12 do MKT lista “Semana 1…7” em fonte de corpo; uma detecção
ingênua criaria 7 aulas ali.
**Causa:** regex sem contexto de fonte/posição.
**Solução:** faixas de página explícitas em `projects.yaml` + exigir fonte de
título e posição no topo.
**Evitar:** teste de estrutura nas páginas 2–3 e 12 do MKT.

---

## E006 — Ordem de texto confusa em páginas com referências/opções

**Erro:** COM p. 21 mistura questão, referências, títulos de S01 e opções.
**Causa:** o PDF foi montado com múltiplos blocos/colunas.
**Solução:** classificar referências por fonte/tamanho e remover; manter as
questões; revisar `manuscript.md`.
**Evitar:** inspeção manual das páginas 19–23, 51–52, 82, 125–126, 158–159,
196–197.

---

## E007 — `edge-tts` cria arquivo vazio e sai com código 0

**Erro:** ao testar vozes inexistentes (`pt-BR-ElzaNeural` etc.), o CLI criou
arquivos de 0 bytes e o `ffprobe` falhou com “Invalid data found”.
**Causa:** o CLI não valida o áudio recebido.
**Solução:** usar a API Python, capturar `NoAudioReceived`, validar tamanho e
duração com `ffprobe`, marcar `invalid` e repetir.
**Evitar:** nunca confiar no exit code; sempre validar o artefato.

---

## E008 — `edge-tts` tem falhas intermitentes (WebSocket 1006)

**Erro:** `NoAudioReceived: No audio was received` em algumas requisições.
**Causa:** instabilidade do serviço não oficial.
**Solução:** retry com backoff, concorrência 1–4, cache por chunk.
**Evitar:** não rodar 20 requisições em paralelo; não perder progresso.

---

## E009 — ThalitaMultilingual é ~3x mais lenta

**Erro:** geração de 24 s de áudio levou 15,5 s (vs. 7,3 s da Francisca).
**Causa:** modelo multilíngue maior.
**Solução:** Francisca como padrão; Thalita só se o inglês do MKT incomodar.
**Evitar:** medir latência antes de escolher a voz para 11 h de áudio.

---

## E010 — Kokoro é fraco em pt-BR

**Erro:** as vozes pt-BR do Kokoro têm Elo 1.633 e nota ~5,6; o resultado soa
pior que o Edge.
**Causa:** pouco treino em português.
**Solução:** não usar Kokoro neste projeto; fallback local é Phonon/Pocket.
**Evitar:** não assumir que “modelo popular em inglês” é bom em pt-BR.

---

## E011 — PyMuPDF é AGPL

**Erro:** a opção mais fácil para layout (`fitz`) é AGPL.
**Causa:** licença do PyMuPDF.
**Solução:** usar `pdfplumber` (MIT) + `pypdfium2` para capa.
**Evitar:** verificar licença antes de adicionar dependência.

---

## E012 — PDFs e texto não podem ir para repo público

**Erro:** o repo `NMarlon/1-Mini-Projetos` é público; os PDFs são material
didático possivelmente protegido.
**Causa:** decisão de transparência do usuário + copyright.
**Solução:** `input/` e `content/` no `.gitignore`; commitar só código/docs/
manifests. O usuário escolheu essa opção explicitamente.
**Evitar:** nunca rodar `git add -f` nesses diretórios.

---

## E013 — `pypdf` não encontra outline/índice

**Erro:** `PdfReader.outline` retorna vazio nos dois PDFs.
**Causa:** PDFs montados por `pdf-merger-js`/`pdf-lib`, sem bookmarks.
**Solução:** estrutura detectada por conteúdo + faixas de página.
**Evitar:** não depender de outline.

---

## E014 — `ffmpeg` instalado em dois caminhos

**Erro:** `where.exe ffmpeg` retornou duas versões (9.0.1 e 9.0.2).
**Causa:** instalações antigas do winget.
**Solução:** usar o primeiro do PATH; `doctor` mostra a versão e o caminho.
**Evitar:** não fixar caminho absoluto sem fallback.

---

## E015 — Sem GPU NVIDIA

**Erro:** `nvidia-smi` não existe.
**Causa:** máquina com Intel UHD.
**Solução:** Edge TTS é nuvem; montagem é CPU. Modelos locais pesados ficam no
backlog.
**Evitar:** não planejar XTTS/F5/Orpheus local sem GPU.

---

## E016 — `uv` e `gh` não estão instalados

**Erro:** comandos `uv`/`gh` não encontrados.
**Causa:** ambiente limpo.
**Solução:** usar `pip`/`venv` e `git` puro. Não depender de `gh` para commits.
**Evitar:** scripts devem checar ferramentas opcionais.

---

## E017 — Áudio é grande demais para Git

**Erro:** ~1,2 GB de áudio + cache.
**Causa:** 11 h de fala em MP3/M4B.
**Solução:** `output/` e `cache/` no `.gitignore`; manifests versionados.
**Evitar:** nunca `git add output`.

---

## E018 — Nomes com espaços/acentos

**Erro:** caminhos como `PDF TTS`, `Livro texto COM 150-1.pdf`.
**Causa:** nomes originais.
**Solução:** `pathlib`, aspas nos comandos, slugs ASCII para saída.
**Evitar:** não renomear os PDFs sem atualizar `projects.yaml` e o SHA-256.

---

## E019 — PowerShell scanner rejeita heredoc complexo

**Erro:** `Portable shell scanner cannot analyze command: invalid-structure` ao
passar um script Python com `^`/`\b` em `python -c`.
**Causa:** o scanner do shell não lida bem com certos caracteres.
**Solução:** usar `python -c @"..."@` (here-string) ou criar um arquivo `.py`
temporário.
**Evitar:** para scripts longos, criar arquivo; não abusar de one-liners.

---

## E020 — `content/` é derivado e não versionado

**Erro:** ao clonar o repo em outra máquina, `content/` não existe.
**Causa:** decisão de copyright.
**Solução:** copiar os PDFs para `input/`, rodar `extract`/`segment`.
**Evitar:** documentar o checklist de clone novo em `05-OPERATIONS.md`.

---

## E021 — Caminho digitado errado criou pasta fora do repo

**Erro:** ao criar `cli.py`, o caminho foi digitado como
`C:\MarlonScripts\1-IMini-Projetos\...` (com “I” extra), criando uma pasta fora
do repositório.
**Causa:** erro de digitação em caminho absoluto.
**Solução:** a pasta foi removida e o arquivo foi criado no caminho correto.
**Evitar:** usar caminhos relativos dentro do projeto (`PDF TTS/...`) e conferir
`git status`/`Test-Path` após criar arquivos.

---

## E022 — `resegment` leu blocos já mutados

**Erro:** depois de transformar “Conclusão” em subseção, o `resegment` não a
reconhecia mais como seção, porque o `blocks.jsonl` já estava com `kind=heading`.
**Causa:** a segmentação mutava `block.kind` e gravava o bloco mutado.
**Solução:** adicionar `original_kind`/`original_level` ao `Block`; a segmentação
restaura a classificação original antes de reestruturar.
**Evitar:** nunca usar o campo mutável como fonte de verdade para reprocessar.
Mantenha o “cru” separado do “renderizado”.

---

## E023 — Falsos positivos de tabela em listas/quizzes

**Erro:** `page.find_tables()` detectou “tabelas” de 1 coluna nos quizzes,
listas de vocabulário e respostas.
**Causa:** o detector infere tabelas por alinhamento de texto.
**Solução:** aceitar apenas tabelas com ≥ 2 colunas **efetivas** (células
preenchidas) e ≥ 2 linhas. Tabelas reais (p52, p72, p86) têm 3–4 colunas.
**Evitar:** sempre inspecionar `table.extract()` antes de usar; ignorar tabelas
de 1 coluna.

---

## E024 — `small_print` dropava conteúdo com “Fonte:”

**Erro:** legendas como “Percepção é como... Fonte: Pexels.com” eram descartadas
inteiras.
**Causa:** a regra dropava qualquer texto pequeno que contivesse “Fonte:”.
**Solução:** dropar apenas linhas que **começam** com Fonte/Atributo/etc.;
quando o crédito está no fim, remover só o crédito (`strip_attribution`).
**Evitar:** separar “é crédito?” de “contém crédito?”.

---

## E025 — Modo de referência dropava instruções seguintes

**Erro:** em p169, o parágrafo “Compartilhe sua opinião...” foi classificado
como referência e removido; em outros casos, instruções após uma citação eram
descartadas.
**Causa:** score de referência alto por “Conferência Geral” + ano; modo de
referência agressivo.
**Solução:** parágrafos com ≥ 2 frases ou > 300 chars não são referência;
modo de referência só continua para fragmentos de citação (curtos, minúsculos,
publisher/periódico). Caso contrário, encerra o modo.
**Evitar:** testar páginas com citações no meio de exercícios (COM 169, 158).

---

## E026 — Deduplicação global de títulos juntou seções diferentes

**Erro:** “Introdução” da semana e “Introdução” de uma tarefa foram fundidas,
puxando o conteúdo da tarefa para a introdução.
**Causa:** deduplicação por título em toda a semana.
**Solução:** não deduplicar títulos globalmente; remover apenas seções vazias e
tratar “Introdução/Conclusão” dentro de tarefa/estudo de caso como subseção.
**Evitar:** títulos genéricos podem se repetir legitimamente; use contexto
(tipo da seção + página) em vez de texto puro.

---

## E027 — “COM” case-insensitive virava “com”

**Erro:** “Preencha ________ com cuidado” virou “Preencha lacuna C O M cuidado”.
**Causa:** a substituição de siglas usava `re.IGNORECASE`; `\bCOM\b` casou com
“com”.
**Solução:** `case_sensitive: true` nas siglas; o normalizador respeita o campo.
**Evitar:** qualquer sigla curta (COM, TI, IA, RH) deve ser case-sensitive.

---

## E028 — Notas de rodapé colavam no texto

**Erro:** “melhor.6” → “melhor. seis.”; “Tusler10” → “Tusler10”; “favor.11
Essas” → “favor.onze”.
**Causa:** números de nota no fim/início de frases e anexados a palavras.
**Solução:**
- remover `([.!?"”’])\s*\d{1,3}` quando seguido de espaço+maiúscula/fim;
- remover dígitos anexados a palavra minúscula antes de pontuação/espaço;
- separar letra+número (`Week4` → `Week 4`) **depois** das notas e antes dos
  números.
**Evitar:** testar páginas com notas de rodapé (COM 36, 47, 151, 196, 221).

---

## E029 — Fragmentos de frase viravam chunks isolados

**Erro:** chunks “Essa.”, “Peço que.”, “Uma pequena.”, “A fórmula é.”.
**Causa:** o PDF quebra a frase em blocos por layout; o chunker tratava cada
bloco como independente.
**Solução:** pós-processar a seção: fragmentos < 30 chars são fundidos com o
**próximo** chunk; se terminam em palavra funcional (`que`, `é`, `uma`…),
remover o ponto artificial e minusculizar a continuação.
**Evitar:** não fundir com o anterior (o fragmento costuma iniciar a frase
seguinte).

---

## E030 — Datas inválidas (frações) ficavam com dígitos

**Erro:** “13/75” virava “13 ou 75” com dígitos.
**Causa:** a regex de data protegia “13/75” e `_date` devolvia o texto original
quando dia/mês inválidos; os números não eram convertidos.
**Solução:** data inválida vira “treze dividido por setenta e cinco”.
**Evitar:** toda função de proteção deve devolver texto já normalizado, nunca
dígitos crus.

---

## E031 — Cache de `-5%` e `5%` colidiria

**Erro:** `sanitize_component("-5%")` removia o sinal e virava `5pct`; `"5%"`
também viraria `5pct`.
**Causa:** `.strip("._-")` removeu o hífen inicial.
**Solução:** prefixar `neg` quando o valor começa com `-`; `-5%` → `neg5pct` e
`+5%` → `p5pct`.
**Evitar:** nunca remover sinais de taxas/velocidades ao gerar nomes de pasta.

---

## E032 — Montagem exige que o build tenha gravado os `cache_key`

**Erro:** se você rodar `segment` e depois `assemble` sem `build`, a aula não
tem `cache_key`/áudio e a montagem falha com “Chunk sem áudio”.
**Causa:** a montagem lê os MP3 do cache; o `build` é quem sintetiza e grava as
chaves no JSON da aula.
**Solução:** rodar `build --project … --lesson …` antes de `assemble`; o build
com `--no-assemble` já deixa tudo pronto.
**Evitar:** o `assemble` calcula a chave a partir do texto como fallback, mas o
arquivo ainda precisa existir no cache.

---

## E033 — `loudnorm` e capítulos no M4B

**Observação:** o comando `ffmpeg -f ipod` com `-map_metadata`/`-map_chapters`
funcionou; a capa `mjpeg` foi embutida como `attached_pic` e os capítulos
aparecem em `ffprobe -show_chapters`.
**Cuidado:** `-map_metadata`/`-map_chapters` precisam apontar para o **índice**
do arquivo de capítulos (1 sem capa, 2 com capa). Se mudar a ordem dos `-i`,
ajuste os índices.

---

## E034 — Não rodar dois builds Edge em paralelo

**Risco:** dois processos com 3 conexões cada = 6 conexões simultâneas ao
serviço não oficial, aumentando 429/1006 e falhas em cascata.
**Regra:** um build por vez. Para paralelizar, aumente `--concurrency` no
máximo até 4, nunca dois processos.
**Sintoma:** `NoAudioReceived`/WebSocket 1006 em sequência; o cache preserva o
que já foi feito.

---

## E035 — Remoção de nota de rodapé comeu o “.2” de “Tabela6.2”

**Erro:** a legenda “Tabela6.2” virava “Tabela6.” e o áudio dizia “Tabela seis.”
**Causa:** a regex de nota de rodapé `([.!?])\s*\d{1,3}` casou com o `.2` de
“Tabela6.2”, interpretando como nota.
**Solução:** exigir que o sinal de pontuação **não** seja precedido por dígito:
`(?<!\d)([.!?"”’])\s*\d{1,3}...`.
**Evitar:** testar legendas com numeração decimal (`Tabela 6.2`, `Imagem 1.1`).

---

## E036 — Montagem do COM 150 estourou 30 min

**Erro:** `assemble --project com150` foi interrompido por timeout de 30 min
depois de montar S01–S05 e iniciar S06.
**Causa:** cada aula leva ~5–6 min (decodificar chunks, concatenar WAV,
loudnorm em duas passadas e encodar MP3/M4B); 7 aulas + livro completo passam
de 30 min.
**Solução:** `assemble_lesson` agora reaproveita `Sxx.mp3/.m4b/.srt/_norm.wav`
quando são mais novos que o JSON da aula; rerun retomou de S06/S07 e montou o
livro completo. Use timeout de 60 min para o primeiro build do COM.
**Evitar:** para livros longos, rode `assemble` em background ou por aula;
não mate o processo se os arquivos anteriores já existem — o skip evita
re-trabalho.

---

## E037 — Uvicorn quebra no `.exe` com `--noconsole`

**Erro:** o portátil iniciava e morria com
`AttributeError: 'NoneType' object has no attribute 'isatty'` em
`uvicorn/logging.py`.
**Causa:** em app windowed (`console=False`), `sys.stdout` e `sys.stderr` são
`None`; o logging do uvicorn chama `.isatty()`.
**Solução:** `launcher._ensure_streams()` redireciona ambos para
`logs/launcher.log` antes de criar o servidor.
**Evitar:** qualquer app Python windowed que use logging/uvicorn precisa de
streams válidos.

---

## E038 — FastAPI + Ruff B008

**Erro:** Ruff acusou `B008 Do not perform function call File in argument
defaults`.
**Causa:** o padrão clássico do FastAPI (`file: UploadFile = File(...)`).
**Solução:** usar `Annotated[UploadFile, File()]` e
`Annotated[str, Form()]`.
**Evitar:** prefira `Annotated` em projetos com Ruff ativo.

---

## E039 — Sumário virava capítulos no modo genérico

**Erro:** a detecção achou “Semana 2…7” no sumário do COM e criou capítulos
falsos; também pegou `S01` como capítulo.
**Causa:** títulos de sumário usam a mesma fonte; `S0x` parece capítulo.
**Solução:**
- ignorar páginas iniciais com muitos títulos (sumário);
- priorizar padrões fortes (`Semana`, `Capítulo`, `Parte`, `Aula`…);
- tratar `S0x` como subseção quando há padrões fortes;
- escolher o título com padrão na página, não o primeiro por posição.
**Evitar:** validar detecção nos PDFs reais e permitir edição manual.

---

## E040 — Título de metadados inútil

**Erro:** slug/título viravam `(anonymous)` ou um hash/uuid.
**Causa:** metadados do ReportLab/Word e nome do upload temporário.
**Solução:** ignorar títulos vazios, “anonymous”, “untitled”, “Microsoft Word”
e strings hex/uuid; usar o nome original do arquivo enviado.
**Evitar:** sempre ter fallback para o nome do arquivo.

---

## E041 — `relative_to(ROOT)` em PDF externo

**Erro:** manifest falhou com PDF temporário fora do repositório.
**Causa:** `project.pdf.relative_to(ROOT)` levanta `ValueError` quando o PDF
está em `%TEMP%`.
**Solução:** usar caminho relativo somente se `is_relative_to(ROOT)`; senão,
guardar o caminho absoluto.
**Evitar:** nunca assumir que a entrada está dentro da pasta do projeto.

---

## E042 — Caminho de config/web/ffmpeg no PyInstaller

**Observação:** o `.exe` usa `ROOT` = pasta do executável (dados/áudio) e
`RESOURCE_ROOT` = `_internal` (config/web). O ffmpeg/ffprobe foram copiados
para a pasta do `.exe` e são encontrados por `find_tool`.
**Evitar:** usar `Path(__file__)` para dados graváveis em app congelado; separe
recursos de dados.

---

## Modelo para novos registros

```markdown
## E0XX — Título curto

**Erro:** o que aconteceu.
**Causa:** por que aconteceu.
**Solução:** o que foi feito.
**Evitar:** regra/teste para não repetir.
```
