# 09 — Erros e aprendizados

Última atualização: **2026-11-17**

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

## E013 — `$HOME` é read-only no PowerShell

- **Data:** 2026-11-16
- **Contexto:** `Configurar-Hermes.ps1` usava `$home = Get-HermesHome`.
- **O que aconteceu:** `SessionStateUnauthorizedAccessException`: a variável
  `HOME` é automática e somente leitura.
- **Causa:** colisão com a variável automática `$HOME`.
- **Correção:** renomear para `$hermesHome`.
- **Como evitar:** nunca usar `$home`, `$pid`, `$host` etc. como variáveis
  próprias em scripts PowerShell.

## E014 — `Get-HermesPython` escolheu o Python errado

- **Data:** 2026-11-16
- **Contexto:** gerar o hash scrypt.
- **O que aconteceu:** a função pegou o Python do store
  (`tools\python-3.14.9...`) em vez do Python do venv staged; o store não
  tem `httpx`, e o import de `plugins.dashboard_auth.basic` falhou.
- **Causa:** ordenação por `LastWriteTime` misturando as duas árvores.
- **Correção:** preferir sempre `installs\*\environments\*\venv\Scripts\python.exe`;
  o Python do store é apenas fallback.
- **Como evitar:** o hash scrypt depende das dependências do venv do Hermes.

## E015 — JSON com aspas quebrado ao passar para `curl.exe`

- **Data:** 2026-11-16
- **Contexto:** testar `POST /auth/password-login` no PowerShell 5.1.
- **O que aconteceu:** `422 JSON decode error` porque o PowerShell removeu as
  aspas do JSON ao passar `-d $body` para o `curl.exe`.
- **Causa:** parsing de argumentos do PowerShell 5.1 para comandos nativos.
- **Correção:** gravar o JSON num arquivo temporário e usar
  `curl.exe --data-binary "@arquivo"`.
- **Como evitar:** para JSON em comandos nativos, usar arquivo; ou usar
  `Invoke-RestMethod`.

## E016 — `icacls /grant:r` mangled pelo PowerShell

- **Data:** 2026-11-16
- **Contexto:** restringir a ACL do `secrets.json`.
- **O que aconteceu:** `icacls.exe` retornou “Parâmetro inválido
  `/grant:r`” quando chamado direto; via `cmd /c` funcionou.
- **Causa:** o PowerShell 5.1 interpreta/mangleia o argumento `/grant:r`.
- **Correção:** montar a linha e executar com `cmd.exe /c`.
- **Como evitar:** para `icacls`, usar `cmd /c` com a linha completa.

## E017 — Modelo padrão `deepseek-flash` rejeitado pelo OpenCode Go

- **Data:** 2026-11-16
- **Contexto:** primeiro teste de prompt pelo WebSocket.
- **O que aconteceu:** o agente respondeu com erro:
  `HTTP 400: Model deepseek-flash isn't included in OpenCode Go`.
- **Causa:** o `model.default` estava `deepseek-flash`; o `model.main_model`
  já era `deepseek-v4.1-flash`. O provider não aceita o alias antigo.
- **Correção:** backup do `config.yaml` e
  `hermes config set model.default deepseek-v4.1-flash`. Teste repetido
  retornou `OK`.
- **Como evitar:** após trocar de provider/plano, validar o modelo com um
  prompt curto; ver `06-TROUBLESHOOTING.md` seção 9.

## E018 — `Get-TailscaleServeEntry` acessava `HTTPS` inexistente

- **Data:** 2026-11-16
- **Contexto:** diagnóstico do Tailscale.
- **O que aconteceu:** `PropertyNotFoundException: HTTPS` sob
  `Set-StrictMode`; os handlers 443/8443 eram reportados como ausentes.
- **Causa:** o JSON do `tailscale serve status` tem `TCP.443.HTTPS`, não
  `Web["host:443"].HTTPS`.
- **Correção:** remover o campo `Https` do objeto e criar
  `Test-TailscaleFunnelEnabled` lendo `AllowFunnel`.
- **Como evitar:** não acessar propriedades opcionais sem
  `PSObject.Properties.Match()`.

## E019 — `.Count` em objeto único

- **Data:** 2026-11-16
- **Contexto:** `Get-NetTCPConnection` retornou um único listener.
- **O que aconteceu:** `PropertyNotFoundException: Count` sob StrictMode.
- **Causa:** um único objeto não tem `.Count` (no PS 5.1).
- **Correção:** usar `@($listeners).Count`.
- **Como evitar:** sempre envolver resultados de cmdlets em `@()` antes de
  medir/count.

## E020 — `Register-ScheduledTask -Task` é ambíguo

- **Data:** 2026-11-16
- **Contexto:** criar a Tarefa Agendada do autostart.
- **O que aconteceu:** erro “parâmetro 'Task' é ambíguo; candidatos
  -TaskName -TaskPath”.
- **Causa:** o parâmetro do objeto é `-InputObject`, não `-Task`, nesta
  versão do módulo ScheduledTasks.
- **Correção:** `Register-ScheduledTask -TaskName ... -InputObject $task`.
- **Como evitar:** conferir `Get-Command Register-ScheduledTask`.

## E021 — `Start-Process` com redirecionamento segura o terminal

- **Data:** 2026-11-16
- **Contexto:** subir o `hermes serve` em background pelo script.
- **O que aconteceu:** o script imprimia “servidor ativo” mas o comando
  demorava/hangava no shell do agente; o servidor ficava rodando.
- **Causa:** os handles de stdout/stderr redirecionados ficavam abertos no
  processo filho, e o job do terminal esperava.
- **Correção:** gerar um VBS (`Iniciar-HermesServe-<porta>.vbs`) e iniciar
  via `wscript.exe`, destacado. O modo `-Foreground` (Tarefa Agendada) usa
  `hermes serve` direto e grava em `logs/task-servidor-*.log`.
- **Como evitar:** para processos de longa duração, não usar
  `Start-Process` com redirecionamento no mesmo terminal; usar VBS/serviço.

## E022 — `Stop-ScheduledTask` não mata o servidor destacado

- **Data:** 2026-11-16
- **Contexto:** testar o autostart.
- **O que aconteceu:** a tarefa ficou `Ready`, mas o `hermes serve` continuou
  escutando em 80.
- **Causa:** o `hermes.exe` (alias) destaca o processo; parar a tarefa não
  garante matar o filho.
- **Correção:** verificar a porta/HTTP, não só o estado da tarefa; parar com
  `Parar-Mobile.ps1` (PID da porta).
- **Como evitar:** tratar “tarefa Running/Ready” e “servidor de pé” como
  sinais separados.

## E023 — Atalho `.lnk` com URL ficou sem destino

- **Data:** 2026-11-16
- **Contexto:** criar o atalho "Hermes Mobile" na área de trabalho.
- **O que aconteceu:** `WScript.Shell.CreateShortcut` com
  `TargetPath = "https://..."` criou um `.lnk` com target vazio.
- **Causa:** `.lnk` não é o formato correto para URL.
- **Correção:** criar um arquivo **`.url`** (Internet Shortcut) com:
  `[InternetShortcut]`, `URL=...`, `IconFile=...`.
- **Como evitar:** para sites, usar `.url`; para programas, `.lnk`.

## E024 — `robocopy` com `Start-Process -ArgumentList` quebrou o caminho

- **Data:** 2026-11-17
- **Contexto:** copiar o renderer para o webapp.
- **O que aconteceu:** `Start-Process -ArgumentList @($src,$dst,...)` juntou
  os argumentos sem aspas; o robocopy leu `C:\Program` e falhou com
  “Parâmetro Inválido #3”.
- **Causa:** `Start-Process` não cita cada elemento do array.
- **Correção:** montar a linha com aspas e rodar `cmd.exe /c`:
  `robocopy "src" "dst" /MIR ...`; checar `$LASTEXITCODE` (0-7 = sucesso).
- **Como evitar:** para caminhos com espaços, usar `cmd /c` com aspas.

## E025 — Webapp raiz retorna 302 (login), não 200

- **Data:** 2026-11-17
- **Contexto:** testar `https://...:8444/` com `curl`.
- **O que aconteceu:** HTTP 302 e “HTML inesperado”.
- **Causa:** `webapp.public_url` liga o auth gate; a raiz redireciona para
  `/login` quando não há sessão.
- **Correção:** testar `/login` (200) ou fazer login e reenviar o cookie;
  com sessão, `/` retorna 200 e o HTML contém `__HERMES_UI_SURFACE__`.
- **Como evitar:** no diagnóstico, checar `/login` e `/api/status` (públicos)
  antes de concluir que o webapp está quebrado.

## E026 — Aviso de versão no Mono Hermes

- **Data:** 2026-11-17
- **Contexto:** Mono Hermes v0.4.0 conectado ao servidor 0.23.2.
- **O que aconteceu:** aviso de versão (UI construída para Hermes 0.22.0).
- **Causa:** o app é comunitário e congela a UI em 0.22.0; não há release
  mais nova até 17/11/2026.
- **Correção:** o aviso é informativo; para o workspace completo e alinhado,
  usar o **Webapp oficial em `:8444`** (renderer do app instalado). Acompanhar novas
  releases do Mono Hermes.
- **Como evitar:** não confundir aviso de versão com falha de gateway; testar
  `/api/status` e o chat.

## E027 — Gateway manual parava e gerava aviso intermitente

- **Data:** 2026-11-17
- **Contexto:** Desktop/Mono Hermes mostravam “Gateway” vermelho às vezes.
- **O que aconteceu:** `hermes gateway status` dizia “Running manually”, e o
  processo sumia quando o Desktop/terminal fechava.
- **Causa:** gateway iniciado manualmente, sem serviço/login item.
- **Correção:** `hermes gateway install --force --start-on-login` (o UAC foi
  pulado e ele criou `Startup\Hermes_Gateway.vbs`). `/api/status` passou a
  `gateway_running: true`, `overall: ok`.
- **Como evitar:** manter o gateway como login item; conferir
  `hermes gateway status` após logoff/login.

## E028 — Mono Hermes: WebSocket 403 por `Origin: http://localhost`

- **Data:** 2026-11-18
- **Contexto:** Mono Hermes conectava, mas mostrava
  “Could not connect to Hermes gateway (websocket error before Open)”.
- **O que eu fiz:** testei o WebSocket com vários `Origin`:
  - sem Origin → OK
  - `http://localhost` → **HTTP 403**
  - `http://localhost:80` → **HTTP 403**
  - `http://localhost:9119` → OK
  - `https://marlon-dell-pc.tail6ded59.ts.net:8443` → OK
- **Causa:** o WebView do Mono Hermes usa `androidScheme: http` e
  `hostname: localhost`, então envia `Origin: http://localhost` (porta 80).
  O Hermes 0.23.2 endureceu a checagem: uma origem loopback só é confiável
  se a porta for igual à `state.bound_port` (ou se o `public_url` for
  loopback). Com o serve em 9119, 80 ≠ 9119 → 403 antes de abrir o socket.
  O app foi construído para 0.22.0, quando a checagem era mais permissiva.
- **Correção:** rodar o `hermes serve` em `127.0.0.1:80` e manter o Tailscale
  Serve `:8443 → 127.0.0.1:80`. O URL público continua
  `https://...:8443`; o `Origin: http://localhost` agora casa com a porta 80.
- **Atenção:** a 8444 (webapp) também rejeita esse Origin, porque o listener
  está em 9120. Mono Hermes usa **8443**, não 8444.
- **Como evitar:** não presumir que qualquer porta local serve para o Mono
  Hermes; a origem do WebView é fixa em `http://localhost`.

---

## Erros a registrar durante a execução

- (vazio — preencher conforme acontecerem)
