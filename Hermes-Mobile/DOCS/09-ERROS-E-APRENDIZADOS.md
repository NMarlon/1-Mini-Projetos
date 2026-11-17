# 09 — Erros e aprendizados

Última atualização: **2026-11-16**

> Registre aqui **erros reais** (com o comando/saída), não teoria.
> A próxima IA deve ler do fim para o início.

---

## Formato

```text
### E0xx — Título curto
- Data:
- Contexto:
- O que eu fiz:
- O que aconteceu:
- Causa:
- Correção:
- Como evitar:
```

---

## E001 — Caminho do projeto OpenCode com usuário errado

- **Data:** 2026-11-16
- **Contexto:** o Marlon passou o caminho
  `C:\Users\marlo\OneDrive\Desktop\...`.
- **O que eu fiz:** tentei `Get-ChildItem` no caminho literal.
- **O que aconteceu:** `PathNotFound` — o perfil real é `C:\Users\Marlon`.
- **Causa:** o caminho foi escrito com `marlo` (sem o “n”).
- **Correção:** usar `$env:USERPROFILE` ou `C:\Users\Marlon`.
- **Como evitar:** nunca hardcodar `C:\Users\<nome>`; use `$env:USERPROFILE`
  ou confirme com `Get-ChildItem C:\Users`.

## E002 — Assumi que o webapp oficial vinha na instalação da Store

- **Data:** 2026-11-16
- **Contexto:** planejar o acesso mobile via `hermes webapp`.
- **O que eu fiz:** verifiquei `webapp_dist_dir` no código instalado.
- **O que aconteceu:** o caminho esperado é
  `<project_root>/apps/desktop/dist-webapp`; essa pasta **não existe** na
  instalação MSIX. O `project_root` é o payload somente-leitura em
  `C:\Program Files\WindowsApps\...\agent-payload\hermes-agent`, que também
  não tem `apps/desktop`.
- **Causa:** a distribuição “desktop-app” da Store empacota o renderer
  Electron, mas não o bundle webapp nem o código-fonte.
- **Correção:** não usar o webapp. Adotar o Pomelu, que fala com o
  `hermes serve` e não depende do bundle.
- **Como evitar:** antes de planejar `hermes webapp`, rodar
  `hermes webapp --status` e conferir `webapp_dist_dir`; não assumir que o
  bundle está presente.

## E003 — Workaround do renderer copiado (descartado)

- **Data:** 2026-11-16
- **Contexto:** tentar salvar o webapp copiando
  `app.asar.unpacked\dist` e apontando `HERMES_WEBAPP_DIST`.
- **O que eu fiz:** servi o `dist` num HTTP temporário e abri no Chrome.
  Com `window.__HERMES_UI_SURFACE__='webapp'`, a UI carregou e pediu login.
- **O que aconteceu:** tecnicamente funciona, mas é um workaround: o bundle
  é do produto “desktop”, não do “webapp”; uma atualização pode quebrar.
- **Causa:** ausência do bundle oficial.
- **Correção:** descartado em favor do Pomelu (decisão do Marlon em
  16/11/2026).
- **Como evitar:** preferir clientes nativos que falam o protocolo do
  `hermes serve` em vez de remendar o frontend.

## E004 — `dashboard.public_url` liga o auth gate em loopback

- **Data:** 2026-11-16
- **Contexto:** manter o `hermes serve` em `127.0.0.1` e publicar via
  Tailscale Serve.
- **O que eu fiz:** li `hermes_cli/web_server_boundary.py` e
  `gateway/run_api.py`.
- **O que aconteceu:** `public_hosts_engage_gate()` retorna `true` quando o
  host do `dashboard.public_url` não é loopback. O listener em loopback
  passa a exigir auth e **recusa iniciar sem um provider**.
- **Causa:** proteção contra exposição via proxy/túnel.
- **Correção:** configurar `HERMES_DASHBOARD_BASIC_AUTH_*` **antes** de
  definir o `public_url` e subir o servidor.
- **Como evitar:** ordem obrigatória: auth → public_url → servidor.

## E005 — Tailscale 443 já pertence ao OpenCode

- **Data:** 2026-11-16
- **Contexto:** publicar o Hermes no Tailscale.
- **O que eu fiz:** `tailscale serve status`.
- **O que aconteceu:** `:443 → 127.0.0.1:28894` (OpenCode). Usar 443
  quebraria o OpenCode.
- **Causa:** o Tailscale Serve tem um handler por porta.
- **Correção:** usar `:8443` para o Hermes.
- **Como evitar:** sempre rodar `tailscale serve status` antes de adicionar
  um handler; nunca usar `tailscale serve reset`.

## E006 — Aviso `install out of sync` é pré-existente

- **Data:** 2026-11-16
- **Contexto:** qualquer comando `hermes`.
- **O que eu fiz:** rodei `hermes --version`, `doctor`, `status`.
- **O que aconteceu:** o shim imprime
  `⚠ install out of sync (venv: out of sync with uv.lock)`.
- **Causa:** instalação gerenciada pelo app da Store; o artefato precisa de
  rebuild.
- **Correção:** nenhuma agora. O `doctor` mostra o runtime staged ativo e o
  CLI funciona.
- **Como evitar:** **não** rodar `hermes update`/rebuild sem backup e
  autorização (REGRA 13). Registrar como tarefa separada.

## E007 — VBS do gateway aponta para pasta inexistente

- **Data:** 2026-11-16
- **Contexto:** verificar autostart existente.
- **O que eu fiz:** li
  `%LOCALAPPDATA%\hermes\gateway-service\Hermes_Gateway.vbs`.
- **O que aconteceu:** ele aponta `HERMES_HOME=C:\Users\marlo\...` e
  `PYTHONPATH=C:\Users\marlo\AppData\Local\hermes\hermes-agent`, que **não
  existe**. Além disso, não há Tarefa Agendada nem atalho na Startup.
- **Causa:** script gerado por uma instalação antiga/outro perfil.
- **Correção:** o projeto cria a própria Tarefa Agendada
  `Hermes Mobile - Servidor`, apontando para `hermes serve` via PowerShell.
  Verificar com `Get-ScheduledTask`.
- **Como evitar:** nunca confiar em autostart pré-existente sem inspecionar
  o `.vbs`/`.cmd` e testar após logout/login.

## E008 — PowerShell 5.1: acentos e `curl`

- **Data:** 2026-11-16
- **Contexto:** escrever scripts com mensagens em português.
- **O que eu fiz:** usei `.ps1` UTF-8.
- **O que aconteceu:** o PS 5.1 interpreta UTF-8 sem BOM como ANSI e quebra
  acentos; `curl` é alias de `Invoke-WebRequest`.
- **Causa:** comportamento do Windows PowerShell 5.1.
- **Correção:** salvar `.ps1` como **UTF-8 com BOM**; usar `curl.exe`.
- **Como evitar:** manter o padrão em todos os scripts.

## E009 — `hermes serve` vs `hermes dashboard`

- **Data:** 2026-11-16
- **Contexto:** escolher o comando do servidor.
- **O que eu fiz:** li o README e o `PROTOCOL.md` do Pomelu.
- **O que aconteceu:** o README cita `hermes dashboard --host 0.0.0.0`,
  mas o protocolo diz `hermes serve`. Os dois expõem a mesma API.
- **Causa:** documentação do app cobre os dois modos.
- **Correção:** usar `hermes serve` (headless, com `--stop/--status`), bind
  `127.0.0.1`, e Tailscale Serve para expor. Se faltar alguma rota, testar
  `hermes dashboard` como fallback.
- **Como evitar:** testar `/api/status` e o handshake WebSocket logo após
  subir.

## E010 — O repositório tem alterações antigas de outros projetos

- **Data:** 2026-11-16
- **Contexto:** commit da pasta `Hermes-Mobile`.
- **O que eu fiz:** `git status`.
- **O que aconteceu:** `M "Alexandre - Videos/.gitignore"` e
  `?? "Reconhecedor de Rostos de  Imagens/"` já estavam lá.
- **Causa:** trabalho anterior do Marlon.
- **Correção:** `git add -- "Hermes-Mobile"` e commit só dessa pasta.
- **Como evitar:** **nunca** `git add -A`/`git add .` neste repositório.

## E011 — Primeiro plano ficou complexo demais

- **Data:** 2026-11-16
- **Contexto:** planejar o acesso mobile do Hermes.
- **O que eu fiz:** propus copiar o renderer do Desktop e servir como webapp.
- **O que aconteceu:** o Marlon apontou que já existem apps nativos (Pomelu)
  que fazem isso; o workaround era desnecessário.
- **Causa:** comecei pela solução “oficial” do Hermes sem pesquisar antes os
  clientes móveis prontos.
- **Correção:** adotar Pomelu + `hermes serve`.
- **Como evitar:** antes de propor solução caseira, pesquisar clientes
  nativos mantidos que falem o protocolo do servidor.

## E012 — Saída de `Get-ChildItem -Recurse` truncada

- **Data:** 2026-11-16
- **Contexto:** listar a pasta do projeto OpenCode no OneDrive.
- **O que eu fiz:** `Get-ChildItem -Recurse | Select-Object RelativePath`.
- **O que aconteceu:** a saída veio com caminhos repetidos/truncados.
- **Causa:** combinação de caminho longo + formatação do console.
- **Correção:** usei `cmd /c dir /s /b` e `-Name`.
- **Como evitar:** para árvores grandes, usar `cmd /c dir /s /b` ou
  `Get-ChildItem | ForEach-Object { $_.FullName }`.

---

## Erros a registrar durante a execução

- (vazio — preencher conforme acontecerem)
