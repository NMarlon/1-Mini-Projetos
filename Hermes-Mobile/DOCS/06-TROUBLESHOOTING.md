# 06 — Troubleshooting

Última atualização: **2026-11-16**

> Antes de qualquer coisa, rode:
> `powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1 -SalvarEmLog`

---

## 1. O Pomelu não conecta

### Sintoma: “Connection failed” / timeout

**Causas prováveis:**

1. Tailscale do celular desconectado.
2. PC dormindo/desligado.
3. `hermes serve` não está rodando.
4. Tailscale Serve `:8443` não está configurado.
5. URL errada no app.

**Verificar no PC:**

```powershell
tailscale status
tailscale serve status
Get-NetTCPConnection -LocalPort 9119 -State Listen
curl.exe -s http://127.0.0.1:9119/api/status
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
```

**Correção:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1
```

No celular: abrir o Tailscale e confirmar que `a32-de-marlon` aparece
conectado.

### Sintoma: “401 / Invalid credentials”

- Usuário/senha errados.
- A senha foi rotacionada e o app ainda tem a antiga.
- O `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` não confere.

**Correção:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar
```

No Pomelu, remover o servidor e adicionar de novo.

### Sintoma: “400 Host refused”

O `dashboard.public_url` não corresponde ao host usado pelo app.

- Confira o valor:
  `hermes config get dashboard.public_url`
- Deve ser exatamente
  `https://marlon-dell-pc.tail6ded59.ts.net:8443`.
- Se o nome do PC mudou, atualize e reinicie.

### Sintoma: “Gateway too old” / versão

O Pomelu exige Hermes **0.21.5+**. Confira:

```powershell
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
```

Se a versão for menor, atualize o Hermes (com backup e autorização).

### Sintoma: conecta mas o WebSocket cai

- Verifique se o Tailscale Serve está proxying WebSocket (ele suporta).
- Veja `hermes logs --since 30m`.
- Teste a URL no navegador do celular: deve aparecer a tela de login do
  dashboard.

## 2. O servidor não sobe

### Sintoma: `hermes serve` falha ao iniciar

Verifique o log:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\HermesMobile\logs" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
Get-Content <log> -Tail 80
```

Causas comuns:

| Erro | Causa | Correção |
|---|---|---|
| `auth provider required` | `dashboard.public_url` setado sem auth | Rode `Configurar-Hermes.ps1` |
| `address already in use` | Porta 9119 ocupada | Use `-Porta 9121` ou pare o processo |
| `Webapp build failed` | `--skip-build` ausente | Use `--skip-build` (o script já usa) |
| `install out of sync` | Aviso pré-existente da Store | Não impede; não rode update sem backup |

### Sintoma: porta 9119 ocupada pelo Desktop

```powershell
hermes serve --status
Get-NetTCPConnection -LocalPort 9119 -State Listen
```

- Se for o Desktop, **não mate**. Use outra porta:
  `Iniciar-Mobile.ps1 -Porta 9121` e
  `tailscale serve --bg --https=8443 http://127.0.0.1:9121`.

## 3. Tailscale Serve

### Sintoma: `Serve is not enabled on your tailnet`

O recurso Serve precisa ser aprovado uma vez no tailnet. O comando imprime
um link `https://login.tailscale.com/f/serve?...`; abra e aprove.

### Sintoma: `tailscale serve status` não mostra 8443

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1
tailscale serve status --json
```

### Sintoma: HTTPS não funciona

Fallback privado (ainda dentro do tailnet):

```powershell
tailscale serve --bg --http=8443 http://127.0.0.1:9119
```

A URL fica `http://marlon-dell-pc.tail6ded59.ts.net:8443` (sem TLS). O
Pomelu aceita, mas o microfone/PWA podem não funcionar. Prefira HTTPS.

### Sintoma: o 443 do OpenCode quebrou

```powershell
tailscale serve status
```

Deve mostrar `:443 → 127.0.0.1:28894`. Se não, restaure pelo projeto do
OpenCode (`Iniciar-Mobile.ps1` de lá) ou rode:

```powershell
tailscale serve --bg --https=443 http://127.0.0.1:28894
```

**Nunca** rode `tailscale serve reset` sem entender o que será removido.

## 4. Autostart

### Sintoma: após reiniciar, o Pomelu não conecta

```powershell
Get-ScheduledTask -TaskName "Hermes Mobile - Servidor"
Get-ScheduledTaskInfo -TaskName "Hermes Mobile - Servidor"
```

- `State` deve ser `Ready`/`Running`.
- Veja o log em `%LOCALAPPDATA%\HermesMobile\logs\`.
- Rode `Instalar-Autostart.ps1` de novo se a tarefa sumiu.

### Sintoma: a tarefa roda mas o servidor não sobe

- O caminho da pasta mudou? Reinstale o autostart.
- O `hermes` não está no PATH do usuário? Use o caminho absoluto do
  `hermes.exe` no script.
- Veja o log do `Iniciar-Servidor.ps1`.

## 5. PC dormindo

Se o PC suspender, o celular perde o acesso. O projeto **não altera energia**
(REGRA 14). Opções:

- Manter o PC na tomada e configurar o Windows manualmente.
- Rodar `Manter-Acordado.ps1 -Ativar` **somente com autorização**.

## 6. Hermes atualizado

Após atualizar o Hermes:

1. `Status-Diagnostico.ps1`
2. Testar `/api/status` e login.
3. Se o Pomelu recusar a versão, veja se há atualização do app.
4. Se o protocolo mudou, registre em `09-ERROS-E-APRENDIZADOS.md`.

## 7. Logs úteis

```powershell
hermes logs --since 1h
hermes logs errors
Get-Content "$env:LOCALAPPDATA\HermesMobile\logs\servidor-*.log" -Tail 100
```

## 8. Reset de emergência

```powershell
# Parar só o servidor deste projeto
powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1

# Remover o handler 8443
tailscale serve --https=8443 off

# Reconfigurar tudo
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1
```
