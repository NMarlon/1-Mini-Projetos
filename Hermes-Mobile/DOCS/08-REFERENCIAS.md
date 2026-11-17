# 08 — Referências

Última atualização: **2026-11-17**

---

## 1. Hermes Agent

| Recurso | Link |
|---|---|
| Repositório | <https://github.com/NousResearch/hermes-agent> |
| Documentação | <https://hermes-agent.nousresearch.com/docs/> |
| Quickstart | <https://hermes-agent.nousresearch.com/docs/getting-started/quickstart> |
| Instalação | <https://hermes-agent.nousresearch.com/docs/getting-started/installation> |
| Desktop / Webapp | <https://hermes-agent.nousresearch.com/docs/user-guide/desktop> |
| Web Dashboard / auth | <https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard> |
| Termux (Android) | <https://hermes-agent.nousresearch.com/docs/getting-started/termux> |

## 2. Pomelu

| Recurso | Link |
|---|---|
| GitHub | <https://github.com/ateymoori/pomelu> |
| Site | <https://royan.se/pomelu/> |
| Play Store | <https://play.google.com/store/apps/details?id=se.royan.pomelu> |
| Releases/APK | <https://github.com/ateymoori/pomelu/releases/latest> |
| Protocolo | <https://github.com/ateymoori/pomelu/blob/main/docs/PROTOCOL.md> |
| Arquitetura | <https://github.com/ateymoori/pomelu/blob/main/docs/ARCHITECTURE.md> |
| Plugin de push | <https://github.com/ateymoori/pomelu-hermes-plugin> |

## 3. Alternativas

| App | Link |
|---|---|
| Hermes-Android | <https://github.com/hermes-webui/hermes-android> |
| Mono Hermes | <https://github.com/Monoperro0207/mono-hermes> |
| Hermes WebUI (comunidade) | <https://github.com/nesquena/hermes-webui> |

## 4. Tailscale

| Recurso | Link |
|---|---|
| Serve | <https://tailscale.com/kb/1247/funnel-serve-use-cases> |
| CLI serve | <https://tailscale.com/docs/reference/tailscale-cli/serve> |
| Admin console | <https://login.tailscale.com/admin/machines> |
| Download | <https://tailscale.com/download> |

## 5. Versões desta máquina (2026-11-16)

| Componente | Versão |
|---|---|
| Windows | 11 Pro (Dell Latitude 5440) |
| Hermes Agent | 0.23.1 stable (Microsoft Store/MSIX) |
| Python do Hermes | 3.14.9 |
| Tailscale | 1.104.6 |
| PowerShell | 5.1 |
| Celular | Galaxy A32 (Android 10+) |
| Pomelu | versão da Play Store/GitHub (verificar no app) |

## 6. Endpoints do protocolo (Pomelu)

| Uso | Endpoint |
|---|---|
| Status público | `GET /api/status` |
| Providers de auth | `GET /api/auth/providers` |
| Login | `POST /auth/password-login` |
| Refresh | `POST /auth/native/refresh` |
| Ticket do WebSocket | `POST /api/auth/ws-ticket` |
| WebSocket | `WS /api/ws` |
| Perfis/bots | `POST` JSON-RPC `profiles.list` |
| Sessões | REST `/api/sessions` + JSON-RPC |

Referência completa: `docs/PROTOCOL.md` do Pomelu.

## 7. Notas importantes

- O Pomelu foi checado contra **Hermes 0.22.2**; nossa versão é **0.23.1**.
  Testar `/api/status` e o handshake após qualquer atualização.
- O Hermes da Microsoft Store emite o aviso `install out of sync`; é
  pré-existente e não impede o uso. Não atualizar sem backup (REGRA 13).
- O webapp oficial não está empacotado nesta instalação (ver
  `09-ERROS-E-APRENDIZADOS.md`).
