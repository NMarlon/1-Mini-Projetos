# 03 — Pipeline de PDF

## Objetivo desta etapa

Transformar os PDFs em uma sequência de blocos de texto confiáveis, na ordem
correta, sem lixo de layout e com metadados suficientes para dividir por
semana/seção.

O resultado fica em `content/<projeto>/` e **não é versionado** (copyright).

## Ferramenta

**`pdfplumber`** (MIT), sobre `pdfminer.six`. Fornece:

- `page.chars` com `text`, `fontname`, `size`, `x0`, `x1`, `top`, `bottom`;
- `page.extract_words(extra_attrs=["fontname", "size"])`;
- `page.find_tables()` / `page.extract_tables()`;
- coordenadas para detectar cabeçalhos, rodapés e colunas.

**Não usamos PyMuPDF** porque é AGPL e contaminaria o projeto. Se o
`pdfplumber` falhar em alguma página, comparar com `pypdf` (já instalado) antes
de considerar outra ferramenta.

## Estrutura dos PDFs

### MKT 120

| Semana | Páginas | Título | Caracteres |
|---|---|---|---|
| 1 | 6–17 | Noções Básicas de Marketing | 19.445 |
| 2 | 18–33 | Necessidades e Desejos dos Clientes | 23.832 |
| 3 | 34–46 | Análise SWOT | 20.873 |
| 4 | 47–65 | Pesquisa de Marketing | 29.075 |
| 5 | 66–79 | Desempenho de Marketing | 22.311 |
| 6 | 80–100 | Mix de Promoção | 48.101 |
| 7 | 101–113 | Estratégia de Vendas | 21.473 |

- 113 páginas, 186.604 caracteres.
- Capa (p. 1), sumário (p. 2–3), agradecimentos/copyright (p. 4–5) → fora.
- A p. 12 lista “Semana 1…7” em fonte de corpo; **não** é início de semana.
- 6 tabelas e 17 legendas de imagem.
- Tarefas em inglês (`Task:`, `Purpose:`) no meio de texto português.
- 7 URLs (OpenStax etc.).

### COM 150

| Semana | Páginas | Título | Caracteres |
|---|---|---|---|
| 1 | 7–31 | Fundamentos da Comunicação Interpessoal | 46.115 |
| 2 | 32–62 | Autocomunicação | 59.867 |
| 3 | 63–94 | Habilidades de Comunicação | 68.335 |
| 4 | 95–137 | Relacionamentos | 85.256 |
| 5 | 138–170 | Percepção | 64.931 |
| 6 | 171–210 | Conflito | 69.764 |
| 7 | 211–220 | Conclusão | 17.023 |

- 220 páginas, 413.704 caracteres.
- Capa (p. 1), sumário (p. 2–3), copyright (p. 4–6) → fora.
- Listas de referências sem título explícito em 21, 51–52, 82, 125–126,
  158–159, 196–197.
- Página 21 tem ordem de texto confusa (referências + questões + opções).
- Muitos exercícios de vocabulário com lacunas (`________`).
- Alguns títulos se repetem no sumário e no corpo; usar a faixa de páginas.

## Regras de extração

### 1. Linhas e blocos

1. Agrupar `chars` em palavras, palavras em linhas (tolerância vertical ~2,5 pt).
2. Ordenar por `top` e `x0` (coluna única). Se detectar duas colunas
   consistentes, ordenar por coluna.
3. Agrupar linhas em blocos quando:
   - o gap vertical > 1,6× a altura mediana da linha; ou
   - a linha anterior termina com pontuação final e a próxima começa com
     maiúscula; ou
   - o `x0` muda de forma significativa (indentação).
4. Mesclar linhas de título quebradas (ex.: “Semana 2: Necessidades e Desejos
   dos\nClientes”).

### 2. Classificação

| Tipo | Critério |
|---|---|
| `title` | Fonte ≥ `body_size * 1.5`, curta, no topo ou após gap grande |
| `heading` | Fonte ≥ `body_size * 1.15`, ou negrito ≥ 1.03× e curta |
| `paragraph` | Texto normal |
| `list_item` | Marcador (•, -, número) no início |
| `caption` | Começa com “Imagem”, “Figura”, “Tabela”, “Quadro” |
| `reference` | Fonte menor + score de citação ≥ 2 |
| `header`/`footer` | Topo/rodapé, repetido ou número de página |
| `table_row` | Linha extraída de tabela |

### 3. Remoções (com motivo em `skipped.jsonl`)

- Ligaduras: `ﬁ`→`fi`, `ﬂ`→`fl`, `ﬀ`→`ff`, `ﬃ`→`ffi`, `ﬄ`→`ffl`, `ﬅ`/`ﬆ`→`st`.
- Private Use Area: U+E000–U+F8FF, U+F0000–U+FFFFD, U+100000–U+10FFFD.
- `\u00a0`, `\u2007`, `\u202f`, `\u200b`, `\ufeff`, `\u00ad`, `\u200e`, `\u200f`.
- Controle, espaços múltiplos, linhas vazias.
- “This publication is currently unlisted…”, “Filter content…”.
- “Acesso gratuito em …” (depois de remover URL).
- URLs e e-mails.
- Números de página (linha só com dígitos no rodapé).
- Cabeçalhos/rodapés repetidos (ex.: “Fundamentos de Marketing”,
  “Comunicação Interpessoal: Teoria e Prática”).
- Bibliografia/blocos de referência.
- Sumário, capa, copyright/agradecimentos (páginas iniciais).

### 4. Hifenização

Se a linha termina em `-` e a próxima começa com minúscula:

- **Manter o hífen** se o próximo fragmento for pronome enclítico
  (`lo, la, los, las, me, te, se, nos, vos, lhe, lhes, o, a, os, as`) ou prefixo
  conhecido (`e-, pré-, pós-, bem-, mal-, auto-, micro-, macro-, anti-, co-,
  re-, sub-, super-, ultra-, vice-, ex-, sem-, pró-`).
- **Remover o hífen** nos demais casos (quebra de linha comum).

Exemplos:
- `torná-` + `los` → `torná-los` (manter)
- `impedi-` + `am` → `impediam` (remover)
- `e-` + `mail` → `e-mail` (manter)

### 5. Tabelas

- `page.find_tables()` com bbox; remover as linhas dentro do bbox do fluxo
  normal e gerar `table_row` blocks.
- Cada linha vira uma frase: `Coluna A: valor; Coluna B: valor.`
- Ignorar tabelas com < 2 linhas/colunas ou que ocupem > 85% da página
  (provável layout, não tabela).
- Revisar as tabelas no `manuscript.md`; se a extração piorar a leitura,
  desativar para a página em `config/structure.yaml` (futuro).

### 6. Imagens

- Ignorar imagens decorativas.
- Manter legendas (“Imagem 1.1 …”) como `caption`.
- OCR de diagramas fica no backlog (Tesseract), pois adiciona ruído e depende
  de instalação externa.

## Regras de estrutura

- A semana é determinada por `config/projects.yaml` (`start_page`/`end_page`).
  Isso é a fonte de verdade; a detecção por fonte só confirma o título.
- Se o título “Semana N” for detectado fora da faixa (sumário, lista), ignorar.
- Seções começam em títulos que casam com `config/structure.yaml`:
  - `S0\d` (ex.: `S01 Participação`, `S01 Tarefa: …`);
  - `Introdução`, `Conclusão`, `Resumo`;
  - `Vocabulário`, `Glossário`, `Dicas de Estudo`;
  - `Exercícios`, `Verificação de Conhecimento`;
  - `Projeto Final`, `Estudo de Caso`, `Discussão`, `Tarefa`;
  - `A Mão do Senhor`, `Mantenha o Ímético Espiritual`.
- Títulos quebrados em duas linhas são mesclados.
- Se uma seção não tiver conteúdo, é descartada.
- Se a detecção falhar, adicionar override em `config/structure.yaml`
  (estrutura `manual_sections`, a implementar) ou ajustar a regra.

## Saídas

### `blocks.jsonl`

Um bloco por linha, com todos os campos, inclusive `drop_reason`.

### `skipped.jsonl`

Blocos removidos com motivo (`page_number`, `header`, `reference`, `url`,
`boilerplate`, `empty`).

### `structure.json`

```json
{
  "project": "mkt120",
  "title": "Fundamentos de Marketing",
  "weeks": [
    {
      "week": 1,
      "id": "S01",
      "title": "Noções Básicas de Marketing",
      "start_page": 6,
      "end_page": 17,
      "chars": 19445,
      "sections": [
        {"id": "S01-01", "title": "Semana 1 — Noções Básicas de Marketing", "type": "week"},
        {"id": "S01-02", "title": "S01 Participação", "type": "sxx"},
        {"id": "S01-03", "title": "A Mão do Senhor", "type": "spiritual"}
      ]
    }
  ]
}
```

### `manuscript.md`

Documento legível para revisão humana:

```markdown
# Fundamentos de Marketing

## Semana 1 — Noções Básicas de Marketing

### S01 Participação

Texto do parágrafo…

### S01 Plano de Marketing: Perfil da Empresa

Texto…
```

Blocos descartados aparecem em um apêndice com página e motivo.

### `lessons/S01.json` e `S01.txt`

- JSON: blocos, seções, texto de exibição e texto falado.
- TXT: versão de leitura, com títulos e parágrafos.

## Processo de revisão (obrigatório)

Antes de sintetizar um projeto novo:

1. Rodar `extract` e `segment`.
2. Abrir `content/<projeto>/manuscript.md`.
3. Conferir:
   - as 7 semanas estão nos lugares certos;
   - nenhum trecho grande faltando;
   - referências não estão no meio do conteúdo (ou estão marcadas);
   - exercícios e quizzes estão presentes (decisão do usuário);
   - títulos não duplicados;
   - tabelas legíveis.
4. Se algo estiver errado, corrigir a regra no código/config e regenerar; não
   editar o texto à mão.
5. Registrar o que foi revisado em `06-TASKS.md`.

## Testes

- `tests/test_clean.py`: ligaduras, PUA, URLs, cabeçalhos, hifenização.
- `tests/test_classify.py`: títulos, opções, small print, referências e tabelas.
- Validação nos PDFs reais:
  - contagem de caracteres por semana próxima da tabela acima;
  - nenhum bloco com PUA ou ligadura;
  - títulos das 7 semanas corretos;
  - `skipped.jsonl` com motivos.

## Aprendizados da implementação (2026-11-17)

- `page.chars` + agrupamento por `top` funciona bem; os espaços já vêm nos
  chars, mas uma regra de gap (`> 0.45 * size`) corrige células grudadas.
- Corpo é 9,0 pt; títulos 15–25,7 pt; `Roboto-Black` em 9,0 pt é **ênfase**
  (termo de vocabulário, cabeçalho de tabela), não título.
- Cabeçalho de página: `top≈21.7`, 8 pt Helvetica; rodapé: `top≈757.7`.
- `find_tables()` acha tabelas reais e falsos positivos; o filtro de ≥2 colunas
  efetivas resolve (falsos positivos são de 1 coluna).
- Tabelas reais sem borda são reconstruídas bem por `extract_tables()`:
  p52 (pesquisa), p72 (CLV), p86 (mix de promoção), p93/106 etc.
- Células com quebra de linha: se a linha seguinte começa com `-`, é item de
  lista (`; `); caso contrário, é continuação (` `). Isso deixou as tabelas
  legíveis.
- Legendas de figura em 7,2 pt são conteúdo; só descartar créditos que
  **começam** com Fonte/Atributo/etc. Se o crédito está no fim, remover apenas
  o crédito.
- Bibliografias sem título são detectadas por score (ano, editora, Conferência
  Geral, “pág.”, autor). Um parágrafo com ≥2 frases não é referência.
- Após a primeira referência, só descartar fragmentos de citação; uma citação
  isolada não deve “engolir” as instruções seguintes.
- Títulos genéricos (“Introdução”, “Conclusão”) podem se repetir dentro de
  tarefas; não deduplicar globalmente. Tratar como subseção quando estão na
  mesma página de uma tarefa/estudo de caso/discussão.
- Seções muito longas (>6.000 chars) são divididas em títulos nível 1, para
  gerar capítulos de tamanho razoável.
- O `blocks.jsonl` guarda `original_kind`/`original_level` para que
  `resegment` seja idempotente.
