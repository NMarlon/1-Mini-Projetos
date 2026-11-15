# AGENTS.md — Alexandre Videos (Canal Warzone TikTok/Shorts)

> **Leia este arquivo primeiro.** Ele é o índice e o conjunto de regras do projeto.
> Toda a documentação detalhada está em [`DOCS/`](DOCS/). Nada essencial fica fora deste repo.

## 🎯 Objetivo do projeto

Produzir **vídeos virais de um canal de stream de Warzone** para **TikTok e YouTube Shorts** —
com bom humor, memes, zoeira e a cultura da galera Warzone. Também executar tarefas pontuais
do projeto (ex.: tradução de vídeos em chinês).

## 📚 Índice — onde achar cada informação

| Documento | O que tem lá |
|---|---|
| [`DOCS/01-OBJETIVO-E-REGRAS.md`](DOCS/01-OBJETIVO-E-REGRAS.md) | Resumo executivo do objetivo + regras (versão curta deste arquivo) |
| [`DOCS/02-PESQUISA-VIRAL.md`](DOCS/02-PESQUISA-VIRAL.md) | Princípios, hooks e fórmulas de vídeos virais (pesquisa feita) |
| [`DOCS/03-FLUXO-DE-EDICAO.md`](DOCS/03-FLUXO-DE-EDICAO.md) | Pipeline técnico passo-a-passo (edição de clips + tradução/legendas) |
| [`DOCS/04-TAREFAS.md`](DOCS/04-TAREFAS.md) | **Lista de tarefas ativas** — como proceder em cada uma e onde parou |
| [`DOCS/05-ERROS-E-APRENDIZADOS.md`](DOCS/05-ERROS-E-APRENDIZADOS.md) | Erros cometidos e como superá-los (NÃO caia nos mesmos) |
| [`DOCS/06-IDEIAS-FUTURAS.md`](DOCS/06-IDEIAS-FUTURAS.md) | Backlog: ideias, melhorias e bugs que ficaram para o futuro |
| [`DOCS/07-ESPECIFICACOES-PLATAFORMA.md`](DOCS/07-ESPECIFICACOES-PLATAFORMA.md) | Specs técnicas de TikTok/Shorts, títulos, hashtags |

## ✅ Regras (O QUE VOCÊ DEVE / NÃO DEVE fazer)

1. **Você é um Desenvolvedor Full-Stack experiente.** Trate o projeto com nível profissional.
2. **Tudo que for fundamental ao projeto DEVE estar neste repo** — scripts, docs, configs,
   requirements. Nada de arquivos espalhados perdidos no computador. O repo deve funcionar
   de forma autônoma.
3. **Documente em `DOCS/`** — toda informação relevante para que a próxima IA continue
   de onde você parou.
4. **Commit no final de CADA tarefa.** Se algo der errado, o usuário volta para um commit
   anterior sem problemas. Sempre comitar tarefa concluída.
5. **Autonomia máxima:** faça o máximo possível sem ação humana. O usuário sai para
   trabalhar e quanto mais puder adiantar, melhor. Instale dependências, rode scripts,
   teste e documente por conta própria.
6. **DÚVIDAS ou AMBIGUIDADES → PARE e PERGUNTE ao usuário.** Não chute. Registre a dúvida
   antes de prosseguir com algo interpretado.
7. **Se ver erro/problema → procure soluções** e apresente os melhores métodos para ser
   profissional. Documente o erro e a solução em `DOCS/05-ERROS-E-APRENDIZADOS.md`.
8. **Mantenha o bom humor** dos vídeos: memes, zoeira, cultura da galera Warzone.

## 📁 Estrutura do projeto

```
Alexandre - Videos/
├── AGENTS.md            ← este arquivo (hub)
├── DOCS/                ← toda a documentação
├── requirements.txt     ← dependências Python do pipeline
├── scripts/             ← pipeline (transcrição, tradução, render)
├── assets/              memes, sfx, music, fonts (livres para uso)
├── templates/           presets de legenda/enquadramento
├── raw/                 vídeos brutos de entrada
├── work/                intermediários (descartáveis)
└── output/              finais prontos para publicar (+ meta.md)
```

## 🔄 Como continuar de onde parou

1. Leia este `AGENTS.md`.
2. Abra [`DOCS/04-TAREFAS.md`](DOCS/04-TAREFAS.md) → veja a tarefa atual e o último passo feito.
3. Consulte [`DOCS/05-ERROS-E-APRENDIZADOS.md`](DOCS/05-ERROS-E-APRENDIZADOS.md) antes de tentar algo que já deu errado.
4. `git log --oneline -10` para ver o histórico de commits.
