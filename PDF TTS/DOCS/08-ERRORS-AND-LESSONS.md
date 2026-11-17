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

## Modelo para novos registros

```markdown
## E0XX — Título curto

**Erro:** o que aconteceu.
**Causa:** por que aconteceu.
**Solução:** o que foi feito.
**Evitar:** regra/teste para não repetir.
```
