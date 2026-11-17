# 11 — Backlog e ideias

Última atualização: **2026-11-16**

> Ideias e tarefas que **não** serão implementadas agora.
> Não executar sem aprovação do Marlon.

---

## 1. Plugin Pomelu de push

**O que é:** plugin oficial do app para o Hermes que:

- entrega mensagens de cron no chat do bot;
- envia push quando o app está fechado;
- registra o celular em `%LOCALAPPDATA%\hermes\pomelu\devices.json`.

**Instalação:**

```powershell
hermes plugins install ateymoori/pomelu-hermes-plugin --enable
hermes pomelu setup
# reiniciar o hermes serve
```

**Prós:** notificações reais com o app fechado; cron entrega no app.

**Contras:** relay de terceiros (Royan AB), projeto novo (1 star), mais uma
superfície de segurança.

**Decisão:** backlog (16/11/2026).

---

## 2. Telegram como canal secundário

**O que é:** usar o gateway nativo do Hermes para Telegram.

**Passos:**

1. Criar bot no `@BotFather`.
2. `hermes gateway setup` → Telegram.
3. `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ALLOWED_USERS` no `.env`.
4. `hermes gateway start`.

**Prós:** funciona sem Tailscale; notificações; voz; ótimo para emergência.

**Contras:** mensagens passam pelo Telegram; não é a UI completa.

**Decisão:** backlog.

---

## 3. PWA / webapp oficial (se o bundle aparecer)

- A instalação da Store não traz `apps/desktop/dist-webapp`.
- Se uma atualização futura incluir, reavaliar `hermes webapp` + PWA.
- Workaround atual (copiar renderer) foi descartado.

---

## 4. Hermes-Android / Mono Hermes

- Alternativas se o Pomelu falhar.
- Hermes-Android precisa do webapp oficial; Mono Hermes usa `hermes serve`.
- Testar em uma sessão futura.

---

## 5. Manter o PC acordado

- O projeto **não** altera energia (decisão do Marlon).
- `Manter-Acordado.ps1` existe para uso manual.
- Ideia: agendar tarefa que só ativa na tomada.

---

## 6. QR code da URL no terminal

- Gerar um QR com a URL `https://...:8443` (sem senha) para abrir no celular.
- Poderia usar Python `qrcode` ou um gerador local.
- Cuidado: não incluir credenciais no QR.

---

## 7. Múltiplos perfis/bots

- O Pomelu lista todos os perfis do Hermes.
- Documentar como criar/renomear bots.
- Verificar se o `hermes serve` multiplexa todos os perfis.

---

## 8. Health check agendado

- Tarefa a cada 15 min que testa `/api/status`.
- Se falhar, reinicia o `hermes serve` e/ou notifica.
- Cuidado para não brigar com o autostart.

---

## 9. Backup do `.env` e das credenciais

- Incluir no backup geral do Hermes.
- Nunca versionar.
- Testar restauração em uma home temporária.

---

## 10. Domínio próprio / HTTPS público

- **Não recomendado** para este projeto.
- Exigiria OAuth/OIDC e superfície pública.
- Tailscale já resolve.

---

## 11. Tailscale Funnel

- **Rejeitado.** Expõe à internet. Não usar.

---

## 12. Atualização automática do Pomelu

- Play Store já atualiza.
- APK GitHub: usar Obtainium.
- Documentar.

---

## 13. Logs e métricas

- O `hermes serve` grava em `%LOCALAPPDATA%\hermes\logs`.
- O projeto grava `logs\servidor-*.log`.
- Ideia: rotação e limpeza automática.

---

## 14. Testar o Desktop coexistindo

- Abrir o Hermes Desktop com o `hermes serve` do projeto rodando.
- Verificar se compartilham sessões.
- Documentar.

---

## 15. Senha por dispositivo / múltiplos usuários

- Hoje há um usuário `hermes` compartilhado.
- O Hermes básico não tem contas por usuário.
- Se precisar, avaliar OAuth/OIDC (fora do escopo).
