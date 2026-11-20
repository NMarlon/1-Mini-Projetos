# 03 — Guia rápido (PC + celular)

Última atualização: **2026-11-17**

---

## 1. Pré-requisitos

- Hermes Agent **0.21.5+** instalado no PC (atual: 0.23.2).
- Tailscale instalado e logado no PC e no celular, na **mesma conta**.
- Celular Android **10+** (Galaxy A32 atende).
- PC ligado e acordado.

## 2. Primeira instalação no PC

Abra o PowerShell na pasta `Hermes-Mobile` e rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1
```

O script vai:

1. Verificar Hermes e Tailscale.
2. Gerar usuário `hermes`, senha forte, hash scrypt e secret.
3. Gravar as variáveis no `%LOCALAPPDATA%\hermes\.env` (com backup).
4. Definir `dashboard.public_url` para a URL do tailnet.
5. Subir o `hermes serve` em `127.0.0.1:80`.
6. Ativar o Tailscale Serve em `:8443`.
7. Oferecer instalar o autostart no login.
8. Mostrar a URL e como ver a senha.

Se preferir passo a passo, veja a seção 4.

## 3. No celular

1. Instale o **Pomelu**:
   - Google Play:
     <https://play.google.com/store/apps/details?id=se.royan.pomelu>
   - APK oficial:
     <https://github.com/ateymoori/pomelu/releases/latest>
2. Abra o app → **Settings**.
3. Adicione o gateway:
   - **URL:** `https://marlon-dell-pc.tail6ded59.ts.net:8443`
   - **Usuário:** `hermes`
   - **Senha:** veja no PC com
     `powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar`
4. Toque em **Test connection**.
5. Toque em **Save and connect**.
6. Abra um bot e envie um prompt de teste.

> A senha é necessária apenas no primeiro login. O Pomelu guarda a sessão no
> Android Keystore.

### 3.1. Webapp completo (sessões, projetos, arquivos, Git, terminal)

O gateway serve o workspace do Desktop em `:8444`:

1. Abra no Chrome do celular:
   `https://marlon-dell-pc.tail6ded59.ts.net:8444`
2. Faça login com o mesmo usuário/senha.
3. Opcional: “Adicionar à tela inicial” (PWA) ou instalar o **Hermes-Android**
   e apontar para a mesma URL.
4. Se não abrir, rode no PC:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1
   ```

> O **Mono Hermes** (APK) mostra sessões no `:8443`, mas a UI dele é de
> Hermes 0.22.0; no servidor 0.23.2 aparece um aviso de versão informativo.
> Para o workspace completo e alinhado, use o Webapp `:8444`.

## 4. Passo a passo manual (se não quiser o Instalar-Tudo)

### 4.1. Configurar autenticação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Hermes.ps1
```

Isso grava no `.env`:

```env
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=hermes
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=scrypt$...
HERMES_DASHBOARD_BASIC_AUTH_SECRET=<32 bytes>
HERMES_DASHBOARD_BASIC_AUTH_TTL_SECONDS=604800
```

E define no `config.yaml`:

```yaml
dashboard:
  public_url: "https://marlon-dell-pc.tail6ded59.ts.net:8443"
```

### 4.2. Subir o servidor

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1
```

Equivalente manual:

```powershell
hermes serve --host 127.0.0.1 --port 80 --skip-build
```

> A porta local é **80** (não 9119) porque o WebView do Mono Hermes envia
> `Origin: http://localhost`; o Hermes 0.23.2 só aceita esse Origin quando a
> porta local é 80. O URL público continua `:8443`.

### 4.3. Publicar no Tailscale

```powershell
tailscale serve --bg --https=8443 http://127.0.0.1:80
```

Verifique:

```powershell
tailscale serve status
```

Deve mostrar **os dois** handlers:

```text
https://marlon-dell-pc.tail6ded59.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:28894
https://marlon-dell-pc.tail6ded59.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:80
```

### 4.4. Testar

```powershell
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
```

O JSON deve conter `"auth_required": true` e `"auth_providers": ["basic"]`.

## 5. Uso diário

```powershell
# Garantir que tudo está de pé
powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1

# Webapp completo (se estiver habilitado)
powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1

# Ver status
powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1
```

No celular, basta abrir o Pomelu com o Tailscale ligado.

## 6. Parar / desligar

```powershell
# Para o servidor do Hermes e remove o handler 8443
powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1

# Remove o autostart
powershell -ExecutionPolicy Bypass -File .\scripts\Remover-Autostart.ps1
```

O OpenCode em `:443` **não é afetado**.
O gateway/webapp em `:9120` continua; use `-PararGateway` se quiser parar
também (isso derruba o webapp `:8444`).

## 7. Reverter tudo (rollback completo)

1. `Parar-Mobile.ps1`
2. `Remover-Autostart.ps1`
3. `tailscale serve --https=8443 off`
4. No `.env`, remover as linhas `HERMES_DASHBOARD_BASIC_AUTH_*`.
5. No `config.yaml`, limpar `dashboard.public_url`.
6. Opcional: apagar `%LOCALAPPDATA%\HermesMobile\`.
7. Reiniciar o Hermes/Desktop se estiver aberto.

## 8. Atualização do Hermes

Quando o Hermes for atualizado (Store/`hermes update`):

1. Rode `Status-Diagnostico.ps1`.
2. Teste `/api/status` e o login.
3. Se o webapp estiver habilitado, rode `Configurar-Webapp.ps1 -Forcar`
   para recopiar o renderer da nova versão.
4. Se o protocolo mudar, veja `DOCS/06-TROUBLESHOOTING.md`.
5. **Não** rode `hermes update` sozinho sem backup (REGRA 13).

## 9. PC novo

1. Copie esta pasta.
2. Instale Hermes e Tailscale.
3. Rode `Instalar-Tudo.ps1`.
4. Gere novas credenciais (o script faz).
5. Reconfigure o Pomelu com a nova URL/nome do PC.
