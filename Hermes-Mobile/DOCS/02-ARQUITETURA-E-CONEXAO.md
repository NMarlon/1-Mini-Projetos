# 02 — Arquitetura e conexão

Última atualização: **2026-11-17**

---

## 1. Diagrama final

```text
┌──────────────────────────────────────────────┐
│  Galaxy A32 (Android 10+)                    │
│  ├─ Tailscale ligado                         │
│  ├─ Pomelu / Mono Hermes  → :8443            │
│  └─ Chrome / Hermes-Android → :8444 (webapp) │
└───────────────────┬──────────────────────────┘
                    │ Tailnet WireGuard + HTTPS
                    ▼
┌──────────────────────────────────────────────┐
│  PC Windows 11 — marlon-dell-pc               │
│                                              │
│  Tailscale Serve :443  → 127.0.0.1:28894     │  ← OpenCode
│  Tailscale Serve :8443 → 127.0.0.1:9119      │  ← hermes serve
│  Tailscale Serve :8444 → 127.0.0.1:9120      │  ← gateway/webapp
│                                              │
│  hermes serve (127.0.0.1:9119)               │
│  gateway      (127.0.0.1:9120)               │
│  └─ webapp = renderer copiado do app 0.23.1  │
└──────────────────────────────────────────────┘
```

## 2. Componentes (de baixo para cima)

1. **Hermes Agent v0.23.1** — CLI + agent core.
   Home: `%LOCALAPPDATA%\hermes`.
2. **`hermes serve`** — backend headless. Bind `127.0.0.1:9119`.
   Expõe REST e WebSocket; é o mesmo backend que o Desktop usa.
3. **Tailscale daemon** — v1.104.6. PC `marlon-dell-pc`
   (`100.76.44.54`); celular `a32-de-marlon` (`100.66.158.57`).
4. **Tailscale Serve** — HTTPS no tailnet:
   - `:443` → `127.0.0.1:28894` (OpenCode, existente).
   - `:8443` → `127.0.0.1:9119` (Hermes, novo).
5. **Pomelu** — app Flutter. Fala REST + JSON-RPC/WebSocket com o gateway.
   Guarda credenciais no Android Keystore.
6. **Gateway/Webapp** — processo do gateway em `127.0.0.1:9120`.
   Serve o renderer do Desktop copiado do app instalado (v0.23.1) com
   `HERMES_WEBAPP_DIST`; o Tailscale Serve publica em `:8444`.
   É o workspace completo: sessões, projetos, arquivos, Git e terminal.

## 3. Fluxo de dados

```text
Usuário escreve no Pomelu
  → app envia JSON-RPC via WSS /api/ws (ou REST /api/...)
  → Tailscale cifra e entrega ao PC
  → Tailscale Serve termina TLS e proxia para 127.0.0.1:9119
  → hermes serve valida o token/sessão
  → agente executa ferramentas no PC (terminal, arquivos, web...)
  → eventos de streaming voltam pelo mesmo WebSocket
  → Pomelu mostra resposta, aprovações, perguntas e anexos
```

## 4. Segurança por camada

| Camada | Proteção |
|---|---|
| Rota | Tailnet privado (WireGuard); só dispositivos da conta |
| Transporte | TLS 1.3 + certificado `*.ts.net` do Tailscale |
| Bind | Hermes escuta **somente** `127.0.0.1` |
| Auth | `dashboard.basic_auth` (usuário + hash scrypt + secret) |
| Gate | `dashboard.public_url` liga o login mesmo em loopback |
| Sessão | Token de acesso + refresh; Pomelu renova sozinho |
| App | Credenciais no Android Keystore |
| Webapp | Mesmo auth do gateway; `webapp.public_url` liga o gate; renderer copiado com hash no manifesto |
| Internet pública | **zero** — sem Funnel, sem porta no roteador |

## 5. ADRs (decisões técnicas)

### ADR-001 — Cliente principal: Pomelu
- **Decisão:** usar o Pomelu como app Android.
- **Alternativas descartadas:**
  - **Webapp oficial do Hermes:** bundle ausente na instalação da Store.
  - **Hermes-Android/Mono Hermes:** dependem do webapp ou de renderer
    específico; mais peças para manter.
  - **Telegram:** ótimo canal, mas não é a interface completa do Hermes.
  - **Termux:** seria outro Hermes no celular, não o do PC.
- **Por quê:** app nativo, open-source, Play Store, protocolo oficial,
  Tailscale-friendly, Keystore, notificações, voz e arquivos.

### ADR-002 — `hermes serve` em `127.0.0.1:9119`
- **Decisão:** rodar o backend headless, não o `hermes dashboard` em
  `0.0.0.0`.
- **Por quê:** é o backend que o Pomelu documenta; mantém o serviço em
  loopback; o Tailscale Serve faz a exposição.
- **Alternativa:** `hermes dashboard --host 127.0.0.1 --port 9119 --no-open`
  (mesma API) se o `hermes serve` apresentar problema.

### ADR-003 — Tailscale Serve em `:8443`, não `:443`
- **Decisão:** Hermes em 8443; OpenCode continua em 443.
- **Por quê:** o 443 já pertence ao OpenCode. Não há motivo para mexer.
- **Fallback:** `--http=8443` (HTTP privado no tailnet) se o HTTPS falhar.

### ADR-004 — `dashboard.public_url` para ligar o gate
- **Decisão:** definir `dashboard.public_url` com a URL do tailnet.
- **Por quê:** em loopback o Hermes não exige login por padrão. O
  `public_url` com host não-loopback liga o gate mesmo em `127.0.0.1`.
- **Consequência:** a ordem importa — **auth primeiro, servidor depois**.

### ADR-005 — Auth básica com hash scrypt + secret
- **Decisão:** `HERMES_DASHBOARD_BASIC_AUTH_USERNAME`,
  `_PASSWORD_HASH` (scrypt) e `_SECRET` no `.env`.
- **Por quê:** não deixa senha em texto no `config.yaml`; sessions
  sobrevivem a restart; é o provider recomendado para VPN/tailnet.
- **Alternativa:** `_PASSWORD` em texto (mais simples, menos seguro).

### ADR-006 — Sem `0.0.0.0` e sem Funnel
- **Decisão:** nunca bind público, nunca Funnel.
- **Por quê:** o Tailscale Serve já resolve o acesso remoto. Bind público
  exporia o gateway à LAN; Funnel exporia à internet.

### ADR-007 — Não alterar energia
- **Decisão:** não mexer em suspensão/hibernação.
- **Por quê:** decisão do Marlon em 16/11/2026. O script
  `Manter-Acordado.ps1` existe, mas é opcional e manual.
- **Limitação:** se o PC dormir, o celular perde o acesso até acordar.

### ADR-008 — Webapp oficial habilitado via cópia do renderer
- **Decisão:** copiar `app.asar.unpacked\dist` do app instalado para
  `%LOCALAPPDATA%\HermesMobile\webapp-dist`, apontar `HERMES_WEBAPP_DIST`
  e servir no gateway `127.0.0.1:9120` (Tailscale `:8444`).
- **Por quê:** a instalação MSIX não traz `apps/desktop/dist-webapp` nem o
  código-fonte. O renderer do Desktop é o mesmo produto e funciona no
  navegador quando o gateway injeta `window.__HERMES_UI_SURFACE__`.
- **Resultado:** workspace completo (sessões, projetos, arquivos, Git,
  terminal) alinhado ao servidor 0.23.1.
- **Manutenção:** após atualizar o Hermes, rodar
  `Configurar-Webapp.ps1 -Forcar` para recopiar o renderer.
- **Alternativas descartadas:** compilar `apps/desktop` do zero (sem fonte
  na Store) ou instalar o Hermes WebUI separado (mais peças).

### ADR-009 — Não usar Termux
- **Decisão:** não instalar Hermes no celular.
- **Por quê:** seria um agente separado, sem os arquivos/sessões do PC.

### ADR-010 — Plugin Pomelu de push fica no backlog
- **Decisão:** não instalar agora.
- **Por quê:** o acesso básico funciona sem ele. O plugin adiciona push via
  relay de terceiros (Royan AB), com mensagens cifradas. Requer avaliação
  de segurança e teste separado.

### ADR-011 — Gateway como login item e Webapp em 8444
- **Decisão:** instalar o gateway como item de login
  (`Startup\Hermes_Gateway.vbs`) e publicar o webapp em `:8444`.
- **Por quê:** o gateway iniciado manualmente parava quando o Desktop ou o
  terminal fechava, causando o aviso intermitente de Gateway no Desktop e no
  Mono Hermes. O login item mantém o processo estável.
- **Portas:** `:8443` continua para Pomelu/Mono Hermes; `:8444` para o webapp;
  `:443` continua OpenCode.
- **Segurança:** gateway escuta `127.0.0.1`; Tailscale Serve é tailnet-only.

## 6. Portas e endereços

| O quê | Valor |
|---|---|
| Hermes serve | `http://127.0.0.1:9119` |
| Gateway/webapp | `http://127.0.0.1:9120` |
| Tailscale Serve Hermes | `https://marlon-dell-pc.tail6ded59.ts.net:8443` |
| Tailscale Serve Webapp | `https://marlon-dell-pc.tail6ded59.ts.net:8444` |
| Tailscale Serve OpenCode | `https://marlon-dell-pc.tail6ded59.ts.net` (443) |
| IP do PC no tailnet | `100.76.44.54` |
| IP do celular | `100.66.158.57` |
| MagicDNS do PC | `marlon-dell-pc.tail6ded59.ts.net` |
| Endpoint de saúde | `/api/status` |
| Login | `POST /auth/password-login` |
| WebSocket | `/api/ws` |

## 7. Planos B

| Nº | Fallback | Quando usar |
|---|---|---|
| B-1 | `hermes dashboard --host 127.0.0.1 --port 9119 --no-open` | Se `hermes serve` não expuser as rotas do Pomelu |
| B-2 | `tailscale serve --bg --http=8443 http://127.0.0.1:9119` | Se o HTTPS do tailnet falhar |
| B-3 | Porta alternativa (ex.: 9121) | Se 9119 estiver ocupada pelo Desktop |
| B-4 | Plugin Pomelu de push | Se precisar de notificações com app fechado |
| B-5 | Telegram gateway | Canal secundário de mensagens |
| B-6 | Webapp oficial em `:8444` | Workspace completo (já habilitado) |
| B-7 | Mono Hermes (APK) | Sessões/histórico no Android; UI 0.22.0 |
| B-8 | Hermes-Android + Webapp `:8444` | Shell nativo do webapp |
