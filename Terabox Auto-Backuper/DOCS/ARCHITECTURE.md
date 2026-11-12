# Arquitetura — Terabox Auto-Backuper

## Visão Geral

Aplicativo local com servidor FastAPI em `localhost:8765` e interface web (SPA vanilla) que gerencia sincronização de arquivos para o Terabox.

```
┌─────────────────────────────────────────────────────────────┐
│                    NAVEGADOR (localhost:8765)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SPA (index.html + app.js + restore_tree.js + css)   │   │
│  │  - Configuração de mapeamentos                       │   │
│  │  - Status de sync em tempo real (SSE/polling)        │   │
│  │  - Restaurar (processo reverso)                      │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │ HTTP (fetch)
┌─────────────────────────┼───────────────────────────────────┐
│                    FASTAPI (app.py / backend/api.py)         │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │  Rotas REST: /api/mappings, /api/sync, /api/auth,    │   │
│  │  /api/manifest, /api/settings, /api/status (SSE)      │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │  Serviços:                                           │   │
│  │  - auth.py (rookie-cookies + jsToken scraping)       │   │
│  │  - terabox_client.py (list/upload/download/...)       │   │
│  │  - sync_engine.py (fila, retry, rate-limit, dedup)    │   │
│  │  - file_monitor.py (watchdog)                        │   │
│  │  - scheduler.py (APScheduler)                        │   │
│  │  - manifest.py (manifesto de sync)                   │   │
│  │  - notifications.py (toast Windows)                  │   │
│  │  - windows_startup.py (autostart)                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │  SQLite (data/app.db)                                │   │
│  │  - mappings, files, sync_runs, settings, auth_cache   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────┼───────────────────────────────────┐
│                    TERABOX API (www.terabox.com)             │
│  - /api/list, /api/precreate, /api/create, /api/quota      │
│  - /rest/2.0/pcs/superfile2 (upload via curl)              │
│  - /main (scraping jsToken)                                │
└─────────────────────────────────────────────────────────────┘
```

## Fluxo de Autenticação

1. Usuário clica "Conectar ao Terabox"
2. `auth.py` chama `rookie_cookies.jar(browser=..., domains=["terabox.com"])`
3. Tenta Chrome → Edge → Firefox (configurável)
4. Filtra cookies: `ndus` (obrigatório), `csrfToken`, `browserid`, `lang`, `ndut_fmt`
5. GET `https://www.terabox.com/main` com cookies
6. Regex extrai `jsToken` do HTML
7. Cacheia em SQLite (`auth_cache`), TTL 5min para jsToken
8. Testa com `/api/quota` — se OK, autenticado
9. Se falhar, tenta próximo browser ou exibe instrução manual

## Fluxo de Sync (upload)

O sync é **unidirecional local → Terabox** e usa um plano calculado antes de
qualquer upload. A mesma lógica alimenta a prévia (dry-run).

1. Usuário clica "Prévia" ou "Sincronizar"; scheduler/watchdog também podem disparar.
2. `sync_engine.py` cria `sync_run` no DB.
3. `_build_plan()`:
   a. Lista os arquivos locais (`collect_local_entries`), sem seguir symlinks.
   b. Lista o remoto com `fetch_remote_snapshot()`: páginas de 1000, recursivo,
      guardando `path`, `size`, `md5`, `isdir` e `mtime`.
   c. Normaliza caminhos para POSIX e sanitiza componentes remotos (ver abaixo).
   d. Para cada arquivo local, compara **caminho exato + tamanho + MD5**:
      - remoto ausente → `upload`
      - MD5/tamanho igual → `skip`
      - conteúdo diferente → `replace` (mesmo caminho, `rtype=3`)
      - pasta no lugar de arquivo → `error`
   e. A prévia retorna contagens e os primeiros 500 itens, sem alterar nada.
4. `_run_sync()`:
   a. Cria cada diretório **uma única vez** na execução, com `rtype=0`.
   b. Executa o plano; erros temporários repetem o arquivo inteiro (até 3x,
      com backoff).
   c. Substituições são verificadas por listagem e MD5/tamanho após o upload.
   d. Renova o jsToken antes de expirar (TTL ~300s).
5. Atualiza o manifesto v2 no Terabox, com apenas arquivos confirmados no remoto.
6. Notificação toast e atualização do `sync_run`.

## Regras do Terabox Aprendidas

| Operação | `rtype` | Motivo |
|---|---|---|
| Criar pasta | `0` | Não renomeia se já existe |
| Arquivo novo | `0` | Cria no caminho exato |
| Substituir arquivo | `3` | Sobrescreve o mesmo caminho |
| **Nunca usar** | `1` | Renomeia em conflito e cria pastas/arquivos com data |

- `target_path` e todos os caminhos enviados à API são POSIX (`/`).
- Emojis e símbolos são rejeitados pelo Terabox em nomes de pasta. O app
  **sanitiza apenas o caminho remoto** (substitui por espaço e acrescenta um
  hash curto quando muda). O `local_rel_path` original fica no manifesto, então
  o Restaurar recria os nomes corretos (inclusive emojis).
- Acentos e pontuação comum (`Ação`, `Realidade; Verdade`) são preservados.
- `errno -7` e `-9` significam "não existe"; não são erro fatal ao listar uma
  pasta que ainda será criada.

## Deduplicação e Política de Conflito

Política padrão (escolhida pelo usuário): **caminho canônico + sobrescrever**.

- Um único arquivo remoto por caminho local.
- Arquivo igual → `skip`.
- Arquivo alterado → substitui no mesmo caminho, sem criar versão com data.
- Nunca apagar arquivos remotos automaticamente; o app não é um espelho com
  exclusão. Arquivos locais apagados permanecem no Terabox, mas saem do
  manifesto (o Restaurar mostra apenas o que existe no remoto).
- Criptografia Fernet usa IV aleatório; para mapeamentos criptografados a
  dedup usa o MD5 do **plaintext** guardado no banco, não o MD5 do ciphertext.
- O banco tem índice único `(mapping_id, local_rel_path)` e UPSERT de verdade.

## Seleção de Mapeamentos para o Backup

A UI da aba Configuração tem um checkbox **Sincronizar** por mapeamento. O
estado é gravado em `mappings.enabled` e é a única fonte da verdade:

- **Sincronizar Agora** e **Prévia do Sync** enviam os IDs marcados;
- **Auto-sync** (scheduler + watchdog) usa `enabled = 1`;
- Desmarcar **não apaga** nada no Terabox; apenas impede novos envios e remove
  os arquivos daquele mapeamento do manifesto no próximo sync;
- Reativar volta a incluir o mapeamento no backup e no manifesto;
- Se todos forem desmarcados, o próximo sync gera um manifesto vazio para que
  o Restaurar não continue listando arquivos de mapeamentos desativados;
- Os botões **Selecionar todos** / **Desmarcar todos** usam
  `PUT /api/mappings/bulk-enabled`, e o watchdog é recarregado.

## Seleção de Arquivos para Restaurar

- O manifesto é exibido em árvore: primeiro nível por mapeamento, depois as
  pastas reais de `local_rel_path` e, por fim, os arquivos.
- **Todos os arquivos começam selecionados** quando não existe seleção salva.
- O checkbox de pasta tem três estados (marcado, desmarcado e indeterminado) e
  seleciona/desmarca toda a subárvore.
- **Selecionar todos**, **Desmarcar todos**, **Inverter**, **Expandir tudo** e
  **Recolher tudo** operam sobre a árvore; um contador mostra “X de Y” e o
  tamanho selecionado.
- A seleção é salva em `localStorage` (`terabox_restore_selected_v2`) somente
  quando o usuário altera algo. A chave antiga (`..._v1`) é migrada quando tem
  caminhos; uma v1 vazia (`[]`) é tratada como ausência de seleção, porque era
  o estado defeituoso gravado pela versão anterior.
- Caminhos que não existem mais no manifesto são removidos da seleção.
- A seleção enviada ao backend contém apenas `remote_path` de arquivos;
  checkboxes de pasta são exclusivamente de UI.
- O Auto-sync não altera a seleção; ele só atualiza o manifesto no Terabox.
- Arquivos de mapeamentos desmarcados no backup aparecem com o aviso
  “⚠️ backup desativado”, mas continuam restauráveis manualmente.
- Cada nó de mapeamento mostra o caminho local de destino atual. Se o
  mapeamento não existir mais, o nó avisa e o arquivo não é restaurado.
- Limitação: a seleção é local ao navegador/perfil, não viaja para outro PC.

## Rate Limiting e Otimização

- **Pacing**: mínimo 400ms entre chamadas à API do Terabox
- **Concorrência**: worker pool configurável (padrão 2-3)
- **Retry**: até 3 tentativas com backoff exponencial + jitter para erros
  transitórios (timeout, 5xx, curl, rate limit)
- **Token**: renovação automática antes dos 5 minutos e em erro de autenticação
- **Deduplicação**: caminho exato + tamanho + MD5; cache no banco evita reler
  arquivos cujo tamanho/mtime não mudaram
- **Verificação**: obrigatória em substituições; arquivos novos confiam no MD5
  retornado pelo upload (evita uma listagem extra por arquivo no 1º backup)
- **Debounce watchdog**: 2s após último evento de filesystem
- **Sync automático**: scheduler e watchdog só disparam se `auto_sync=true`

## Watchdog (file_monitor.py)

- Usa `watchdog.observers.Observer` com `FileSystemEventHandler`
- Monitora cada pasta mapeada; para mapeamento de arquivo único, vigia a pasta pai
- Eventos: created, modified, moved → dispara sync (debounce de 2s)
- O handler roda na thread do watchdog; a task é criada no event loop principal
  via `loop.call_soon_threadsafe` (evita `RuntimeError: no current event loop`)
- Só dispara se `auto_sync=true`
- Ignora arquivos temporários (.tmp, .part, ~$, .chunk_*)

## Scheduler (scheduler.py)

- APScheduler AsyncIOScheduler
- Job: sync completo a cada N minutos (configurável; padrão 30)
- Inicia com o app, para ao encerrar
- Ativar/desativar "Sync automático" nas Configurações adiciona/remove o job

## Manifesto

- Arquivo `_terabox_autobackup_manifest.json` na raiz do Terabox
- Versão 2.0; upload com `rtype=3` (sobrescreve o anterior)
- Inclui apenas arquivos cuja existência remota foi confirmada
- Estrutura:
```json
{
  "version": "2.0",
  "generated_at": "2026-11-09T20:46:44",
  "run_started_at": "2026-11-09T20:46:38",
  "files": [
    {
      "local_rel_path": "00 - 📥 Inbox/nota 📝.txt",
      "remote_path": "/backup/00 - Inbox_a19902/nota_9bac5f.txt",
      "size": 1234,
      "md5": "md5-do-plaintext",
      "remote_md5": "md5-do-arquivo-remoto",
      "mapping_id": 1,
      "mapping_name": "Documentos",
      "synced_at": "2026-11-09T20:46:41",
      "encrypted": false
    }
  ],
  "directories": []
}
```
- `local_rel_path` preserva o nome original (com emoji/acentos) para o Restaurar
- `remote_path` é o caminho sanitizado realmente usado no Terabox

## Processo Reverso (Restaurar)

1. Usuário clica "Restaurar" na UI
2. Backend baixa o manifesto do Terabox (`/api/filemetas` → dlink)
3. Exibe a árvore por mapeamento/pastas com todos os arquivos selecionados por
   padrão; a seleção é lembrada no navegador
4. Usuário ajusta a seleção. Não existe mais pasta de destino manual: cada
   arquivo usa a pasta original do mapeamento
5. Backend monta um plano somente leitura (`POST /api/restore/plan`) com:
   destino de cada arquivo, se ele será criado ou substituído, e erros
6. Se a configuração `restore_confirm_overwrite` estiver ligada, a UI pede
   confirmação antes de substituir arquivos existentes
7. Backend baixa cada arquivo via dlink e grava no destino original
8. Se criptografado, baixa o `.enc` para temp, descriptografa para um
   `.restore-part` na mesma pasta e faz `os.replace` atômico
9. Resultado por arquivo (criado/substituído/erro) é devolvido à UI

## Resolução de Destino no Restaurar

O destino não vem da UI; vem do mapeamento atual em Configuração.

| Tipo de mapeamento | Destino |
|---|---|
| Pasta | `mapping.local_path / local_rel_path` |
| Arquivo único | `mapping.local_path` (o arquivo em si) |

Regras:

- `mapping.is_file` é persistido no banco para diferenciar arquivo único de
  pasta mesmo quando o arquivo original foi apagado.
- O mapeamento é resolvido por `mapping_id` validado contra o caminho remoto ou
  nome; se o ID não servir (outro PC), usa o prefixo remoto mais longo e, por
  último, o nome único. Nunca usa apenas o ID.
- Pastas existentes são mescladas. Nada é apagado.
- Arquivo no mesmo caminho vira `replace`; pasta no lugar de arquivo (ou
  vice-versa) vira erro.
- `local_rel_path` precisa ser relativo e seguro. O destino resolvido ainda é
  conferido contra `mapping.local_path` para bloquear `..`, unidades diferentes
  e symlinks/junções que escapem da pasta.
- Dois arquivos selecionados para o mesmo destino geram erro.
- Após um restore bem-sucedido, o cache local (`files`) é atualizado com
  tamanho, MD5 e mtime do arquivo restaurado, para o próximo sync não reenviar
  conteúdo idêntico.

> O agrupamento por mapeamento é apenas visual. A estrutura preservada é a do
> `local_rel_path` dentro de cada mapeamento; o nome do mapeamento não vira
> pasta no destino.

## Autostart Windows

- `windows_startup.py` registra no `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Chave: `TeraboxAutoBackuper` → `pythonw.exe app.py` (ou caminho do exe)
- Opção de ativar/desativar na UI
- Ao iniciar, abre navegador automaticamente (`webbrowser.open`)

## Decisões de Design

1. **curl para upload binário**: mais confiável que requests para multipart grande (como no CLI original)
2. **httpx para API calls**: async nativo, melhor que requests em contexto async
3. **SQLite local**: zero infraestrutura, backup trivial, suficiente para uso single-user
4. **Frontend vanilla**: sem build step, portável, fácil de manter
5. **rookie-cookies**: única lib que suporta Chrome App-Bound v20 (necessário para Chrome 127+)
6. **jsToken scraping**: como terabox-webdav-worker, evita depender do usuário colar manualmente
7. **Fernet para criptografia**: simples, seguro, compatível com o CLI original
8. **Subprocessos ocultos**: como o app roda via `pythonw.exe`, qualquer processo de console (`curl`, `tasklist`, `powershell`) usa `backend/process_utils.run_hidden()` com `CREATE_NO_WINDOW` para não abrir janelas piscando
9. **Plano antes da execução**: a prévia (dry-run) e o sync real usam o mesmo `_build_plan`, evitando divergência entre o que é mostrado e o que é feito
10. **Sanitização só no remoto**: emojis são removidos do caminho do Terabox, mas o nome local original fica no manifesto para restauração fiel
11. **Sem exclusão automática**: backup unidirecional seguro; o app não apaga arquivos remotos quando o local é apagado