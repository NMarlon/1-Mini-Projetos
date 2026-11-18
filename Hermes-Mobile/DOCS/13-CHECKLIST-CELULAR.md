# 13 — Checklist do celular

Última atualização: **2026-11-17**

> Esta é a parte que **só o Marlon pode fazer** (instalar/autenticar no
> celular). O PC já está configurado e validado.

---

## 1. O que já está pronto no PC

- [x] Hermes v0.23.1 rodando.
- [x] `hermes serve` em `127.0.0.1:80`.
- [x] Auth básica com hash scrypt + secret.
- [x] `dashboard.public_url` configurado.
- [x] Tailscale Serve `:8443 → 127.0.0.1:80`.
- [x] Gateway/webapp em `127.0.0.1:9120` e Tailscale `:8444`.
- [x] Gateway instalado como login item (`Hermes_Gateway.vbs`).
- [x] Tailscale Serve `:443 → 127.0.0.1:28894` (OpenCode) preservado.
- [x] Tarefa Agendada `Hermes Mobile - Servidor` no login.
- [x] Modelo padrão `deepseek-v4.1-flash` (OpenCode Go) testado.
- [x] WebSocket + agente testados via HTTPS do tailnet (`OK`).
- [x] Segredos fora do Git.

## 2. No celular (Galaxy A32)

### 2.1. Tailscale

1. Abra o app **Tailscale**.
2. Confirme que está conectado com a mesma conta do PC
   (`marlonrviana@gmail.com`).
3. O dispositivo deve aparecer como `a32-de-marlon` (`100.66.158.57`).

### 2.2. Pomelu

1. Instale pela **Google Play**:
   <https://play.google.com/store/apps/details?id=se.royan.pomelu>
   - Alternativa (APK oficial):
     <https://github.com/ateymoori/pomelu/releases/latest>
2. Abra o Pomelu → **Settings**.
3. Adicione um servidor:
   - **URL:** `https://marlon-dell-pc.tail6ded59.ts.net:8443`
   - **Usuário:** `hermes`
   - **Senha:** veja no PC com
     `powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar`
4. Toque em **Test connection**.
5. Toque em **Save and connect**.

### 2.3. Teste

1. Abra o bot `default`.
2. Envie: `Responda apenas OK`.
3. Deve aparecer `OK` em alguns segundos.
4. Peça algo que exija aprovação (ex.: “liste os arquivos e proponha
   apagar um temporário”) e confirme que o card de aprovação aparece.
5. Feche e reabra o app; a sessão deve continuar.

### 2.4. Webapp completo (opcional, recomendado para projetos)

1. Abra no Chrome:
   `https://marlon-dell-pc.tail6ded59.ts.net:8444`
2. Faça login com o mesmo usuário/senha.
3. Você verá o workspace do Desktop: sessões, projetos, arquivos, Git e
   terminal.
4. Opcional: “Adicionar à tela inicial” (PWA) ou usar o **Hermes-Android**
   apontando para a mesma URL.

### 2.5. Mono Hermes (opcional)

- APK v0.4.0: <https://github.com/Monoperro0207/mono-hermes/releases/latest>
- URL: `https://marlon-dell-pc.tail6ded59.ts.net:8443`
- Mostra sessões/histórico, mas a UI é de Hermes 0.22.0; no servidor 0.23.1
  aparece um **aviso de versão informativo**.
- Para o workspace completo e alinhado, use o Webapp `:8444`.

## 3. Se não conectar

Consulte [`06-TROUBLESHOOTING.md`](06-TROUBLESHOOTING.md). Os erros mais
comuns:

| Sintoma | Causa provável | Correção rápida |
|---|---|---|
| Timeout | Tailscale do celular off / PC dormindo | Ligar Tailscale / acordar o PC |
| 401 | Senha antiga | Rotacionar/ver credenciais e reautenticar |
| 400 Host refused | `dashboard.public_url` errado | Conferir no PC |
| “Gateway too old” | Hermes < 0.21.5 | Atualizar (com backup) |
| WebSocket cai | Tailscale/rede instável | Reconectar; ver logs |
| Webapp `:8444` não abre | gateway parado | `hermes gateway start` ou `Configurar-Webapp.ps1` |
| Aviso de versão no Mono Hermes | app 0.22 vs servidor 0.23 | informativo; usar Webapp `:8444` |

## 4. Opcional: plugin de push

O Pomelu funciona sem plugin. O plugin adiciona push com o app fechado e
entrega de cron no app. Está no backlog
([`11-BACKLOG-E-IDEIAS.md`](11-BACKLOG-E-IDEIAS.md)).

## 5. Segurança

- A senha é pessoal; não compartilhe.
- O Pomelu guarda a sessão no Android Keystore.
- O acesso só funciona com o Tailscale conectado.
- Nada está exposto à internet pública.
- Se perder o celular: remova o dispositivo no admin do Tailscale e
  rotacione a senha (`Configurar-Hermes.ps1 -Rotacionar`).

## 6. Quando voltar

Se algo não funcionar:

```powershell
# No PC:
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1 -SalvarEmLog
```

E leia `DOCS/12-VERIFICACAO-E-TESTES.md` / `DOCS/06-TROUBLESHOOTING.md`.
