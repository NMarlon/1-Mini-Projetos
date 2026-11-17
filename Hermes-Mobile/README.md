# Hermes-Mobile

Usar o **Hermes Agent** que roda no PC Windows a partir do **celular Android**,
com acesso privado pelo **Tailscale** e interface do app **Pomelu**.

Este projeto é o equivalente, para o Hermes, do que o projeto
`Integração OpenCode CLI Desktop com Mobile` faz para o OpenCode.

---

## Como funciona

```text
Pomelu (Android)
   │  HTTPS + Tailscale
   ▼
https://marlon-dell-pc.tail6ded59.ts.net:8443
   │  Tailscale Serve (somente tailnet)
   ▼
hermes serve  →  127.0.0.1:9119
```

- O agente, os modelos, os arquivos e as sessões ficam **no PC**.
- O celular é só o cliente: conversa, aprova comandos, responde perguntas,
  envia arquivos/fotos/voz e acompanha tarefas.
- O Hermes escuta **apenas em `127.0.0.1`**.
- O Tailscale Serve publica em **8443**, sem abrir porta no roteador e sem
  Funnel. O OpenCode continua no **443** e não é alterado.

## Começar do zero (PC novo ou PC atual)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1
```

Esse script:

1. Verifica o Hermes instalado e o Tailscale.
2. Gera usuário/senha/segredo de autenticação do gateway.
3. Define `dashboard.public_url` para a URL do tailnet.
4. Sobe o `hermes serve` em `127.0.0.1:9119`.
5. Ativa o Tailscale Serve em `:8443`.
6. Instala o autostart no login (opcional).
7. Mostra a URL e as credenciais.

## No celular

1. Instale o **Pomelu**:
   - Google Play: <https://play.google.com/store/apps/details?id=se.royan.pomelu>
   - APK oficial: <https://github.com/ateymoori/pomelu/releases/latest>
2. Abra **Settings** e adicione o gateway:
   `https://marlon-dell-pc.tail6ded59.ts.net:8443`
3. Entre com o usuário/senha mostrados por `Ver-Credenciais.ps1`.
4. Toque em **Test connection** e depois **Save and connect**.
5. Opcional: ative notificações/“Stay connected”.

## Comandos do dia a dia

```powershell
# Diagnóstico completo (rodar antes de assumir qualquer coisa)
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1

# Subir/garantir o servidor + Tailscale
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1

# Parar o servidor e remover o handler 8443
powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1

# Ver URL/usuário e, com -Revelar, a senha
powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar
```

## Documentação

Toda a documentação está em [`DOCS/`](DOCS/00-INDICE.md). Comece pelo
[`DOCS/00-INDICE.md`](DOCS/00-INDICE.md) e leia o
[`AGENTS.md`](AGENTS.md) antes de alterar qualquer coisa.

## Segurança

- Segredos ficam **fora do repositório**: `%LOCALAPPDATA%\hermes\.env` e
  `%LOCALAPPDATA%\HermesMobile\secrets.json`.
- Nunca commitar senha, token, hash ou cookie.
- Nunca usar Tailscale Funnel nem abrir porta no roteador.
- Nunca trocar o bind do Hermes para `0.0.0.0`.

Detalhes em [`DOCS/05-SEGURANCA.md`](DOCS/05-SEGURANCA.md).
