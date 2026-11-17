# 05 — Segurança

Última atualização: **2026-11-16**

---

## 1. Modelo de ameaça

O que estamos protegendo:

- Acesso ao agente (que pode executar comandos e ler arquivos do PC).
- Chaves de API dos providers (no `.env` do Hermes).
- Sessões, histórico e arquivos do usuário.
- O tailnet e o PC.

De quem:

- Qualquer pessoa na internet (não há exposição pública).
- Dispositivos na LAN (o Hermes não escuta em `0.0.0.0`).
- Outros dispositivos do tailnet (o login ainda protege).
- Alguém com acesso físico ao celular (Keystore + senha do aparelho).

## 2. Camadas de proteção

| Camada | O que faz |
|---|---|
| Tailnet | Só dispositivos da conta Tailscale do Marlon |
| WireGuard | Criptografia ponto a ponto |
| TLS `*.ts.net` | HTTPS válido no navegador/app |
| Bind loopback | Hermes só em `127.0.0.1` |
| Auth gate | `dashboard.public_url` liga o login |
| Senha | Hash **scrypt** (não texto puro) |
| Secret | Assina os tokens de sessão; 32 bytes aleatórios |
| TTL | Sessão expira (padrão 7 dias) |
| Keystore | Pomelu guarda credenciais no Android Keystore |

## 3. Onde ficam os segredos

| Segredo | Local | ACL |
|---|---|---|
| Senha do gateway (texto) | `%LOCALAPPDATA%\HermesMobile\secrets.json` | só o usuário |
| Hash da senha | `%LOCALAPPDATA%\hermes\.env` | perfil do usuário |
| Secret de assinatura | `%LOCALAPPDATA%\hermes\.env` | perfil do usuário |
| Chaves de API | `%LOCALAPPDATA%\hermes\.env` | perfil do usuário |
| Tokens de sessão | memória do processo + cookies do app | — |

**Nunca** copie esses arquivos para dentro do repositório.

## 4. Rotação de senha

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Hermes.ps1
```

Isso gera nova senha/hash/secret. Depois:

1. Reinicie o servidor (`Parar-Mobile.ps1` + `Iniciar-Mobile.ps1`).
2. No Pomelu, remova o servidor salvo e adicione de novo com a nova senha.
3. Confirme que sessões antigas foram invalidadas (o secret novo invalida).

## 5. Revogar acesso de um dispositivo

1. **Tailscale:** remova o dispositivo no admin console
   (`https://login.tailscale.com/admin/machines`). Sem tailnet, o celular
   não alcança o PC.
2. **Senha:** rotacione (seção 4). Isso invalida tokens antigos.
3. **Pomelu:** desinstale o app ou limpe os dados do app.

## 6. Checklist antes de dormir

- [ ] Nenhum segredo no `git status`.
- [ ] `tailscale serve status` mostra 443 → 28894 e 8443 → 9119.
- [ ] `tailscale funnel status` **não** mostra nada.
- [ ] Hermes escutando só em `127.0.0.1`.
- [ ] `/api/status` retorna `auth_required: true`.
- [ ] `secrets.json` com ACL só do usuário.
- [ ] OpenCode em 443 ainda funciona.

## 7. O que NUNCA fazer

- ❌ Abrir porta no roteador.
- ❌ Usar `tailscale funnel`.
- ❌ Rodar `hermes serve --host 0.0.0.0`.
- ❌ Commitar `.env`, `secrets.json`, cookies ou logs com token.
- ❌ Colar a senha em chat público, issue ou screenshot.
- ❌ Desativar o auth gate para “facilitar”.
- ❌ Instalar APK do Pomelu de site aleatório (só Play Store ou GitHub
  oficial `ateymoori/pomelu`).
- ❌ Conectar o Pomelu em HTTP público.

## 8. Plugin Pomelu (quando avaliado)

O plugin de push:

- Usa um relay Cloudflare da Royan AB.
- Cifra a mensagem com uma chave gerada no celular (AES-256-GCM).
- O relay vê o token de push e bytes cifrados, não o texto.
- Guarda dispositivos em `%LOCALAPPDATA%\hermes\pomelu\devices.json`.
- É opcional; o app funciona sem ele.

Antes de instalar, revisar o código do plugin e do relay. Está no backlog.

## 9. Referências

- Tailscale Serve: <https://tailscale.com/kb/1247/funnel-serve-use-cases>
- Hermes Web Dashboard auth:
  <https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard>
- Pomelu security: <https://github.com/ateymoori/pomelu/blob/main/SECURITY.md>
