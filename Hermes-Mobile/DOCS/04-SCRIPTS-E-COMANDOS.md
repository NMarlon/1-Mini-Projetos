# 04 — Scripts e comandos

Última atualização: **2026-11-17**

Todos os scripts ficam em `scripts/` e são compatíveis com **PowerShell 5.1**.
Nunca use `pwsh` nem recursos do PowerShell 7.

---

## 1. Visão geral

| Script | O que faz | Quando usar |
|---|---|---|
| `Instalar-Tudo.ps1` | Configura auth + servidor + Tailscale + autostart | Primeira instalação ou PC novo |
| `Configurar-Hermes.ps1` | Gera credenciais e define `dashboard.public_url` | Reconfigurar auth |
| `Configurar-Tailscale.ps1` | Cria/remove o handler `:8443` | Publicar ou reverter |
| `Configurar-Webapp.ps1` | Copia o renderer e liga o Webapp em `:9120`/`:8444` | Workspace completo (projetos/arquivos/Git/terminal) |
| `Iniciar-Servidor.ps1` | Garante o `hermes serve` (background ou `-Foreground`) | Chamado pelo `Iniciar-Mobile` e pela Tarefa Agendada |
| `Iniciar-Mobile.ps1` | Garante servidor + Tailscale e mostra URL | Dia a dia |
| `Parar-Mobile.ps1` | Para o servidor e remove o handler | Manutenção |
| `Instalar-Autostart.ps1` | Tarefa Agendada no login + atalho | Quer acesso após reiniciar |
| `Remover-Autostart.ps1` | Remove a Tarefa Agendada/atalho | Desfazer autostart |
| `Ver-Credenciais.ps1` | Mostra URL/usuário e senha com `-Revelar` | Configurar o celular |
| `Status-Diagnostico.ps1` | Diagnóstico completo, somente leitura | Antes de qualquer mudança |
| `Manter-Acordado.ps1` | Opcional: evita suspensão na tomada | Só se o Marlon pedir |

## 2. `Instalar-Tudo.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1
```

Parâmetros:

| Parâmetro | Efeito |
|---|---|
| `-Sim` | Não faz perguntas; assume “sim” nas etapas seguras |
| `-SemAutostart` | Não instala a Tarefa Agendada |
| `-Porta 9119` | Porta local do `hermes serve` |
| `-UrlPublica <url>` | Sobrescreve a URL do tailnet detectada |

O script é **idempotente**: pode rodar de novo sem duplicar variáveis no
`.env` (ele remove as antigas antes de gravar).

## 3. `Configurar-Hermes.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Hermes.ps1
```

O que faz:

1. Detecta a home do Hermes e a URL do tailnet.
2. Faz backup do `.env` em `%LOCALAPPDATA%\HermesMobile\backups\`.
3. Gera senha forte (32+ chars) e secret (32 bytes) com
   `System.Security.Cryptography`.
4. Calcula o hash scrypt usando o Python do próprio Hermes.
5. Remove linhas antigas `HERMES_DASHBOARD_BASIC_AUTH_*` do `.env`.
6. Grava usuário, hash, secret e TTL.
7. Salva a senha em `%LOCALAPPDATA%\HermesMobile\secrets.json` com ACL.
8. Define `dashboard.public_url` via `hermes config set`.

Parâmetros:

| Parâmetro | Efeito |
|---|---|
| `-Usuario hermes` | Usuário do gateway |
| `-Senha <texto>` | Usa uma senha específica em vez de gerar |
| `-TtlDias 7` | Validade da sessão (padrão: 7) |
| `-UrlPublica <url>` | URL pública |
| `-Revelar` | Mostra a senha no console ao final |

> A senha **não** é impressa por padrão. Use `Ver-Credenciais.ps1 -Revelar`.

## 4. `Configurar-Tailscale.ps1`

```powershell
# Criar/garantir
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1

# Remover somente o 8443
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1 -Remover
```

O script:

- Verifica se o Tailscale está instalado/logado.
- Detecta o DNS name do PC.
- Cria `tailscale serve --bg --https=8443 http://127.0.0.1:9119`.
- Confere no `tailscale serve status --json` que **443 → 28894** continua
  intacto.
- Se o HTTPS falhar, tenta `--http=8443` e avisa.

## 5. `Iniciar-Servidor.ps1`

```powershell
# Background (dia a dia; o Iniciar-Mobile chama este)
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1

# Outra porta
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1 -Porta 9121

# Foreground (usado pela Tarefa Agendada)
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1 -Foreground
```

- Se já existe um `hermes serve` na porta, não sobe outro.
- Se a porta estiver ocupada por outro processo, **não** mata; pede para
  usar `-Porta`.
- No modo background, gera um VBS em
  `%LOCALAPPDATA%\HermesMobile\Iniciar-HermesServe-<porta>.vbs` e o executa
  destacado (sem segurar o terminal).
- No modo `-Foreground`, roda `hermes serve` no processo atual e grava o log
  em `logs/task-servidor-<data>.log`. É o modo da Tarefa Agendada.

## 6. `Iniciar-Mobile.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1
```

O que faz:

1. Chama `Iniciar-Servidor.ps1`.
2. Chama `Configurar-Tailscale.ps1`.
3. Verifica `/api/status` local e via HTTPS.
4. Mostra URL e como obter as credenciais.
5. Se o webapp estiver habilitado, checa `:9120` e mostra a URL `:8444`.

Opções: `-Porta`, `-PortaPublica`, `-SemTailscale`, `-AbrirNavegador`.

## 7. `Parar-Mobile.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1
```

- Identifica o processo que escuta em 9119.
- Verifica se a linha de comando é do `hermes serve` **deste projeto**.
- Para **somente** esse PID.
- Remove o handler `:8443` (opcional; por padrão mantém).
- **Nunca** roda `hermes serve --stop` (que pararia o Desktop também).
- O gateway/webapp em `:9120` continua; use `-PararGateway` para parar também.

## 8. `Instalar-Autostart.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Autostart.ps1
```

Cria a Tarefa Agendada **`Hermes Mobile - Servidor`**:

- Gatilho: logon do usuário atual.
- Ação: `powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "<pasta>\scripts\Iniciar-Servidor.ps1" -Porta 9119 -Foreground`.
- Sem limite de tempo; reinicia em caso de falha.
- Log da tarefa: `logs/task-servidor-<data>.log`.
- Roda com o usuário atual (sem UAC/admin).

Se o Task Scheduler recusar, o script cria um fallback na pasta Startup
(atalho para um VBS) e avisa. O `Remover-Autostart.ps1` limpa os dois.

Também cria um atalho **“Hermes Mobile”** na área de trabalho que abre a URL
do tailnet no navegador.

## 9. `Remover-Autostart.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Remover-Autostart.ps1
```

Remove a Tarefa Agendada e o atalho. Não para o servidor em execução.

## 10. `Ver-Credenciais.ps1`

```powershell
# Mostra URL e usuário; senha oculta
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1

# Mostra a senha
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar

# Copia a senha para a área de transferência
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar -Copiar
```

Lê `%LOCALAPPDATA%\HermesMobile\secrets.json`.

## 11. `Status-Diagnostico.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1 -SalvarEmLog
```

Checa:

1. Versão/instalação do Hermes (inclui o aviso `install out of sync`).
2. `dashboard.public_url`.
3. Variáveis de auth no `.env` (sem imprimir valores).
4. Processo/porta 9119.
5. `/api/status` local (código HTTP + JSON resumido).
6. Tailscale + `serve status --json` (443 e 8443).
7. `/api/status` via HTTPS do tailnet.
8. Firewall (somente leitura).
9. Tarefa Agendada.
10. Webapp (config, `HERMES_WEBAPP_DIST`, 9120, 8444, login).
11. Salva log em `logs/` se `-SalvarEmLog`.

## 12. `Manter-Acordado.ps1`

**Opcional. Não rodar sem pedido do Marlon (REGRA 14).**

```powershell
# Evitar suspensão/hibernação somente na tomada
powershell -ExecutionPolicy Bypass -File .\scripts\Manter-Acordado.ps1 -Ativar

# Reverter
powershell -ExecutionPolicy Bypass -File .\scripts\Manter-Acordado.ps1 -Reverter
```

Backup em `%LOCALAPPDATA%\HermesMobile\energia-backup.json`.

## 14. `Configurar-Webapp.ps1`

```powershell
# Copiar/atualizar e ligar o webapp
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1

# Forçar recópia do renderer (após atualizar o Hermes)
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1 -Forcar
```

O que faz:

1. Localiza `app.asar.unpacked\dist` na instalação MSIX.
2. Copia para `%LOCALAPPDATA%\HermesMobile\webapp-dist` (robocopy /MIR).
3. Grava `HERMES_WEBAPP_DIST` no `.env`.
4. Liga `webapp.enabled` no gateway (`127.0.0.1:9120`) e define
   `webapp.public_url` para `https://<pc>.<tailnet>.ts.net:8444`.
5. Reinicia o gateway e aguarda `/api/status`.
6. Publica `tailscale serve --https=8444 http://127.0.0.1:9120`.
7. Testa local e público.

O Pomelu continua no `:8443`; o webapp usa `:8444`.

## 15. Comandos úteis (sem script)

```powershell
# Ver status do servidor
hermes serve --status

# Ver config efetiva
hermes config get dashboard.public_url
hermes config get dashboard.basic_auth

# Ver handlers do Tailscale
tailscale serve status
tailscale serve status --json

# Testar saúde local
curl.exe -s http://127.0.0.1:9119/api/status

# Testar saúde pública
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status

# Ver processos/porta
Get-NetTCPConnection -LocalPort 9119 -State Listen
Get-Process -Id <pid>

# Logs do Hermes
hermes logs --since 1h
```

> No PowerShell 5.1, `curl` é alias de `Invoke-WebRequest`. Use sempre
> `curl.exe`.
