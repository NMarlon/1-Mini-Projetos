# Hermes-Mobile

Usar o **Hermes Agent** que roda no PC Windows a partir do **celular Android**,
com acesso privado pelo **Tailscale** e interface do app **Pomelu**.

Este projeto é o equivalente, para o Hermes, do que o projeto
`Integração OpenCode CLI Desktop com Mobile` faz para o OpenCode.

---

## Como funciona

```text
Pomelu / Mono Hermes (Android)
   │  HTTPS + Tailscale
   ▼
https://marlon-dell-pc.tail6ded59.ts.net:8443
   │  Tailscale Serve (somente tailnet)
   ▼
hermes serve  →  127.0.0.1:9119

Webapp / Hermes-Android (Android)
   │  HTTPS + Tailscale
   ▼
https://marlon-dell-pc.tail6ded59.ts.net:8444
   │  Tailscale Serve
   ▼
gateway (webapp)  →  127.0.0.1:9120
```

- O agente, os modelos, os arquivos e as sessões ficam **no PC**.
- O celular é só o cliente: conversa, aprova comandos, responde perguntas,
  envia arquivos/fotos/voz e acompanha tarefas.
- O Hermes escuta **apenas em `127.0.0.1`**.
- O Tailscale Serve publica em **8443** (Pomelu/Mono Hermes) e **8444**
  (Webapp completo). O OpenCode continua no **443** e não é alterado.

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

### Pomelu (conversas rápidas)

1. Instale o **Pomelu**:
   - Google Play: <https://play.google.com/store/apps/details?id=se.royan.pomelu>
   - APK oficial: <https://github.com/ateymoori/pomelu/releases/latest>
2. Abra **Settings** e adicione o gateway:
   `https://marlon-dell-pc.tail6ded59.ts.net:8443`
3. Entre com o usuário/senha mostrados por `Ver-Credenciais.ps1`.
4. Toque em **Test connection** e depois **Save and connect**.
5. Opcional: ative notificações/“Stay connected”.

### Webapp completo (sessões, projetos, arquivos, Git, terminal)

1. O webapp é servido pelo gateway em `:8444`:
   `https://marlon-dell-pc.tail6ded59.ts.net:8444`
2. Abra no Chrome (Android/PC) e faça login com o mesmo usuário/senha.
3. Opcional: “Adicionar à tela inicial” (PWA) ou usar o app **Hermes-Android**
   apontando para a mesma URL.
4. Se o webapp não abrir, rode:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1
   ```

> O **Mono Hermes** (APK) também conecta no `:8443` e mostra sessões, mas a
> UI dele é de Hermes 0.22.0; no servidor 0.23.1 aparece um **aviso de versão**
> (informativo). Para o workspace completo e alinhado, use o Webapp `:8444`.

## Comandos do dia a dia

```powershell
# Diagnóstico completo (rodar antes de assumir qualquer coisa)
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1

# Subir/garantir o servidor + Tailscale + webapp
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1

# Configurar/reparar o webapp completo (workspace do Desktop)
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1

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
