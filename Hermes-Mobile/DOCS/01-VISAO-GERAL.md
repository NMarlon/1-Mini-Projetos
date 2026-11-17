# 01 — Visão geral

Última atualização: **2026-11-16**

---

## 1. Objetivo

Usar o **Hermes Agent** que roda no PC Windows do Marlon a partir do
**celular Android (Galaxy A32)**, com acesso privado pelo **Tailscale**.

O cliente escolhido é o **Pomelu**, um app Android/iOS open-source feito
especificamente para Hermes. Ele fala o protocolo do `hermes serve`
(REST + JSON-RPC/WebSocket) e oferece chats por bot/perfil, aprovações,
perguntas, voz, arquivos, cron e tela do bot.

## 2. Escopo

### Dentro do escopo

- Configurar autenticação do gateway do Hermes.
- Subir o `hermes serve` em `127.0.0.1:9119`.
- Publicar via Tailscale Serve HTTPS em `:8443`.
- Instalar/manter o autostart no login.
- Documentar o uso do Pomelu no celular.
- Scripts de diagnóstico, início, parada, credenciais e rollback.

### Fora do escopo

- Criar app Android próprio.
- Compilar o webapp oficial do Hermes.
- Instalar um Hermes separado no celular (Termux).
- Gerenciar modelos/providers/chaves de API.
- Abrir portas no roteador ou usar Tailscale Funnel.
- Alterar configurações de energia do PC.

## 3. Estado atual (2026-11-16)

| Item | Valor |
|---|---|
| Hermes | v0.23.1 stable (Microsoft Store/MSIX) |
| Home | `C:\Users\Marlon\AppData\Local\hermes` |
| Servidor | `hermes serve` em `127.0.0.1:9119` |
| Auth | usuário + hash scrypt + secret (via `.env`) |
| URL pública | `https://marlon-dell-pc.tail6ded59.ts.net:8443` |
| Tailscale | PC `marlon-dell-pc` (`100.76.44.54`), celular `a32-de-marlon` (`100.66.158.57`) |
| OpenCode | `https://marlon-dell-pc.tail6ded59.ts.net` (443 → 28894) |
| App | Pomelu (`se.royan.pomelu`) |
| Autostart | Tarefa Agendada no login |
| Energia | não alterada |
| Plugin Pomelu | não instalado (backlog) |

## 4. Critérios de sucesso

1. `https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status` responde JSON
   com `auth_required: true` e `auth_providers` incluindo `basic`.
2. O Pomelu conecta na URL acima, autentica e lista os bots/perfis.
3. Um prompt enviado pelo celular recebe resposta do agente no PC.
4. Uma aprovação/pergunta aparece no celular e pode ser respondida.
5. O OpenCode continua funcionando em `:443`.
6. O servidor volta sozinho após logout/login (autostart).
7. Nenhum segredo no Git; nenhuma porta pública.

## 5. Glossário

| Termo | Significado |
|---|---|
| **Hermes Agent** | Agente de IA self-hosted da Nous Research |
| **Gateway** | Processo/servidor que expõe o agente via REST + WebSocket |
| **`hermes serve`** | Backend headless do Hermes (porta 9119) |
| **Dashboard** | UI web administrativa do Hermes (mesma origem do serve) |
| **Pomelu** | App Android/iOS open-source, cliente do Hermes |
| **Bot** | Um perfil (profile) do Hermes visto como contato no Pomelu |
| **Tailscale Serve** | Proxy HTTPS privado dentro do tailnet |
| **Tailnet** | A rede privada WireGuard do Tailscale |
| **`dashboard.public_url`** | URL pública que liga o login obrigatório no loopback |
| **scrypt** | Algoritmo de hash de senha usado pelo auth básico do Hermes |

## 6. Por que não o webapp oficial

A instalação da Microsoft Store **não inclui** o bundle
`apps/desktop/dist-webapp`. O comando `hermes webapp` tentaria compilar o
renderer a partir de um código-fonte que também não está presente. O Pomelu
não depende desse bundle: ele usa a API do `hermes serve`.

Detalhes em [`09-ERROS-E-APRENDIZADOS.md`](09-ERROS-E-APRENDIZADOS.md).

## 7. Por que não Termux

Termux instalaria **outro Hermes** no celular, com outra home, outros
arquivos e outras sessões. O objetivo é usar o agente **do PC**, com os
projetos e arquivos que já estão lá. Pomelu é apenas um cliente.
