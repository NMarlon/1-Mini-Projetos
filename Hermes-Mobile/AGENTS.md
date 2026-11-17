# AGENTS.md — Hermes-Mobile

> **Arquivo de referência para a próxima IA/dev que continuar este projeto.**
> Leia na íntegra ANTES de modificar qualquer coisa.

Última atualização: **2026-11-16** (sessão: IA assistindo Marlon)

---

## 1. Objetivo do projeto

Permitir que o Marlon use o **Hermes Agent que roda no PC Windows** a partir
do **celular Android (Galaxy A32)**, com acesso privado via **Tailscale** e
interface do app **Pomelu** (cliente Android/iOS open-source para Hermes).

Resultado esperado:

1. No celular, abrir o Pomelu e ver os bots/perfis do Hermes do PC.
2. Conversar, aprovar comandos, responder perguntas, enviar arquivos/fotos/voz.
3. Acompanhar tarefas e sessões de qualquer lugar (com o PC ligado).
4. Reconfigurar outro PC com poucos comandos usando esta pasta.

## 2. O que este projeto NÃO é

- ❌ Não é um fork nem um cliente Android próprio.
- ❌ Não instala um Hermes separado no celular (Termux).
- ❌ Não usa o Webapp oficial do Hermes (o bundle não vem na instalação da
  Microsoft Store; ver `DOCS/09-ERROS-E-APRENDIZADOS.md`).
- ❌ Não gerencia modelos, chaves de provider nem licenças.
- ❌ Não abre porta no roteador nem usa Tailscale Funnel.

## 3. Estado atual (2026-11-16)

| Item | Valor |
|---|---|
| Sistema | Windows 11 Pro (Dell Latitude 5440) |
| Hermes | **v0.23.1 stable**, instalado via Microsoft Store/MSIX |
| Home do Hermes | `C:\Users\Marlon\AppData\Local\hermes` |
| CLI | `hermes` no PATH (alias da Store); aviso pré-existente `install out of sync` |
| Servidor | `hermes serve` em `127.0.0.1:9119` |
| Autenticação | `dashboard.basic_auth` via `.env` (usuário + hash scrypt + secret) |
| URL pública | `https://marlon-dell-pc.tail6ded59.ts.net:8443` |
| Tailscale | v1.104.6; PC `marlon-dell-pc` = `100.76.44.54` |
| Celular | Galaxy A32 `a32-de-marlon` = `100.66.158.57` |
| OpenCode | continua em `https://marlon-dell-pc.tail6ded59.ts.net` (443 → 28894) |
| App Android | **Pomelu** (`se.royan.pomelu`) |
| Autostart | Tarefa Agendada `Hermes Mobile - Servidor` no login |
| Energia | **não alterada** (decisão do Marlon em 16/11/2026) |
| Plugin Pomelu | **não instalado** (backlog; ver `DOCS/11-BACKLOG-E-IDEIAS.md`) |
| Segredos | fora do Git (`.env` + `secrets.json`) |

## 4. ⚠️ REGRAS OBRIGATÓRIAS

### REGRA 00 — Dúvidas ou ambiguidades → PARE E PERGUNTE

> **IMPORTANTE**: se tiver qualquer dúvida, ambiguidade ou decisão que possa
> afetar o PC, o celular, a segurança ou outro projeto do Marlon, **PARE E
> PERGUNTE**. Não assuma nada. Não preencha lacunas por conta própria.

### REGRA 01 — Escopo da pasta

- **Tudo** relacionado a este projeto fica em `Hermes-Mobile/`.
- Só é permitido alterar fora daqui o que for **instalação/configuração de
  sistema** explicitamente necessária (Tarefa Agendada, Tailscale Serve,
  `.env` do Hermes).
- Documentação e artefatos nunca “escapam” da pasta.

### REGRA 02 — Segurança primeiro

- **NUNCA** versionar/commitar senha, token, hash, cookie, `.env`,
  `secrets.json`, QR ou screenshot com segredo.
- Segredos vivem em `%LOCALAPPDATA%\hermes\.env` e
  `%LOCALAPPDATA%\HermesMobile\secrets.json` (ACL do usuário).
- **NUNCA** abrir porta no roteador.
- **NUNCA** usar `tailscale funnel`.
- **NUNCA** trocar o bind do Hermes para `0.0.0.0` sem autorização explícita.
- Se um segredo entrar no Git, remover da história/rotacionar e avisar Marlon.

### REGRA 03 — Documentação viva

Sempre que mudar algo importante, atualize o arquivo certo:

| Mudança | Onde atualizar |
|---|---|
| Arquitetura / conexão / decisão técnica | `DOCS/02-ARQUITETURA-E-CONEXAO.md` |
| Como usar PC ↔ celular | `DOCS/03-GUIA-RAPIDO.md` |
| Scripts / comandos | `DOCS/04-SCRIPTS-E-COMANDOS.md` |
| Segurança / senha / revogação | `DOCS/05-SEGURANCA.md` |
| Bug / falha de rede | `DOCS/06-TROUBLESHOOTING.md` |
| Comparativo de apps | `DOCS/07-APPS-MOBILE.md` |
| Versão / links | `DOCS/08-REFERENCIAS.md` |
| **Erro real que você cometeu** | `DOCS/09-ERROS-E-APRENDIZADOS.md` |
| **Estado atual / tarefas** | `DOCS/10-TAREFAS.md` |
| **Ideia / TODO futuro** | `DOCS/11-BACKLOG-E-IDEIAS.md` |
| **Testes e evidências** | `DOCS/12-VERIFICACAO-E-TESTES.md` |

### REGRA 04 — Rode `Status-Diagnostico.ps1` antes de mudar

O estado real pode mudar (Windows Update, Tailscale, Hermes, Store).
Antes de qualquer mudança importante:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1
```

### REGRA 05 — Simplicidade

Não criar camadas de abstração desnecessárias. O projeto é pequeno e deve
continuar **simples e portátil**. Não criar app Android, não compilar
frontend, não instalar Node/pnpm.

### REGRA 06 — Preserve arquivos de usuário

Arquivos de origem desconhecida ou de outros projetos do repositório
`1-Mini-Projetos` **não devem ser apagados nem alterados**. Em especial:
`Alexandre - Videos/` e `Reconhecedor de Rostos de  Imagens/`.

### REGRA 07 — PowerShell 5.1

Esta máquina usa **PowerShell 5.1**. Não use `pwsh` nem recursos do PS 7
(`-AsHashtable`, ternário `?:`, `??`, `&&`). Todos os `.ps1` são **UTF-8 com
BOM** para acentos funcionarem.

### REGRA 08 — Teste antes de dizer “está pronto”

Antes de declarar qualquer coisa de rede/segurança “pronta”:

- Execute o **comando real** e mostre a **saída real**.
- Rode `scripts/Status-Diagnostico.ps1`.
- Deixe o log em `logs/` (ignorado pelo Git).
- Teste a URL pública, não só o loopback.

### REGRA 09 — Não quebrar o OpenCode

O Tailscale Serve **443** pertence ao OpenCode (`127.0.0.1:28894`).
O Hermes usa **8443**. Nunca remova/altere o handler 443 sem autorização.

### REGRA 10 — Não parar o servidor do Desktop

O Hermes Desktop pode ter o próprio `hermes serve` em outra porta. Não rode
`hermes serve --stop` (para todos) sem antes verificar. Pare apenas o PID
que este projeto subiu, via `Parar-Mobile.ps1`.

### REGRA 11 — Commits

- **Ao fim de cada tarefa/fase, faça commit.**
- Use `git add -- "Hermes-Mobile"` e commite **somente** esta pasta.
- **Nunca** use `git add -A` nem `git add .` no repositório `1-Mini-Projetos`
  (há alterações antigas de outros projetos).
- Push para o remote só com autorização explícita do Marlon.
- Mensagens no padrão Conventional Commits, em português.

### REGRA 12 — Autonomia

O Marlon pode estar fora. Faça o máximo de forma autônoma **no PC**:
instalar/configurar/testar/commitar. Não espere por ele para o que for
seguro e reversível. Pare apenas para: dúvida real, decisão de segurança,
ação no celular, ou algo que possa quebrar outro projeto.

### REGRA 13 — Não atualizar/rebuildar o Hermes sem backup

O aviso `install out of sync` é pré-existente. **Não** rode `hermes update`,
`hermes desktop --force-build` ou reinstalação sem backup e autorização.
Uma atualização pode mudar o protocolo e quebrar o Pomelu.

### REGRA 14 — Não mexer em energia

Decisão do Marlon em 16/11/2026: **não alterar** suspensão/hibernação.
`Manter-Acordado.ps1` existe apenas como opção manual; não rodar sozinho.

### REGRA 15 — Idioma

Documentação e mensagens em **português (pt-BR)**. Nomes de código,
comandos e chaves de configuração permanecem em inglês.

---

## 5. 📂 Mapa de arquivos

| O que preciso achar | Está em |
|---|---|
| Objetivo, conceitos, estado atual | `DOCS/01-VISAO-GERAL.md` |
| Diagrama, componentes, ADRs | `DOCS/02-ARQUITETURA-E-CONEXAO.md` |
| Passo a passo PC novo + celular | `DOCS/03-GUIA-RAPIDO.md` |
| Scripts / comandos | `DOCS/04-SCRIPTS-E-COMANDOS.md` |
| Segurança / senha / revogação | `DOCS/05-SEGURANCA.md` |
| Diagnóstico de bug / rede | `DOCS/06-TROUBLESHOOTING.md` |
| Comparativo de apps | `DOCS/07-APPS-MOBILE.md` |
| Links / referências oficiais | `DOCS/08-REFERENCIAS.md` |
| 📌 **Erros reais** e como evitar | `DOCS/09-ERROS-E-APRENDIZADOS.md` |
| 📌 **Tarefas do projeto** | `DOCS/10-TAREFAS.md` |
| 📌 Ideias / TODO futuro | `DOCS/11-BACKLOG-E-IDEIAS.md` |
| 📌 Testes e evidências | `DOCS/12-VERIFICACAO-E-TESTES.md` |

## 6. 🧭 Primeira ação de uma sessão nova

1. Rode `scripts/Status-Diagnostico.ps1`.
2. Leia `DOCS/10-TAREFAS.md` — ache a tarefa 🟡 em andamento.
3. Leia `DOCS/09-ERROS-E-APRENDIZADOS.md` — do fim para o início.
4. Leia `DOCS/02-ARQUITETURA-E-CONEXAO.md` — inclui ADRs.
5. Só então comece a trabalhar.

## 7. 🧰 Comandos essenciais

```powershell
# Primeira instalação (faz TUDO: auth + servidor + Tailscale + autostart)
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1

# Dia a dia: garantir servidor + Tailscale
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1

# Diagnóstico de saúde (rodar ANTES de assumir qualquer coisa)
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1

# Mostrar/copiar credenciais
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar
```

Detalhes em `DOCS/04-SCRIPTS-E-COMANDOS.md`.

## 8. 🔒 Resumo da segurança

- Rota: Celular → Tailscale (WireGuard) → Tailscale Serve HTTPS `:8443` →
  `hermes serve` em `127.0.0.1:9119`.
- Servidor escuta **apenas** em `127.0.0.1`.
- `dashboard.public_url` liga o login obrigatório mesmo em loopback.
- Auth: usuário + senha com hash **scrypt** + secret de assinatura.
- Nenhuma porta pública; sem Funnel.
- App Pomelu guarda credenciais no Android Keystore.
- Segredos ficam fora do repo.

## 9. 🚫 O que a próxima IA NUNCA deve fazer

- Assumir algo sem perguntar (REGRA 00).
- Commitar senha/segredo (REGRA 02).
- Abrir porta no roteador ou usar Funnel (REGRA 02).
- Trocar o bind para `0.0.0.0` sem autorização (REGRA 02).
- Remover/alterar o handler 443 do OpenCode (REGRA 09).
- Rodar `hermes serve --stop` sem verificar o Desktop (REGRA 10).
- Usar `git add -A` (REGRA 11).
- Rodar `hermes update`/rebuild sem backup (REGRA 13).
- Alterar energia (REGRA 14).
- Apagar arquivos de outros projetos (REGRA 06).

## 10. 🏁 Como finalizar a sessão

Antes de encerrar, **atualize obrigatoriamente**:

1. `DOCS/10-TAREFAS.md` — status da tarefa atual (🟢 feito / 🟡 pendente / 🔴 bloqueado).
2. `DOCS/09-ERROS-E-APRENDIZADOS.md` — registre erros **reais**.
3. `DOCS/11-BACKLOG-E-IDEIAS.md` — se surgiu ideia nova.
4. `DOCS/12-VERIFICACAO-E-TESTES.md` — evidências dos testes.
5. `DOCS/01-VISAO-GERAL.md` — estado atual, se mudou.
6. **Este AGENTS.md** — atualize a data no topo.
7. Faça o commit final da pasta.

## 11. Links oficiais

- Hermes Agent: <https://github.com/NousResearch/hermes-agent>
- Hermes Docs: <https://hermes-agent.nousresearch.com/docs/>
- Pomelu: <https://github.com/ateymoori/pomelu>
- Pomelu Play Store: <https://play.google.com/store/apps/details?id=se.royan.pomelu>
- Pomelu plugin (push): <https://github.com/ateymoori/pomelu-hermes-plugin>
- Tailscale Serve: <https://tailscale.com/kb/1247/funnel-serve-use-cases>

## 12. Colaborador

Marlon — projeto criado e mantido junto com Hermes Agent v0.23.1, Pomelu,
Tailscale v1.104.6, no Windows 11.
