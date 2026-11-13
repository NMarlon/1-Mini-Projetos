# Referência da API Local — Terabox Auto-Backuper

> Endpoints do servidor FastAPI em `http://127.0.0.1:8765`

## Autenticação

### POST /api/auth/connect
Conecta ao Terabox extraindo cookies do navegador.
- **Body**: `{ "browser": "chrome" | "edge" | "firefox" | "auto" }`
- **Response**: `{ "status": "ok", "browser": "chrome", "cookies_found": 5 }`

### GET /api/auth/status
Verifica status de autenticação.
- **Response**: `{ "authenticated": true, "browser": "chrome", "jstoken_expires_in": 280 }`

### POST /api/auth/disconnect
Desconecta (limpa cache de auth).

## Mapeamentos

### GET /api/mappings
Lista todos os mapeamentos.

### POST /api/mappings
Cria novo mapeamento. A origem pode ser pasta ou arquivo único.
- **Body**: `{ "name": "Documentos", "local_path": "C:/docs", "remote_path": "/backup/docs", "include_subfolders": true, "encrypt": false, "enabled": true, "is_file": null }`
- `is_file` é opcional: `true` = arquivo único, `false` = pasta, `null` =
  detectar pelo filesystem (se não existir, assume pasta).
- A origem pode não existir. Pasta é criada na hora; arquivo único cria apenas
  a pasta-pai e nunca um arquivo vazio.
- O `remote_path` é normalizado e sanitizado (emoji vira hash); a resposta mostra o caminho final.

### PUT /api/mappings/{id}
Atualiza mapeamento. Se origem, destino ou criptografia mudarem, o cache de
arquivos daquele mapeamento é limpo.

### PUT /api/mappings/bulk-enabled
Liga/desliga vários mapeamentos de uma vez. É o endpoint usado pelos botões
**Selecionar todos** / **Desmarcar todos**.
- **Body**: `{ "ids": [1, 2, 3], "enabled": true }`
- **Response**: `{ "updated": 3, "enabled": true, "mappings": [...] }`
- O campo `enabled` é a fonte da verdade: o sync manual envia apenas os IDs
  marcados e o Auto-sync lê `enabled = 1` do banco.

### DELETE /api/mappings/{id}
Remove mapeamento e seus registros de arquivos.

### POST /api/mappings/import-csv
Importa uma lista colada no formato `origem; destino`, uma por linha.
- **Body**:
  ```json
  {
    "csv": "C:\\Docs; /Backup/Docs\nC:\\Foto.jpg; /Backup/Fotos",
    "include_subfolders": true,
    "encrypt": false,
    "enabled": true,
    "dry_run": true
  }
  ```
- **Response**: `{ "dry_run": true, "parsed": [...], "created": [], "would_create": [...], "skipped": [...], "errors": [...] }`
- `dry_run=true` apenas valida e mostra o que seria criado.
- Aceita `;`, tabulação ou vírgula (com aspas). Linhas `#` são comentários.
- A origem pode ser pasta ou arquivo; o destino é sempre uma pasta remota.
- A origem pode não existir ainda. Terceiro campo opcional:
  `C:\Saves\Meu Mundo; /Backup/Saves; pasta` ou
  `C:\Saves\Meu Mundo\level.dat; /Backup/Saves; arquivo`.
  Sem o terceiro campo, detecta pelo filesystem e assume pasta se não existir.
- `warnings` em `parsed` avisa quando uma pasta/pasta-pai será criada.

## Sync

### POST /api/sync/preview
Calcula o plano (dry-run) sem enviar nada.
- **Body**: `{ "mapping_ids": [1, 2] }`
- `mapping_ids` ausente/`null` = todos os mapeamentos habilitados (Auto-sync).
- `mapping_ids: []` = nenhum mapeamento; a prévia retorna vazio.
- **Response**:
  ```json
  {
    "files_total": 100,
    "counts": { "upload": 20, "replace": 3, "skip": 77, "error": 0 },
    "items": [ { "local_rel_path": "...", "remote_path": "...", "action": "upload", "reason": "..." } ],
    "truncated": false,
    "directories": 12,
    "errors": [],
    "mappings": []
  }
  ```

### POST /api/sync/start
Inicia sync manual.
- **Body**: `{ "mapping_ids": [1, 2] }`
- Envie apenas os IDs marcados na UI. Sem `mapping_ids`, usa todos os
  mapeamentos com `enabled = 1` (mesma regra do Auto-sync).
- **Response**: `{ "run_id": 42, "status": "started" }`

### POST /api/sync/stop
Para sync em andamento. A parada é verificada entre arquivos e entre pastas.

### GET /api/sync/status
Status do sync atual.
- **Response**: `{ "running": true, "run_id": 42, "files_total": 100, "files_uploaded": 45, "files_failed": 2, "files_skipped": 10, "current_file": "doc.pdf", "errors": [ { "file": "...", "error": "..." } ] }`

### GET /api/sync/history
Histórico de sync runs.
- **Query**: `?limit=20&offset=0`

### GET /api/sync/stream (SSE)
Stream de eventos de sync em tempo real (Server-Sent Events).

## Restaurar (Processo Reverso)

### GET /api/restore/manifest
Baixa e retorna o manifesto do Terabox.

### Observação sobre a seleção de restauração
A aba **Restaurar** mostra o manifesto em árvore (mapeamento → pastas →
arquivos) e seleciona tudo por padrão. A seleção é persistida no `localStorage`
do navegador (`terabox_restore_selected_v2`) somente após uma alteração do
usuário. A chave antiga `terabox_restore_selected_v1` é migrada quando contém
caminhos; uma v1 vazia é tratada como ausência de seleção. A seleção sobrevive a
recarregar o manifesto, trocar de aba, recarregar a página e reiniciar o app.
Ela não é enviada ao Terabox; é uma preferência local do navegador/perfil.

### POST /api/restore/plan
Prévia da restauração. Não baixa arquivos nem cria/altera nada no disco.
- **Body**: `{ "files": ["/remote/path1", "/remote/path2"] }`
- Resolve o mapeamento atual de cada arquivo (`mapping_id`, prefixo remoto ou
  nome único) e devolve o destino local, o tipo (`create`/`replace`/`error`) e
  os motivos de erro.
- **Response**:
```json
{
  "summary": {
    "total": 3,
    "create": 1,
    "replace": 1,
    "errors": 1,
    "mappings": 2,
    "missing_mappings": 0,
    "duplicates": 0,
    "encrypted": 0
  },
  "files": [
    {
      "remote_path": "/remote/path1",
      "mapping_id": 25,
      "mapping_uid": "6f1c2b7e-...",
      "mapping_name": "saves",
      "local_path": "C:\\...\\saves\\0.msav",
      "local_rel_path": "0.msav",
      "action": "replace",
      "exists": true,
      "encrypted": false,
      "error": null,
      "error_code": null,
      "mapping_is_file": false,
      "size": 1234
    }
  ]
}
```

### POST /api/restore/start
Inicia a restauração em background e devolve imediatamente.
- **Body**: `{ "files": ["/remote/path1"], "allow_overwrite": true }`
- O job baixa o manifesto, monta o plano e valida conflitos. Se
  `allow_overwrite=false` e houver arquivo existente, o job termina em
  `phase="failed"` com mensagem de confirmação.
- Retorna `409` se já existir uma restauração em andamento e `400` se a lista
  estiver vazia.
- **Response**: `{ "status": "started", "job_id": "abc123", "files_total": 1 }`

### GET /api/restore/status
Progresso do job de restauração. A UI consulta a cada **0,3s** enquanto
`running=true`.
- **Response**:
```json
{
  "running": true,
  "job_id": "abc123",
  "phase": "downloading",
  "started_at": "2026-11-12T21:30:00",
  "finished_at": null,
  "elapsed_seconds": 12.4,
  "files_total": 100,
  "files_done": 37,
  "files_created": 30,
  "files_replaced": 7,
  "files_failed": 0,
  "files_invalid": 2,
  "current_index": 38,
  "current_file": "C:\\...\\saves\\0.msav",
  "current_mapping": "saves",
  "current_remote_path": "/Backup/saves/0.msav",
  "cancel_requested": false,
  "error": null,
  "errors": [],
  "errors_truncated": false,
  "summary": null
}
```
- Fases: `idle`, `preparing`, `downloading`, `cancelling`, `finished`,
  `cancelled`, `failed`.
- `errors` guarda até 200 falhas com `remote_path`, `local_path`,
  `mapping_name` e `error`; `errors_truncated` indica que houve mais.
- `summary` (`total`, `restored`, `created`, `replaced`, `failed`, `invalid`,
  `cancelled`) só é preenchido ao terminar.

### POST /api/restore/stop
Pede o cancelamento entre arquivos. Arquivos já baixados são mantidos.
- **Response**: `{ "status": "cancelling" }` ou `{ "status": "idle" }`.

### POST /api/restore/download
Restauração seletiva **bloqueante**, mantida por compatibilidade. Prefira
`/api/restore/start` + `/api/restore/status` para progresso ao vivo.
- **Body**: `{ "files": ["/remote/path1"], "allow_overwrite": true }`
- `files` deve conter apenas `remote_path` de arquivos; caminhos de pasta da
  árvore não são enviados.
- Mapeamento de pasta: grava em `mapping.local_path / local_rel_path`,
  mesclando com o que já existe. Mapeamento de arquivo único: grava exatamente
  em `mapping.local_path`.
- Arquivos existentes no mesmo caminho são substituídos. Se
  `allow_overwrite=false` e houver conflito, retorna **409** com
  `detail.summary` e `detail.conflicts`, sem baixar nada.
- Caminhos absolutos, com `..` ou que escapem da pasta original são rejeitados.
  Arquivos criptografados são baixados como `.enc` e descriptografados no
  destino.
- **Response**:
```json
{
  "summary": { "restored": 1, "created": 0, "replaced": 1, "failed": 0 },
  "results": [
    {
      "remote_path": "/remote/path1",
      "local_path": "C:\\...\\saves\\0.msav",
      "success": true,
      "overwritten": true,
      "action": "replaced",
      "error": null
    }
  ]
}
```

## Configuração remota de mapeamentos

### GET /api/remote-config
Status do cadastro remoto.
- **Query**: `?check_remote=true` também consulta o Terabox.
- **Response** (resumo):
```json
{
  "enabled": true,
  "auto_save": true,
  "path": "/config-terabox-auto-backup/terabox-auto-backup.json",
  "shortcut_path": "/_terabox_autobackup_config.json",
  "machine_id": "...",
  "machine_name": "Marlon-PC",
  "mapping_count": 18,
  "last_saved_at": "2026-11-12T12:00:00",
  "last_error": null,
  "remote": {
    "checked": true,
    "exists": true,
    "path": "/config-terabox-auto-backup/terabox-auto-backup.json",
    "source": "configured",
    "error": null,
    "mappings_total": 18,
    "needs_import": false,
    "import_summary": { "new": 0, "existing": 18, "conflicts": 0 }
  }
}
```
- `source` pode ser `configured` (caminho salvo) ou `shortcut` (atalho da raiz).

### POST /api/remote-config/save
Baixa, mescla e grava o arquivo remoto agora.
- **Body**: `{ "force": false }`
- `force=true` é necessário para substituir uma configuração remota inválida ou
  uma lista local vazia sobre uma configuração não vazia.
- Retorna `409` quando a gravação exige confirmação; `401` sem autenticação.
- **Response**: `{ "saved": true, "changed": true, "path": "...", "config_hash": "...", "mappings": 18, "shortcut_written": true }`

### POST /api/remote-config/import/plan
Baixa a configuração remota e monta a revisão de importação para este PC.
- Não altera o banco nem o disco.
- **Response**:
```json
{
  "exists": true,
  "path": "/config-terabox-auto-backup/terabox-auto-backup.json",
  "source": "configured",
  "config_hash": "...",
  "summary": { "total": 18, "new": 18, "existing": 0, "conflicts": 0 },
  "mappings": [
    {
      "uid": "...",
      "name": "Fotos",
      "remote_path": "/Backup/Fotos",
      "is_file": false,
      "status": "new",
      "local_path": "C:\\Users\\Marlon\\Fotos",
      "original_local_path": "C:\\Users\\marlo\\Fotos",
      "rebase": {
        "foreign_user": "marlo",
        "current_user": "Marlon",
        "foreign_root": "C:\\Users\\marlo",
        "current_root": "C:\\Users\\Marlon",
        "suggested_path": "C:\\Users\\Marlon\\Fotos"
      },
      "current_local_path": null,
      "path_error": null,
      "warnings": [
        "O caminho sugerido usava o perfil do usuário 'marlo' de outro computador. Foi ajustado para o seu perfil 'Marlon': C:\\Users\\Marlon\\Fotos"
      ],
      "other_machines": [
        { "machine_name": "PC-antigo", "local_path": "C:\\Users\\Marlon\\Fotos" }
      ],
      "selected": true,
      "blocked": false
    }
  ]
}
```
- `status`: `new`, `existing` ou `conflict`.
- `path_error` indica que o caminho sugerido precisa ser corrigido.
- `needs_update` indica que um mapeamento existente difere do arquivo remoto.
- `original_local_path`/`rebase` aparecem quando o caminho sugerido vinha do
  perfil de outro usuário do Windows e foi ajustado para o perfil atual.
- “Selecionar todos” no frontend ignora linhas `blocked` e linhas com
  `path_error`.

### POST /api/remote-config/import
Importa somente as linhas confirmadas na revisão.
- **Body**:
```json
{
  "config_hash": "hash-devolvido-pelo-plano",
  "mappings": [
    { "uid": "...", "local_path": "D:\\Fotos" }
  ],
  "adopt_path": true
}
```
- `config_hash` evita importar uma revisão desatualizada; se o arquivo mudou,
  retorna `409`.
- `adopt_path=true` adota o caminho descoberto pelo atalho nas configurações.
- Retorna `created`, `updated`, `skipped`, `errors`, `warnings` e, quando
  possível, `remote_config_saved`.
- `warnings` são avisos não fatais: normalmente “não foi possível criar a
  pasta”, mas o mapeamento foi importado mesmo assim. Cada item tem
  `{ "uid": "...", "warning": "..." }`.
- Nada é importado sem esta chamada explícita.

## Configurações

### GET /api/settings
Retorna configurações globais.

### PUT /api/settings
Atualiza configurações.
- **Body**: `{ "sync_interval_minutes": 30, "auto_sync": true, "notifications": true, "max_concurrent_uploads": 3, "autostart": false, "restore_confirm_overwrite": true, "machine_name": "Marlon-PC", "remote_config_enabled": true, "remote_config_path": "/config-terabox-auto-backup/terabox-auto-backup.json", "remote_config_auto_save": true }`
- `auto_sync=false` remove o job do scheduler **e** impede o watchdog de
  disparar sync por alteração de arquivo.
- `restore_confirm_overwrite` controla se o Restaurar pergunta antes de
  substituir arquivos existentes. Padrão: `true`.
- `machine_name` é o nome amigável deste PC no arquivo remoto.
- `remote_config_path` precisa terminar em `.json` e não pode ser a raiz.
- `remote_config_auto_save=false` mantém o botão **Salvar agora**, mas desliga
  o salvamento após alterações e no fim do sync.

## Sistema

### GET /api/system/pick-folder
Abre o seletor nativo de pastas do Windows.
- **Response**: `{ "path": "C:\\..." }` (vazio se cancelado)

### GET /api/system/pick-file
Abre o seletor nativo de arquivos do Windows. É usado na revisão da
configuração remota para mapeamentos de arquivo único.
- **Response**: `{ "path": "C:\\...\\arquivo.ext" }` (vazio se cancelado)

## Status

### GET /api/health
Health check. `{ "status": "ok", "version": "0.3.5" }`

### GET /api/status
Status geral do app (auth, sync, scheduler, watchdog).