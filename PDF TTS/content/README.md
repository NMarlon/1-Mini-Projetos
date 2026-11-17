# content/ — texto extraído e limpo (NÃO versionado)

Esta pasta guarda o resultado da extração dos PDFs:

```text
content/
├─ mkt120/
│  ├─ blocks.jsonl      ← todos os blocos, inclusive descartados
│  ├─ skipped.jsonl     ← blocos removidos + motivo
│  ├─ structure.json    ← semanas, seções, páginas e contagens
│  ├─ manuscript.md     ← texto legível para revisão humana
│  └─ lessons/
│     ├─ S01.json       ← blocos e texto falado da aula
│     └─ S01.txt        ← versão de leitura
└─ com150/...
```

## Por que não versionar

O texto é derivado de material didático possivelmente protegido. O repositório
é público; portanto, `content/` fica no `.gitignore`. O **código** que gera esse
conteúdo é versionado e reproduzível.

## Como regenerar

```powershell
python -m pdf_tts extract --project all
python -m pdf_tts segment --project all
```

A fonte é `input/*.pdf`. Se os PDFs não estiverem presentes, a extração falha
com uma mensagem clara. Veja `input/README.md`.

## O que é seguro compartilhar

- `content/*/structure.json` contém apenas títulos, páginas e contagens. Ainda
  assim, não é versionado por padrão.
- `manifests/*.json` (fora de `content/`) contém voz, ritmo, durações e hashes;
  não contém o corpo do texto e é versionado.
