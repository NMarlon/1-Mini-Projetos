# 07 — Apps mobile (comparativo)

Última atualização: **2026-11-17**

---

## 1. Resumo

| App | Tipo | Requer | Tailscale | Notificações | Veredito |
|---|---|---|---|---|---|
| **Pomelu** | App nativo Flutter (Android/iOS) | Hermes 0.21.5+ | ✅ | ✅ (background; push com plugin) | **Chat rápido**; só perfis, não lista sessões/projetos |
| **Webapp oficial** | Navegador/PWA | renderer copiado + gateway 9120 | ✅ | ❌ | **Workspace completo** em `:8444` |
| Hermes-Android | Shell WebView do Webapp | Webapp `:8444` | ✅ | ✅ | Opcional; usa o Webapp |
| Mono Hermes | Cliente do `hermes serve` | `hermes serve` | ✅ | local | Sessões/histórico; **aviso de versão** (0.22 vs 0.23) |
| Telegram | Gateway de mensageria | Token do BotFather | ❌ (internet) | ✅ | Canal secundário |
| Termux | Hermes no próprio celular | Termux | N/A | ❌ | Não é o objetivo |

## 2. Pomelu (chat rápido)

- **Site:** <https://royan.se/pomelu/>
- **GitHub:** <https://github.com/ateymoori/pomelu>
- **Play Store:** <https://play.google.com/store/apps/details?id=se.royan.pomelu>
- **APK:** <https://github.com/ateymoori/pomelu/releases/latest>
- **Licença:** Apache-2.0
- **Android:** 10+
- **Protocolo:** REST + JSON-RPC/WebSocket no `hermes serve`
- **Versão testada pelo app:** Hermes 0.22.2 (mínimo 0.21.5)
- **Organização:** um chat por **perfil/bot**; não lista as sessões nem os
  projetos existentes do Desktop. É messenger-style de propósito.
- **Recursos:** chats por bot, streaming, aprovações, perguntas, voz,
  fotos/vídeos/arquivos, cron, skills, `SOUL.md`, Bot Screen, notificações.
- **Segurança:** credenciais no Android Keystore; sem conta; sem tracking.
- **Observação:** projeto de terceiros (Royan AB), não oficial da Nous.

## 3. Webapp oficial (habilitado em `:8444`)

- **URL:** `https://marlon-dell-pc.tail6ded59.ts.net:8444`
- **Doc:** <https://hermes-agent.nousresearch.com/docs/user-guide/desktop>
- **Como funciona:** o gateway serve o workspace do Desktop no navegador.
- **Nesta máquina:** a instalação da Store não inclui
  `apps/desktop/dist-webapp`; o projeto copia o renderer do app instalado
  (`app.asar.unpacked\dist`) para
  `%LOCALAPPDATA%\HermesMobile\webapp-dist` e aponta `HERMES_WEBAPP_DIST`.
- **Resultado:** sessões, projetos, arquivos, Git e terminal no navegador,
  alinhado ao servidor 0.23.1.
- **Manutenção:** após atualizar o Hermes, rodar
  `Configurar-Webapp.ps1 -Forcar`.
- **Quando usar:** quando precisar de projetos/arquivos/Git/terminal.

## 4. Hermes-Android

- **GitHub:** <https://github.com/hermes-webui/hermes-android>
- **Tipo:** shell Android (Kotlin) em volta do Webapp oficial ou do
  Hermes WebUI.
- **Requer:** o Webapp habilitado em `:8444` (já está) ou o Hermes WebUI.
- **Vantagens:** notificações nativas, compartilhamento, uploads.
- **Desvantagem:** mais uma peça (webapp/WebUI) para manter.
- **Uso:** instalar o APK e apontar para `https://...:8444`.

## 5. Mono Hermes

- **GitHub:** <https://github.com/Monoperro0207/mono-hermes>
- **Release:** <https://github.com/Monoperro0207/mono-hermes/releases/latest>
- **APK v0.4.0:** <https://github.com/Monoperro0207/mono-hermes/releases/download/v0.4.0/mono-hermes-0.4.0-release.apk>
- **Tipo:** renderer do Desktop empacotado em app Capacitor, cliente do
  `hermes serve`.
- **Vantagens:** UI idêntica ao Desktop; sessões/histórico; Tailscale.
- **Desvantagens:** projeto pequeno; UI congelada em **0.22.0**; sem push;
  **aviso de versão** no servidor 0.23.1 (informativo).
- **Quando usar:** se quiser uma UI nativa de sessões; para o workspace
  completo, use o Webapp `:8444`.

## 6. Telegram

- **Gateway nativo do Hermes:** `hermes gateway setup` → Telegram.
- **Vantagens:** funciona em qualquer lugar; notificações; voz; sem app
  extra; não depende do Tailscale.
- **Desvantagens:** mensagens passam pelos servidores do Telegram; não é a
  UI completa do Hermes.
- **Quando usar:** canal secundário / emergência.

## 7. Termux

- **Doc:** <https://hermes-agent.nousresearch.com/docs/getting-started/termux>
- **O que é:** instalar o Hermes no próprio Android (arm64).
- **Por que não:** seria outro agente, outra home, outros arquivos; não usa
  o Hermes do PC.
- **Quando usar:** se quiser um agente local no celular, sem PC.

## 8. Como trocar de app

1. Instale o novo cliente.
2. Use a URL adequada:
   - **Pomelu / Mono Hermes:** `https://marlon-dell-pc.tail6ded59.ts.net:8443`
   - **Webapp / Hermes-Android:** `https://marlon-dell-pc.tail6ded59.ts.net:8444`
3. Autentique com o mesmo usuário/senha.
4. Teste conexão e um prompt.
5. Não é preciso mudar nada no PC (os servidores são os mesmos).
