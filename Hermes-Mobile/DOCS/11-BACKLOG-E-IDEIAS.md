# 11 — Backlog e ideias

Última atualização: **2026-11-17**

> Ideias e tarefas que **não** serão implementadas agora.
> Não executar sem aprovação do Marlon.

---

## 1. Plugin Pomelu de push

**O que é:** plugin do app para o Hermes que:

- entrega mensagens de cron no chat do bot;
- envia push quando o app está fechado;
- registra o celular em `%LOCALAPPDATA%\hermes\pomelu\devices.json`.

**Instalação:**

```powershell
hermes plugins install ateymoori/pomelu-hermes-plugin --enable
hermes pomelu setup
# reiniciar o gateway/hermes serve
```

**Prós:** notificações reais com o app fechado; cron entrega no app.

**Contras:** relay de terceiros (Royan AB), projeto novo, mais uma
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

## 3. Webapp oficial (habilitado)

- Já habilitado em `:8444` com o renderer copiado do app instalado.
- O Pomelu continua no `:8443`; o webapp é para projetos/arquivos/Git/terminal.
- **Manutenção:** após atualizar o Hermes, rodar
  `Configurar-Webapp.ps1 -Forcar` para recopiar o renderer.
- **Backlog:** testar o webapp no Hermes-Android (APK) e no PWA do Chrome.

---

## 4. Hermes-Android / Mono Hermes

- **Hermes-Android** (shell do Webapp):
  <https://github.com/hermes-webui/hermes-android>
  - apontar para `https://marlon-dell-pc.tail6ded59.ts.net:8444`.
- **Mono Hermes** (sessões/histórico):
  <https://github.com/Monoperro0207/mono-hermes>
  - apontar para `https://marlon-dell-pc.tail6ded59.ts.net:8443`.
  - **Aviso de versão:** UI 0.22.0 vs servidor 0.23.2 - informativo.
  - **Backlog:** acompanhar releases; quando sair uma versão para 0.23.x,
    atualizar.

---

## 5. Manter o PC acordado

- O projeto **não** altera energia (decisão do Marlon).
- `Manter-Acordado.ps1` existe para uso manual (somente AC).
- **Backlog:** avaliar uma regra mais forte para S0 Modern Standby, se o PC
  dormir mesmo na tomada.

---

## 6. QR code da URL no terminal

- Gerar um QR com a URL `https://...:8443` ou `:8444` (sem senha).
- Cuidado para não incluir credenciais.

---

## 7. Múltiplos perfis/bots

- O Pomelu lista todos os perfis do Hermes.
- O webapp mostra sessões/projetos por perfil.
- **Backlog:** documentar como criar/renomear bots e alternar perfis.

---

## 8. Health check / watchdog

- Tarefa a cada 5 minutos que testa `/api/status` em 80 e 9120.
- Se falhar, reinicia `hermes serve`/gateway e registra em `logs/`.
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

## 12. Atualização automática dos clientes

- Pomelu: Play Store atualiza sozinho; APK GitHub via Obtainium.
- Hermes-Android/Mono Hermes: acompanhar Releases; APK manual.
- Webapp: recopiar o renderer após atualizar o Hermes.

---

## 13. Logs e métricas

- O `hermes serve`/gateway gravam em `%LOCALAPPDATA%\hermes\logs`.
- O projeto grava `logs\task-servidor-*.log`.
- **Backlog:** rotação/limpeza automática.

---

## 14. Testar o Desktop coexistindo

- Abrir o Hermes Desktop com `hermes serve` + gateway rodando.
- Verificar se compartilham sessões e se o status do Gateway fica verde.
- Documentar em `02-ARQUITETURA-E-CONEXAO.md`.

---

## 15. Senha por dispositivo / múltiplos usuários

- Hoje há um usuário `hermes` compartilhado.
- O auth básico do Hermes não tem contas por usuário.
- Se precisar, avaliar OAuth/OIDC (fora do escopo).
