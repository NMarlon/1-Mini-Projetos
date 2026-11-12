# Erros e Aprendizados — Terabox Auto-Backuper

> Registre aqui os erros cometidos e como foram superados, para que a próxima IA não caia nos mesmos.

## Formato

```
### [DATA] Título do erro
**Contexto**: O que estava sendo feito
**Erro**: O que aconteceu
**Causa**: Por que aconteceu
**Solução**: Como foi resolvido
**Aprendizado**: Lição para o futuro
```

---

## Erros Registrados

### [2026-11-12] Restaurar pedia uma pasta de destino que já existia na configuração
**Contexto**: Implementar a restauração em árvore para 5.282 arquivos.
**Erro**: A aba Restaurar pedia uma "Pasta de destino" manual e o backend gravava em `destination/local_rel_path`, ignorando `mappings.local_path`. O usuário podia restaurar no lugar errado, ou sobrescrever arquivos sem aviso.
**Causa**: O processo reverso foi pensado como "exportar para uma pasta", não como "devolver ao lugar original". O manifesto já tinha `mapping_id` e `local_rel_path`, mas o backend nunca consultava o mapeamento atual.
**Solução**:
- O destino agora é `mapping.local_path` (pasta) ou o próprio arquivo (mapeamento de arquivo único).
- `POST /api/restore/plan` classifica criar/substituir/erro antes de baixar.
- `allow_overwrite=false` retorna 409 em conflitos; a UI só confirma e reenvia quando o usuário autoriza.
- Configuração `restore_confirm_overwrite` permite desligar a pergunta.
- `mappings.is_file` é persistido para não confundir arquivo apagado com pasta.
- O cache `files` é atualizado após o restore para o próximo sync não reenviar o mesmo conteúdo.
**Aprendizado**: Se o dado de destino já existe na configuração, o fluxo reverso deve derivá-lo dela. Não pedir ao usuário uma informação que o sistema já tem; isso cria divergência e risco de escrever no lugar errado. Planejar antes de baixar (dry-run) permite avisar sobre substituições sem tocar no disco.

---

### [2026-11-12] Seleção de restauração nascia vazia e ficava presa
**Contexto**: Melhorar a aba Restaurar, que listava 5.277 arquivos em uma lista plana.
**Erro**: O manifesto abria com todos os arquivos desmarcados, e o estado vazio continuava após recarregar.
**Causa**: `JSON.parse(localStorage.getItem(KEY) || '[]')` não distingue "chave ausente" de "lista vazia". Além disso, `loadManifest()` chamava `saveRestoreSelection()` logo após carregar e gravava `[]`, transformando o defeito em estado permanente.
**Solução**:
- Nova chave `terabox_restore_selected_v2`; a v1 é migrada se tiver caminhos.
- v1 vazia (`[]`) é tratada como ausência de seleção e volta para "todos".
- A seleção só é gravada depois de uma alteração do usuário.
- A árvore usa checkbox de pasta em três estados, mas o backend recebe apenas `remote_path` de arquivos.
- Checkboxes de pasta têm classe própria; nunca usar `input[type="checkbox"]` genérico para montar o payload.
**Aprendizado**: `localStorage.getItem()` retorna `null` quando a chave não existe; não usar `|| '[]'` quando vazio e ausente têm significados diferentes. Não persistir um estado padrão antes de o usuário interagir.

---

### [2026-11-11] Sync de teste sobrescreveu o manifesto global
**Contexto**: Validar a seleção de mapeamentos com um mapeamento descartável (`_teste_selecao`) e 2 arquivos.
**Erro**: O sync de teste gravou `/_terabox_autobackup_manifest.json` apenas com os 2 arquivos de teste. O backup real (`Marlon Desktop`, ~3.900 arquivos) sumiu da aba Restaurar, e a limpeza seguinte apagou o manifesto.
**Causa**: O manifesto é **global**, não por mapeamento. Usar uma pasta remota descartável não isola o manifesto; qualquer sync o sobrescreve.
**Solução**:
- Reconstruir o manifesto a partir da pasta local + snapshot remoto, sem reenviar arquivos: 3.879 arquivos e 1.102 pastas recuperados.
- Deduplicar por `remote_path` e preferir o nome local natural quando dois arquivos colidem (ex.: `.kkrieger.md` e `kkrieger.md`).
- Verificar baixando o manifesto de volta e conferindo a contagem.
**Aprendizado**: Antes de qualquer sync de teste, salve o manifesto remoto ou use um caminho de manifesto isolado. O manifesto é o artefato que alimenta o Restaurar; perdê-lo não perde os arquivos, mas esconde o backup da UI.

---

### [2026-11-09] Pastas duplicadas com data durante o sync
**Contexto**: Sync do Desktop com muitos arquivos
**Erro**: Pastas como `Marlon Desktop_20261109_190922` apareciam a cada execução
**Causa**: `_process_file()` chamava `create_directory()` para **cada arquivo**, e `create_directory()` usava `rtype=1`. O Terabox interpreta `rtype=1` como "renomeie em conflito", então cada chamada criava uma pasta nova com timestamp em vez de reutilizar a existente.
**Solução**:
- `rtype=0` para criar pastas (nunca renomeia)
- Criar cada diretório uma única vez por execução (`known_dirs` + `ensured`)
- `rtype=3` somente para substituir arquivo alterado
- `target_path` sempre POSIX
**Aprendizado**: `rtype=1` nunca deve ser usado em backup. A pasta não deve ser criada por arquivo; o plano deve garantir a árvore de diretórios antes dos uploads.

---

### [2026-11-09] Arquivo alterado nunca era substituído
**Contexto**: Corrigir deduplicação do sync
**Erro**: A dedup comparava apenas `name` ou `path.endswith(rel_path)`; o `local_md5` era calculado e descartado. Arquivos com o mesmo nome em pastas diferentes eram pulados, e arquivos alterados nunca eram reenviados.
**Solução**:
- Comparar **caminho exato + tamanho + MD5**
- Substituir no mesmo caminho com `rtype=3`
- Guardar `md5`, `remote_md5` e `mtime_ns` no banco
- Para criptografia, comparar o MD5 do plaintext (Fernet usa IV aleatório)
**Aprendizado**: Nunca deduplicar por nome. O caminho relativo completo é a identidade; o hash é o conteúdo.

---

### [2026-11-09] `ON CONFLICT DO NOTHING` não fazia nada
**Contexto**: Inserir registros na tabela `files`
**Erro**: O banco tinha 124 linhas para 122 caminhos distintos; o UPSERT não atualizava nada
**Causa**: A tabela não tinha índice/constraint único em `(mapping_id, local_rel_path)`, então o `ON CONFLICT` nunca era acionado.
**Solução**: Migração idempotente que remove duplicatas/órfãos, cria `UNIQUE INDEX idx_files_mapping_rel` e usa `ON CONFLICT(...) DO UPDATE`.
**Aprendizado**: `ON CONFLICT` só funciona com constraint/índice único correspondente. Migração precisa rodar antes do primeiro UPSERT.

---

### [2026-11-09] Terabox rejeita emojis em nomes de pasta
**Contexto**: Sync do Desktop com pastas `00 - 📥 Inbox`, `01 - 📚 Estudos`
**Erro**: `errno=-7 param path file name is invalid`; a pasta era criada mas a subpasta com emoji falhava
**Causa**: A API do Terabox aceita acentos e `;`, mas rejeita emojis/símbolos Unicode em nomes.
**Solução**:
- `sanitize_remote_component()` substitui símbolos por espaço e anexa hash curto quando muda
- O caminho remoto fica `00 - Inbox_a19902` e `nota_9bac5f.txt`
- O `local_rel_path` original (`📥 Inbox/nota 📝.txt`) fica no manifesto; o Restaurar recria o nome original
- Acentos e `Realidade; Verdade` são preservados
**Aprendizado**: Separar "nome remoto seguro" de "nome local original". O manifesto é a ponte entre os dois.

---

### [2026-11-09] Download do manifesto/restauração retornava vazio
**Contexto**: Implementar Restaurar
**Erro**: `GET /api/restore/manifest` dizia "manifesto não encontrado", mesmo com o arquivo no Terabox; `/api/download` retornava `errno=2`
**Causa**: O endpoint `/api/download` com `path`/`fidlist` não é o correto para conta própria.
**Solução**: Usar `GET /api/filemetas` com `target=["/arquivo"]` e `dlink=1`, que devolve `info[0].dlink`; fallback para `/rest/2.0/pcs/file` (302 + `Location`).
**Aprendizado**: Testar o endpoint de download separadamente. O dlink expira (~8h), então deve ser obtido na hora do download.

---

### [2026-11-09] Watchdog disparava `RuntimeError` de event loop
**Contexto**: Alterar arquivos monitorados com o app via `pythonw`
**Erro**: `RuntimeError: There is no current event loop in thread 'Thread-...'`
**Causa**: `asyncio.ensure_future()` era chamado dentro da thread do watchdog, que não tem event loop.
**Solução**: Capturar o loop principal em `FileMonitor.start()` e usar `loop.call_soon_threadsafe(...)` para criar a task. O callback também respeita `auto_sync`.
**Aprendizado**: Handlers do watchdog rodam em outra thread; nunca criar tasks diretamente nela.

---

### [2026-11-09] Parar sync demorava durante criação de milhares de pastas
**Contexto**: Cancelar um sync que estava criando ~1.100 diretórios
**Erro**: `stop_sync()` demorava porque `_cancelled` só era verificado entre arquivos
**Solução**: Verificar `_cancelled` também entre cada pasta em `_run_sync`.
**Aprendizado**: Loops de setup (diretórios, listagem) também precisam de pontos de cancelamento.

---

### [2026-11-09] Janelas de CMD piscando durante o sync (pythonw + curl)
**Contexto**: Sync de muitos arquivos com o app iniciado pelo `INICIAR.bat` (`pythonw.exe`, sem console)
**Erro**: Uma janela de console piscava para cada arquivo/chunk enviado, tornando o PC desconfortável de usar
**Causa**: `subprocess.run(["curl", ...])` em `terabox_client._curl_upload()` não usava `CREATE_NO_WINDOW`. No Windows, todo processo de console filho de um processo sem console recebe uma janela de console nova. O mesmo risco existia em `tasklist`/`powershell` da autenticação e no seletor de pastas.
**Solução**:
- Criar `backend/process_utils.py` com `run_hidden()` / `popen_hidden()`, aplicando `CREATE_NO_WINDOW` + `STARTUPINFO` com `SW_HIDE`
- Usar o helper no upload via curl, nas verificações/fechamento do Dia e no seletor nativo de pastas
- Manter `subprocess.Popen` visível apenas para reabrir o Dia (é um app gráfico)
- Teste real com 12 arquivos e app via `pythonw`: 12/12 enviados, pico de 0 janelas extras de console
**Aprendizado**: Qualquer `subprocess` de programa de console chamado por um app `pythonw` deve usar `CREATE_NO_WINDOW`. Testar sempre no modo `pythonw`, não no `python` com console — no modo console o filho herda o terminal e o bug não aparece.

---

### [2026-11-09] Sync acidental ao recarregar o file monitor durante testes
**Contexto**: Adicionar um mapeamento temporário via API para testar o upload silencioso
**Erro**: `_reload_file_monitor()` iniciou o monitor e disparou um sync de todos os mapeamentos habilitados, incluindo um mapeamento grande do Desktop do usuário (4.111 arquivos)
**Solução**: Parar o sync imediatamente; desabilitar temporariamente o mapeamento grande durante o teste; limpar mapeamento temporário, arquivos remotos de teste e registros de teste do banco
**Aprendizado**: Ao testar criação/edição de mapeamentos, desabilitar os demais mapeamentos antes. O reload do watchdog pode disparar sync automático por debounce.

---

### [2026-11-08] PowerShell não aceita &&
**Contexto**: Tentando criar pastas e inicializar git em um único comando
**Erro**: `O token '&&' não é um separador de instruções válido nesta versão`
**Causa**: PowerShell (Windows) não suporta `&&` como separador de comandos (diferente do bash)
**Solução**: Usar `;` como separador ou executar comandos separadamente
**Aprendizado**: Sempre usar `;` no PowerShell. Ou melhor, usar a tool `write`/`edit` para criar arquivos e `shell` com comandos simples.

---

### [2026-11-08] Chrome App-Bound Encryption (v20)
**Contexto**: Pesquisa sobre extração de cookies do Chrome
**Erro**: browser-cookie3 não consegue descriptografar cookies do Chrome 127+
**Causa**: Google introduziu App-Bound Encryption (ABE) que vincula a criptografia ao binário do Chrome
**Solução**: Usar rookie-cookies (Rust nativo) que suporta v20 via COM injection
**Aprendizado**: Sempre verificar se a lib de cookies suporta a versão atual do Chrome. rookie-cookies é a única que suporta v20.

---

### [2026-11-08] jsToken não é cookie
**Contexto**: Pesquisa sobre autenticação Terabox
**Erro**: Assumir que jsToken seria um cookie (como csrfToken, ndus, etc.)
**Causa**: jsToken é derivado do HTML da página /main, não de cookies
**Solução**: Fazer GET em /main com cookies e extrair jsToken via regex do HTML
**Aprendizado**: jsToken ≠ cookie. É um token anti-bot derivado da página. Sempre fazer scraping do HTML. Referência: terabox-webdav-worker.

---

### [2026-11-08] ndus é httpOnly
**Contexto**: Pesquisa sobre cookies do Terabox
**Erro**: Tentar ler cookies via document.cookie no console do navegador
**Causa**: ndus é httpOnly, não acessível via JavaScript
**Solução**: Ler do banco de dados do navegador (rookie-cookies) ou do Network tab (Cookie header)
**Aprendizado**: Nunca usar document.cookie para pegar ndus. Usar rookie-cookies ou Network tab.

---

### [2026-11-08] Windows Defender bloqueia rookie-cookies.pyd
**Contexto**: Importando rookie-cookies pela primeira vez
**Erro**: `ImportError: DLL load failed while importing rookie_cookies: Não foi possível concluir a operação... vírus ou software possivelmente indesejado`
**Causa**: Windows Defender (proteção em tempo real) detecta o .pyd (módulo Rust nativo) como heurística de ameaça, porque o COM injection para App-Bound Encryption tem a mesma forma que malware
**Solução**: Adicionar exclusão no Windows Defender para a pasta do pacote: `Add-MpPreference -ExclusionPath "...\site-packages\rookie_cookies\"` (requer admin)
**Aprendizado**: Documentar a necessidade de exclusão. O app deve verificar se rookie-cookies importa e, se falhar, exibir instrução para o usuário adicionar a exclusão. Considerar fallback para browser-cookie3 (sem suporte a v20) ou leitura manual de cookies.

---

### [2026-11-09] Navegador Dia (Windows Store/MSIX) — cookies bloqueados e path especial
**Contexto**: Implementar extração automática de cookies do navegador Dia (The Browser Company)
**Erros encontrados**:
1. `rglob("Dia")` em AppData/Program Files causava travamento (busca recursiva lenta)
2. O Dia não está em `%LOCALAPPDATA%\Dia\...` — é um app MSIX (Windows Store) em `C:\Program Files\WindowsApps\TheBrowserCompany.Dia_*\`
3. O arquivo `Cookies` fica com lock exclusivo enquanto o Dia está aberto (OS error 32) — nem `shutil.copy2` nem `CreateFileW` com share flags funcionam
4. `rookie_cookies.from_path()` com `browser_id` + `local_state_path` juntos dá erro "Chromium credential selectors are mutually exclusive" — usar apenas `local_state_path`
5. `from_path()` retorna lista de **dicts** (não Cookie objects) — `_filter_cookies` precisa suportar ambos

**Solução**:
- Path correto do Dia (MSIX): `%LOCALAPPDATA%\Packages\TheBrowserCompany.Dia_*\LocalCache\Local\Dia\User Data\<Perfil>\Network\Cookies`
- Fechar o Dia graciosamente (`CloseMainWindow()`), aguardar até 15s, senão `Stop-Process -Force`
- Copiar `Cookies` + `Local State` para temp e ler com `rookie_cookies.from_path(cookies, local_state_path=state)`
- Reabrir o Dia automaticamente após a leitura
- Avisar o usuário na UI (confirm) antes de fechar o navegador
**Aprendizado**: Apps MSIX guardam dados em `%LOCALAPPDATA%\Packages\<PackageFamilyName>\LocalCache\`. Nunca usar rglob para localizar browsers. Sempre tratar cookies como dict OU objeto.

---

### [2026-11-09] Conectar via Dia cancelava a requisição (UI hospedada no próprio Dia)
**Contexto**: Clicar em "Conectar" com o navegador Dia selecionado
**Erro**: O Dia fechava para liberar o arquivo de cookies, a página da UI (aberta no próprio Dia) morria junto e o status ficava "desconectado" ao reabrir
**Causa**: A requisição `POST /api/auth/connect` era cancelada quando o cliente (página no Dia) desconectava; o handler não terminava de salvar o auth_cache. O usuário abria o app de novo e via "Não conectado".
**Solução**:
1. `POST /api/auth/connect` agora dispara `asyncio.create_task` e responde imediatamente com `connecting: true` (sobrevive à desconexão do cliente)
2. `GET /api/auth/status` retorna `connecting` + `error` do estado global
3. Frontend faz polling do status a cada 1s (e `checkAuth` na carga da página mostra o resultado final)
4. `_start_dia()` reabre o Dia já apontando para `http://127.0.0.1:8765`
**Aprendizado**: Nunca fazer operações longas que fecham o navegador do próprio cliente dentro do handler HTTP. Usar task em background + polling de status.

---

### [2026-11-09] `Get-Process | Where CommandLine` não funciona no PowerShell 5.1
**Contexto**: Matar apenas processos `python app.py` sem afetar outros Python
**Erro**: O filtro por `$_.CommandLine` silenciosamente não matava nada (propriedade inexistente no Get-Process do PS 5.1)
**Solução**: Usar `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` e filtrar por `CommandLine`, depois `Stop-Process -Id`.
**Aprendizado**: No PowerShell 5.1, usar CIM para obter CommandLine.

---

### [2026-11-09] Chrome com múltiplos perfis — cookies da conta errada
**Contexto**: O app pegava o primeiro perfil do Chrome que tinha cookie `ndus` (perfil do pai do usuário), enviando arquivos para a conta errada
**Erro**: Conta conectada era "Wanderson Viana" em vez de "Marlon Viana"
**Causa**: Extração automática iterava perfis sem informar/validar qual conta estava sendo usada
**Solução**: Endpoint `GET /api/auth/profiles?browser=...` lista perfis com indicador `has_terabox` (✅/❌/❔). Usuário escolhe o perfil. Validar conta via `/api/home/info` (username/uk).
**Aprendizado**: Sempre permitir seleção explícita de perfil e exibir a conta conectada na UI.

---

### [2026-11-09] scrape_jstoken retornava None (redirect /main → /portuguese/main)
**Contexto**: Conexão manual com cookies válidos falhava em obter jsToken
**Erro**: `scrape_jstoken` retornava None mesmo com cookies válidos
**Causa**: `httpx` sem `follow_redirects=True`; o Terabox retorna 302 para `/portuguese/main` quando `lang=pt`, então o HTML vinha vazio
**Solução**: Adicionar `follow_redirects=True`
**Aprendizado**: Sempre usar `follow_redirects=True` em scraping do Terabox.

---

### [2026-11-08] TeraBox não tem API oficial pública de upload
**Contexto**: Pesquisa sobre API do Terabox
**Erro**: Procurar SDK/API oficial para upload
**Causa**: TeraBox não oferece API oficial pública para upload (apenas Open Platform com OAuth para parceiros)
**Solução**: Usar a API web/PCS não oficial (como TeraboxUploaderCLI), com cookies + jsToken
**Aprendizado**: A API não oficial pode mudar sem aviso. Manter compatibilidade com o CLI original como referência.