# Tarefas do Projeto — Terabox Auto-Backuper

> Lista ordenada de tarefas. Cada tarefa tem descrição e como proceder.
> Marque como concluída ([x]) ao finalizar. Commit ao final de cada tarefa.

## Fase 1 — Fundação (MVP)

### T1. Estrutura de pastas e git init ✅
- **Status**: Concluída (2026-11-08)
- **Descrição**: Criar toda a estrutura de pastas, .gitignore, requirements.txt, AGENTS.md, DOCS/
- **Como proceder**: Ver AGENTS.md seção 3

### T2. Backend FastAPI básico + SQLite + modelos ✅
- **Status**: Concluída (2026-11-08)
- **Descrição**: Criar app.py (entry point), backend/__init__.py, backend/config.py, backend/database.py, backend/models.py, backend/api.py com rotas básicas (health check, settings)
- **Como proceder**:
  - app.py: cria FastAPI app, monta frontend estático, inicia uvicorn em 127.0.0.1:8765, abre navegador
  - database.py: aiosqlite, cria tabelas (mappings, files, sync_runs, settings, auth_cache)
  - models.py: Pydantic models para request/response
  - api.py: router com endpoints básicos
- **Referência**: DOCS/ARCHITECTURE.md seção "Visão Geral"

### T3. Frontend básico (SPA) ✅
- **Status**: Concluída (2026-11-08)
- **Descrição**: index.html + css/style.css + js/app.js com layout básico, navegação por abas (Configuração, Status, Restaurar), formulário de mapeamentos
- **Como proceder**: SPA vanilla, fetch para API, sem framework
- **Referência**: DOCS/API_REFERENCE.md

### T4. Cliente Terabox (terabox_client.py) ✅
- **Status**: Concluída (2026-11-08)
- **Descrição**: Portar lógica do TeraboxUploaderCLI para classe async: list, precreate, upload (curl), create, quota, fetch_remote_directory
- **Como proceder**: Usar httpx para API calls, subprocess curl para upload. Reutilizar código do CLI (main.py)
- **Referência**: DOCS/TERABOX_API.md, main.py do TeraboxUploaderCLI

### T5. Autenticação automática (auth.py) ✅
- **Status**: Concluída (2026-11-08) - requer login no Terabox no navegador
- **Descrição**: Extrair cookies via rookie-cookies, raspar jsToken do HTML /main, cachear em SQLite
- **Como proceder**:
  - rookie_cookies.jar(browser=..., domains=["terabox.com"])
  - Filtrar cookies necessários
  - GET /main com cookies, regex para jsToken
  - Cachear em auth_cache
- **Referência**: DOCS/ARCHITECTURE.md "Fluxo de Autenticação"

### T6. Sync manual (sync_engine.py) ✅
- **Status**: Concluída (2026-11-08) - testado parcialmente (auth pendente)
- **Descrição**: Motor de sync com fila, retry, rate-limit, deduplicação por MD5. Botão "Sincronizar agora" na UI
- **Como proceder**: Ver DOCS/ARCHITECTURE.md "Fluxo de Sync"
- **Depende de**: T4, T5

### T7. Notificações toast (notifications.py) ✅
- **Status**: Concluída (2026-11-08)
- **Descrição**: Toast do Windows via winotify ao concluir/falhar sync
- **Como proceder**: winotify.Notification com título, mensagem, duração
- **Depende de**: T6

## Fase 2 — Automação

### T8. Watchdog (file_monitor.py) ✅
- **Status**: Concluída (2026-11-08) - integrado ao app e mapeamentos
- **Descrição**: Monitorar pastas mapeadas com watchdog, debounce 2s, enfileirar sync incremental
- **Depende de**: T6

### T9. APScheduler (scheduler.py) ✅
- **Status**: Concluída (2026-11-08) - sync periódico configurável
- **Descrição**: Sync completo periódico (configurável, default 30min)
- **Depende de**: T6

### T10. Fila otimizada + retry + rate-limit ✅
- **Status**: Concluída (2026-11-08) - rate-limit 400ms, retry 3x, worker pool
- **Descrição**: Refinar sync_engine com worker pool, pacing 400ms, retry com backoff
- **Depende de**: T6

### T11. Autostart Windows (windows_startup.py) ✅
- **Status**: Concluída (2026-11-08) - registro HKCU, toggle na UI
- **Descrição**: Registrar/desregistrar no HKCU\Run
- **Depende de**: T2

### T12. Manifesto + processo reverso (Restaurar) ✅
- **Status**: Concluída (2026-11-08) - manifesto gerado, download seletivo implementado
- **Descrição**: Gerar manifesto no Terabox, botão Restaurar com download seletivo
- **Depende de**: T4, T6

## Fase 3 — Polimento

### T13. Criptografia opcional por mapeamento ✅
- **Status**: Concluída (2026-11-08) - Fernet, chave nas settings
- **Descrição**: Fernet encryption/decryption por mapeamento
- **Depende de**: T4

### T14. Histórico de sync runs + logs na UI ✅
- **Status**: Concluída (2026-11-08) - endpoint /sync/history + UI
- **Descrição**: Exibir histórico de syncs e logs na interface
- **Depende de**: T6

### T15. Testes
- **Status**: Pendente
- **Descrição**: Testes unitários e de integração
- **Depende de**: todas

### T16. Corrigir janelas de CMD piscando no sync ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Executar `curl`, `tasklist` e `powershell` sem abrir janela de console quando o app roda via `pythonw.exe`
- **Como proceder**: Usar `backend/process_utils.run_hidden()` em todos os subprocessos de console; manter o Dia visível ao reabrir
- **Teste**: 12 arquivos enviados via app iniciado pelo `INICIAR.bat`, com 0 janelas extras de console
- **Depende de**: T4, T5

### T17. Corrigir pastas duplicadas e substituição de arquivos ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Pastas eram criadas por arquivo com `rtype=1`, gerando cópias com data. Arquivos alterados nunca eram substituídos.
- **Solução**:
  - Pastas com `rtype=0`, uma vez por execução
  - Arquivo novo `rtype=0`; substituição `rtype=3`
  - Caminho exato + tamanho + MD5 (não mais por nome)
  - `target_path` POSIX
  - Índice único `(mapping_id, local_rel_path)` e UPSERT
- **Teste**: 2º sync sem pastas novas; arquivo alterado substituído no mesmo caminho; mesmo nome em pastas diferentes enviado corretamente
- **Depende de**: T6

### T18. Prévia (dry-run) do sync ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Mostrar uploads, substituições, ignorados e erros antes de executar
- **Solução**: `POST /api/sync/preview` + botão "Prévia do Sync" na UI; a mesma função `_build_plan` alimenta prévia e execução
- **Depende de**: T17

### T19. Importação de lista CSV ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Colar lista `origem; destino` e criar mapeamentos em lote
- **Solução**: `backend/csv_import.py` + `POST /api/mappings/import-csv` + textarea na UI; aceita pasta ou arquivo, valida e mostra erros por linha
- **Teste**: importação de pasta + arquivo única; `dry_run` não altera o banco
- **Depende de**: T3

### T20. Criptografia e retomada ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Corrigir upload criptografado (usava plaintext/tamanho errado), chunks fora da pasta de origem, refresh de jsToken e retry
- **Solução**:
  - `upload_path`/`upload_size` em todo o fluxo
  - Chunks em `temp/run_<id>/`
  - Falha de criptografia falha o arquivo (sem fallback silencioso)
  - Retry do arquivo inteiro + backoff; jsToken renovado
- **Teste**: upload `.enc`, restore descriptografado, 2º sync skip
- **Depende de**: T13, T17

### T21. Restaurar preservando estrutura e nomes originais ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Restaurar em `destino/local_rel_path` e recriar nomes com emoji
- **Solução**: Manifesto v2 com `local_rel_path` original; download via `/api/filemetas`; sanitização só no caminho remoto
- **Teste**: pasta `📥 Inbox/nota 📝.txt` restaurada com o nome original
- **Depende de**: T12, T17

### T22. Sanitização de nomes remotos ✅
- **Status**: Concluída (2026-11-09)
- **Descrição**: Terabox rejeita emojis em nomes de pasta (`errno=-7`)
- **Solução**: `sanitize_remote_component()` substitui símbolos, anexa hash curto e mantém acentos/`;`; o nome local original fica no manifesto
- **Teste**: sync de `📥 Inbox` → `Inbox_hash`; restore devolve `📥 Inbox`
- **Depende de**: T17, T21

## Como proceder em cada tarefa

1. Leia a tarefa e suas dependências
2. Leia os arquivos de referência indicados
3. Implemente
4. Teste (se possível)
5. Atualize o status para ✅
6. Commit: `git add -A && git commit -m "feat: T{N} - descrição"`
7. Se encontrar erros, registre em DOCS/ERRORS_LEARNINGS.md