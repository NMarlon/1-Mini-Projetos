# 07 — Apps mobile (comparativo)

Última atualização: **2026-11-16**

---

## 1. Resumo

| App | Tipo | Requer | Tailscale | Notificações | Veredito |
|---|---|---|---|---|---|
| **Pomelu** | App nativo Flutter (Android/iOS) | Hermes 0.21.5+ | ✅ | ✅ (background; push com plugin) | **Escolhido** |
| Hermes Desktop Webapp | Navegador | Hermes 0.22.6+ + bundle webapp | ✅ | ❌ | Fallback (bundle ausente na Store) |
| Hermes-Android | Shell WebView do Webapp | Webapp | ✅ | ✅ | Alternativa (depende do webapp) |
| Mono Hermes | Cliente do `hermes serve` | `hermes serve` | ✅ | local | Alternativa (UI antiga) |
| Telegram | Gateway de mensageria | Token do BotFather | ❌ (internet) | ✅ | Canal secundário |
| Termux | Hermes no próprio celular | Termux | N/A | ❌ | Não é o objetivo |

## 2. Pomelu (escolhido)

- **Site:** <https://royan.se/pomelu/>
- **GitHub:** <https://github.com/ateymoori/pomelu>
- **Play Store:** <https://play.google.com/store/apps/details?id=se.royan.pomelu>
- **APK:** <https://github.com/ateymoori/pomelu/releases/latest>
- **Licença:** Apache-2.0
- **Android:** 10+
- **Protocolo:** REST + JSON-RPC/WebSocket no `hermes serve`
- **Versão testada pelo app:** Hermes 0.22.2 (mínimo 0.21.5)
- **Recursos:** chats por bot, streaming, aprovações, perguntas, voz,
  fotos/vídeos/arquivos, cron, skills, `SOUL.md`, Bot Screen, notificações.
- **Segurança:** credenciais no Android Keystore; sem conta; sem tracking.
- **Observação:** projeto de terceiros (Royan AB), não oficial da Nous.

## 3. Hermes Desktop Webapp (fallback)

- **Doc:** <https://hermes-agent.nousresearch.com/docs/user-guide/desktop>
- **Como funciona:** o gateway serve o workspace do Desktop no navegador.
- **Problema nesta máquina:** a instalação da Microsoft Store **não inclui**
  `apps/desktop/dist-webapp`; `hermes webapp` tentaria compilar e falharia.
- **Workaround possível:** copiar o renderer do app instalado e apontar
  `HERMES_WEBAPP_DIST`. Não foi adotado (complexidade).
- **Quando usar:** se uma atualização futura passar a incluir o bundle.

## 4. Hermes-Android

- **GitHub:** <https://github.com/hermes-webui/hermes-android>
- **Tipo:** shell Android (Kotlin) em volta do Webapp oficial ou do
  Hermes WebUI.
- **Requer:** o webapp oficial habilitado (mesmo problema do bundle) ou o
  Hermes WebUI separado.
- **Vantagens:** notificações nativas, compartilhamento, uploads.
- **Desvantagem:** mais uma peça (webapp/WebUI) para manter.

## 5. Mono Hermes

- **GitHub:** <https://github.com/Monoperro0207/mono-hermes>
- **Tipo:** renderer do Desktop empacotado em app Capacitor, cliente do
  `hermes serve`.
- **Vantagens:** UI idêntica ao Desktop; Tailscale.
- **Desvantagens:** projeto pequeno; UI congelada em 0.22.0; sem push.
- **Quando usar:** se o Pomelu não funcionar.

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
2. Use a mesma URL `https://marlon-dell-pc.tail6ded59.ts.net:8443`.
3. Autentique com o mesmo usuário/senha.
4. Teste conexão e um prompt.
5. Não é preciso mudar nada no PC (o servidor é o mesmo).
