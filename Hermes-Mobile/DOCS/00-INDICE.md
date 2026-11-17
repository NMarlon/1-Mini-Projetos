# 00 — Índice da documentação

Última atualização: **2026-11-16**

Este é o ponto de entrada da documentação do **Hermes-Mobile**.
Leia o [`AGENTS.md`](../AGENTS.md) antes de alterar qualquer coisa.

---

## Ordem de leitura recomendada

### Para entender o projeto

1. [`01-VISAO-GERAL.md`](01-VISAO-GERAL.md) — objetivo, escopo, estado atual.
2. [`02-ARQUITETURA-E-CONEXAO.md`](02-ARQUITETURA-E-CONEXAO.md) — diagrama,
   componentes, fluxo, decisões técnicas (ADRs).
3. [`07-APPS-MOBILE.md`](07-APPS-MOBILE.md) — por que Pomelu e o que foi
   descartado.

### Para usar / configurar

4. [`03-GUIA-RAPIDO.md`](03-GUIA-RAPIDO.md) — passo a passo PC + celular.
5. [`04-SCRIPTS-E-COMANDOS.md`](04-SCRIPTS-E-COMANDOS.md) — cada script e
   comando.
6. [`05-SEGURANCA.md`](05-SEGURANCA.md) — senha, revogação, o que não fazer.

### Para resolver problema

7. [`06-TROUBLESHOOTING.md`](06-TROUBLESHOOTING.md) — sintoma → causa → correção.
8. [`09-ERROS-E-APRENDIZADOS.md`](09-ERROS-E-APRENDIZADOS.md) — erros reais
   desta e de sessões anteriores.

### Para continuar o projeto

9. [`10-TAREFAS.md`](10-TAREFAS.md) — o que está feito, pendente ou bloqueado.
10. [`11-BACKLOG-E-IDEIAS.md`](11-BACKLOG-E-IDEIAS.md) — ideias futuras.
11. [`12-VERIFICACAO-E-TESTES.md`](12-VERIFICACAO-E-TESTES.md) — testes e
    evidências.
12. [`08-REFERENCIAS.md`](08-REFERENCIAS.md) — links, versões, fontes.

---

## Legenda de status

| Símbolo | Significado |
|---|---|
| 🟢 | Feito e validado |
| 🟡 | Em andamento / parcial |
| 🔴 | Bloqueado / não funciona |
| ⚪ | Ainda não iniciado |
| 📌 | Leitura obrigatória para continuar |

## Arquivos fora da pasta

| Caminho | O que é |
|---|---|
| `%LOCALAPPDATA%\hermes\.env` | Segredos do Hermes (auth do gateway, tokens) |
| `%LOCALAPPDATA%\hermes\config.yaml` | Configuração do Hermes (`dashboard.public_url`) |
| `%LOCALAPPDATA%\HermesMobile\secrets.json` | Senha do gateway (ACL do usuário) |
| `%LOCALAPPDATA%\HermesMobile\logs\` | Logs locais (não versionados) |
| Tarefa Agendada `Hermes Mobile - Servidor` | Autostart no login |
