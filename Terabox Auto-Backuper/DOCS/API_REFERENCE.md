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
- **Body**: `{ "name": "Documentos", "local_path": "C:/docs", "remote_path": "/backup/docs", "include_subfolders": true, "encrypt": false, "enabled": true }`
- O `remote_path` é normalizado e sanitizado (emoji vira hash); a resposta mostra o caminho final.

### PUT /api/mappings/{id}
Atualiza mapeamento. Se origem, destino ou criptografia mudarem, o cache de
arquivos daquele mapeamento é limpo.

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

## Sync

### POST /api/sync/preview
Calcula o plano (dry-run) sem enviar nada.
- **Body**: `{ "mapping_ids": [1, 2] | null (todos) }`
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
- **Body**: `{ "mapping_ids": [1, 2] | null (todos) }`
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

### POST /api/restore/download
Inicia download seletivo.
- **Body**: `{ "files": ["/remote/path1", "/remote/path2"], "destination": "C:/restore", "preserve_structure": true }`
- Com `preserve_structure=true`, usa o `local_rel_path` do manifesto,
  recriando as pastas originais (inclusive nomes com emoji). Arquivos
  criptografados são baixados como `.enc` e descriptografados no destino.
- **Response**: `{ "results": [ { "remote_path": "...", "local_path": "...", "success": true, "error": null } ] }`

## Configurações

### GET /api/settings
Retorna configurações globais.

### PUT /api/settings
Atualiza configurações.
- **Body**: `{ "sync_interval_minutes": 30, "auto_sync": true, "notifications": true, "max_concurrent_uploads": 3, "autostart": false }`
- `auto_sync=false` remove o job do scheduler **e** impede o watchdog de
  disparar sync por alteração de arquivo.

## Status

### GET /api/health
Health check. `{ "status": "ok", "version": "0.1.0" }`

### GET /api/status
Status geral do app (auth, sync, scheduler, watchdog).