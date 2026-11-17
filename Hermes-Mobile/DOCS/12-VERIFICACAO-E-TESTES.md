# 12 — Verificação e testes

Última atualização: **2026-11-17**

> Registre aqui **evidências reais** (comando + saída resumida + data).
> Não declare “pronto” sem testar.

---

## 1. Checklist rápido

| # | Teste | Status | Evidência |
|---|---|---|---|
| 1 | Hermes instalado e versão | 🟢 | 0.23.1 |
| 2 | `hermes serve` rodando em 9119 | 🟢 | PID 15672 |
| 3 | `/api/status` local com `auth_required: true` | 🟢 | HTTP 200 |
| 4 | Login local funciona | 🟢 | cookies + `/api/profiles` 200 |
| 5 | Tailscale Serve `:8443` ativo | 🟢 | → 9119 |
| 6 | `/api/status` via HTTPS do tailnet | 🟢 | HTTP 200 |
| 7 | Login via HTTPS | 🟢 | 200 + `__Host-` cookies |
| 8 | OpenCode `:443` intacto | 🟢 | 401 sem auth |
| 9 | Autostart no login | 🟢 | Tarefa `Hermes Mobile - Servidor` |
| 10 | Pomelu conecta e lista bots | 🟢 | confirmado pelo Marlon |
| 11 | Prompt no Pomelu recebe resposta | 🟢 | confirmado pelo Marlon |
| 12 | Aprovação/pergunta no Pomelu | 🟡 | testar quando aparecer |
| 13 | Nenhum segredo no Git | 🟢 | `git grep` sem match |
| 14 | Webapp 9120/8444 | 🟢 | 200 local/público |
| 15 | Login + HTML do webapp | 🟢 | `__HERMES_UI_SURFACE__` |
| 16 | Gateway como login item | 🟢 | `Hermes_Gateway.vbs` |
| 17 | Mono Hermes conecta | 🟢 | aviso de versão (0.22 vs 0.23) |

---

## 2. Comandos de verificação

### 2.1. Hermes

```powershell
hermes --version
hermes serve --status
hermes config get dashboard.public_url
hermes config get dashboard.basic_auth
```

### 2.2. Porta e processo

```powershell
Get-NetTCPConnection -LocalPort 9119 -State Listen |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

### 2.3. Saúde local

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://127.0.0.1:9119/api/status
curl.exe -s http://127.0.0.1:9119/api/status
```

Esperado:

```json
{
  "version": "0.23.1",
  "auth_required": true,
  "auth_providers": ["basic"],
  "profiles": ["default", "..."]
}
```

### 2.4. Tailscale

```powershell
tailscale status
tailscale serve status
tailscale serve status --json
tailscale funnel status
```

Esperado no `serve status`:

```text
https://marlon-dell-pc.tail6ded59.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:28894
https://marlon-dell-pc.tail6ded59.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:9119
```

`tailscale funnel status` **não** deve listar nada.

### 2.5. Saúde via HTTPS

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
```

### 2.6. Login via HTTPS

```powershell
$body = '{"provider":"basic","username":"hermes","password":"<SENHA>","next":""}'
curl.exe -s -i -c cookies.txt -X POST `
  https://marlon-dell-pc.tail6ded59.ts.net:8443/auth/password-login `
  -H "Content-Type: application/json" -d $body

# Com os cookies:
curl.exe -s -b cookies.txt https://marlon-dell-pc.tail6ded59.ts.net:8443/api/profiles
```

Esperado: HTTP 200/303, cookies `hermes_session_at` e `hermes_session_rt`,
e uma lista de perfis.

> Apague `cookies.txt` depois. Ele está no `.gitignore`.

### 2.7. OpenCode intacto

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" https://marlon-dell-pc.tail6ded59.ts.net/api/info
```

Esperado: **401** sem Basic Auth (prova que o serviço está de pé e protegido).

### 2.8. Autostart

```powershell
Get-ScheduledTask -TaskName "Hermes Mobile - Servidor" |
  Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName "Hermes Mobile - Servidor" |
  Select-Object LastRunTime,LastTaskResult,NextRunTime
```

### 2.9. Segredos no Git

```powershell
cd C:\MarlonScripts\1-Mini-Projetos
git status --short
git grep -n -E "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD|password_hash|scrypt\$" -- Hermes-Mobile
```

Esperado: nenhum segredo.

---

## 3. Teste no celular (humano)

1. Tailscale ligado no A32.
2. Pomelu instalado.
3. URL `https://marlon-dell-pc.tail6ded59.ts.net:8443`.
4. Usuário/senha.
5. **Test connection** → **Save and connect**.
6. Lista de bots aparece.
7. Enviar “Olá, responda OK”.
8. Pedir um comando que exija aprovação (ex.: “liste os arquivos do projeto
   e proponha apagar um arquivo temporário”) e aprovar no celular.
9. Fechar o app e reabrir; a sessão deve continuar.

Registrar data/hora e resultado.

---

## 4. Evidências

### 2026-11-16 — Fase 0

- Estrutura criada.
- (preencher após commits/testes)

### 2026-11-16 — Fase 1

- `hermes serve` rodando em `127.0.0.1:9119` (PID 15668 no momento do teste).
- `GET /api/status` → HTTP 200:
  `{"version":"0.23.1","auth_required":true,"auth_providers":["basic"],"auth_flows":["cookie","native_pkce"],"profiles":["default","conversa","manager-developer-hermes","matematico","neuroia"]}`
- Login local: `POST /auth/password-login` → HTTP 200; cookies
  `hermes_session_at`, `hermes_session_rt`, `hermes_session_provider`.
- `GET /api/profiles` com Bearer → HTTP 200 (5 perfis).
- WebSocket `ws://127.0.0.1:9119/api/ws`:
  - `gateway.ready` recebido.
  - `profiles.list` retornou os perfis.
- Teste de agente: `session.create` + `prompt.submit`
  ("Responda apenas com a palavra OK.") → `message.complete status=complete`,
  texto `OK`.
- Modelo: `deepseek-flash` foi rejeitado pelo OpenCode Go; trocado
  `model.default` para `deepseek-v4.1-flash` (backup em
  `%LOCALAPPDATA%\HermesMobile\backups\config-20261116-212349.yaml`).
- `Status-Diagnostico.ps1` executado com sucesso.

### 2026-11-16 — Fase 2

- Tailscale Serve `:8443 → 127.0.0.1:9119` ativo.
- `/api/status` via HTTPS → 200; login HTTPS → 200; `/api/profiles` → 200.
- OpenCode `:443 → 28894` preservado (401 sem auth).
- WebSocket WSS + `session.create` + prompt "OK" → `complete`.
- `tailscale serve status` mostrava 443 e 8443.

### 2026-11-16 — Fase 3

- `Instalar-Autostart.ps1` criou a Tarefa Agendada
  `Hermes Mobile - Servidor` (estado `Running`).
- O log `logs/task-servidor-20261116-213711.log` mostra:
  `HERMES_BACKEND_READY port=9119` e `HERMES_DASHBOARD_READY port=9119`.
- `Parar-Mobile.ps1` parou somente o PID do `hermes serve`; porta livre;
  `:443` do OpenCode preservado.
- `Iniciar-Servidor.ps1` (background via VBS) subiu o servidor (PID 17060)
  e respondeu HTTP 200.
- `Iniciar-Mobile.ps1` confirmou servidor local e URL pública.
- `Instalar-Tudo.ps1 -Sim -SemAutostart` completou configuração, subida,
  Tailscale e diagnóstico.
- `Ver-Credenciais.ps1` (sem `-Revelar`) mostrou URL/usuário.
- `Manter-Acordado.ps1` **não foi executado** (decisão do Marlon).

### 2026-11-16 — Fase 4

- Teste final via **HTTPS + WSS** (`wss://marlon-dell-pc.tail6ded59.ts.net:8443/api/ws`):
  - login 200, ws-ticket 200, `gateway.ready` recebido.
  - `session.create` → modelo `deepseek-v4.1-flash`.
  - `prompt.submit` → `message.complete status=complete`, texto `OK`.
- `Ver-Credenciais.ps1 -Revelar` retornou senha de **32 caracteres**
  (valor não registrado em log).
- ACL do `secrets.json`: somente `DESKTOP-P05PR2E\Marlon:(F)`.
- Tarefa `Hermes Mobile - Servidor`: estado `Running`.
- `tailscale serve status`: `:443 → 28894` e `:8443 → 9119`.
- Verificação de segredos: `git grep -F -f <padrões>` em `Hermes-Mobile`
  → **nenhum segredo encontrado**.
- `git ls-files Hermes-Mobile` → nenhum `.env`/`secret`/cookie versionado.
- `Status-Diagnostico.ps1 -SalvarEmLog` executado com sucesso.
- **Pendente (humano):** instalar o Pomelu no celular e conectar.

---

## 5. Webapp / gateway (2026-11-17)

- Webapp oficial habilitado em `:8444` (gateway `127.0.0.1:9120`).
- Gateway instalado como login item (`Hermes_Gateway.vbs`).
- `HERMES_WEBAPP_DIST` aponta para `%LOCALAPPDATA%\HermesMobile\webapp-dist`.
- Login público 200; HTML com `__HERMES_UI_SURFACE__`; `/login` 200.
- **Mono Hermes:** aviso de versão (UI 0.22.0 vs servidor 0.23.1) — informativo.
- **Pomelu:** conectado; chat/sessões via `:8443`.

## 6. Problemas conhecidos

| Problema | Impacto | Contorno |
|---|---|---|
| `install out of sync` | cosmético | não atualizar sem backup |
| Webapp renderer copiado | manutenção | `Configurar-Webapp.ps1 -Forcar` após update |
| Mono Hermes 0.22 vs 0.23 | aviso de versão | usar Webapp `:8444` ou ignorar |
| PC dorme | perde acesso | manter na tomada / `Manter-Acordado.ps1` |
| Celular em doze | timeout inicial | Tailscale sem restrição de bateria |
