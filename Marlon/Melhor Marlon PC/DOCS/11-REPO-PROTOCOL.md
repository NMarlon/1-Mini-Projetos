# 11 — Protocolo do repositório

Este documento detalha as regras do `AGENTS.md`. Ele existe para a próxima IA
continuar sem depender do chat.

## 1. Um projeto por vez

- Trabalhe só em `Marlon/Melhor Marlon PC/`.
- O repo raiz tem outros projetos com alterações pendentes. **Nunca**
  `git add .`.
- Stage explícito:

```powershell
git add -- "Marlon/Melhor Marlon PC"
git status
git commit -m "feat(marlon-pc): ..."
```

## 2. Um commit por tarefa

- Toda tarefa de `DOCS/06-TASKS.md` termina com commit.
- Se a tarefa for grande, divida em commits menores, mas sempre deixe o repo
  funcionando.
- Mensagens: `feat(marlon-pc):`, `fix(marlon-pc):`, `docs(marlon-pc):`,
  `chore(marlon-pc):`.
- **Nunca** `push`.

## 3. O que entra no Git

| Entra | Não entra |
|---|---|
| Código, scripts, testes | `vendor/` (driver) |
| `AGENTS.md`, `README.md`, `DOCS/` | `reports/` |
| `config/*.json` sem segredos | `logs/` |
| `driver.lock.json` (URL/hash) | `temp/` |
| `src/data/*.csv` | senhas, tokens, chaves |

## 4. Autonomia

Faça sozinho:

- criar/editar arquivos do projeto;
- rodar diagnóstico read-only;
- baixar driver oficial com hash;
- rodar testes;
- commitar.

Pare e pergunte:

- senha do roteador/Wi-Fi;
- reset de rede da impressora;
- mudança no roteador;
- impressão de teste;
- qualquer ação destrutiva.

## 5. Continuidade

Ao final de cada tarefa, atualize:

1. `DOCS/06-TASKS.md` — status e próxima tarefa.
2. `DOCS/08-ERRORS-AND-LESSONS.md` — erros/aprendizados.
3. `DOCS/09-DECISIONS.md` — se mudou decisão.
4. `DOCS/10-VERIFICATION.md` — se mudou critério.
5. `config/printer.json` — se descobriu IP/MAC/modelo.

Se parar no meio, deixe o **comando exato** para continuar em
`DOCS/06-TASKS.md`.

## 6. Rollback

O usuário usa os commits como pontos de retorno. Para desfazer uma tarefa:

```powershell
git log --oneline
git revert <hash>
```

Não usar `git reset --hard` nem `git clean` sem autorização.

## 7. Qualidade

- Testar no PowerShell 5.1.
- Não deixar script quebrar por causa de acento/encoding.
- Não parsear texto localizado do Windows.
- Não imprimir sem confirmação.
- Não gravar segredo em log.
- Não instalar driver de fonte não oficial.

## 8. Definição de pronto

Ver `DOCS/10-VERIFICATION.md` e a seção 9 do `AGENTS.md`.
