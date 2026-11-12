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

### T23. Seleção persistente de mapeamentos e arquivos de restauração ✅
- **Status**: Concluída (2026-11-11)
- **Descrição**: Poder marcar/desmarcar o que entra no backup e o que será restaurado, mantendo a escolha entre execuções.
- **Solução**:
  - Checkbox **Sincronizar** por mapeamento, persistido em `mappings.enabled`
  - `PUT /api/mappings/bulk-enabled` para selecionar/desmarcar todos
  - Sync manual e prévia enviam apenas os IDs marcados; Auto-sync usa `enabled = 1`
  - Manifesto vazio quando nenhum mapeamento está selecionado
  - Checkboxes da aba Restaurar persistidos em `localStorage`
  - Botões Selecionar todos/Desmarcar todos/Inverter e contador
  - Aviso “backup desativado” para arquivos de mapeamentos desmarcados
- **Teste**: desmarcar mapeamento → prévia vazia; reativar → volta; seleção de restauração sobrevive a reload e a novo sync; 31 testes unitários passando
- **Depende de**: T17, T21

### T24. Árvore de restauração por pastas e seleção total por padrão ✅
- **Status**: Concluída (2026-11-12)
- **Descrição**: A aba Restaurar exibia milhares de arquivos em uma lista plana e todos desmarcados; era inviável selecionar e conferir a estrutura.
- **Solução**:
  - Árvore em níveis: mapeamento → pastas de `local_rel_path` → arquivos
  - Pastas recolhidas por padrão; clique na seta/nome expande
  - Checkbox de pasta em três estados (marcado/desmarcado/indeterminado)
  - Todos os arquivos selecionados por padrão
  - Toolbar com Selecionar todos, Desmarcar todos, Inverter, Expandir tudo e Recolher tudo
  - Contador por pasta e global, com tamanho selecionado
  - Persistência em `terabox_restore_selected_v2`; migração da v1 e tratamento de v1 vazia como ausência de seleção
  - Confirmação antes de restaurar muitos arquivos ou achatar a estrutura
  - `restore_tree.js` com helpers puros testáveis
  - Validação de caminho relativo no backend (substituída na T25 pela resolução por mapeamento)
- **Teste**: 39 testes Python (`python -m unittest discover -s tests`) e 10 testes Node (`node --test tests/test_restore_tree.cjs`); validação no navegador com 5.282 arquivos, seleção total, tri-state, persistência de vazio e payload apenas com `remote_path`
- **Depende de**: T21, T23

### T25. Restaurar nas pastas originais com mesclagem e confirmação ✅
- **Status**: Concluída (2026-11-12)
- **Descrição**: O Restaurar pedia uma pasta de destino manual, embora o destino correto já esteja em `mappings.local_path`. Era possível restaurar no lugar errado ou sobrescrever sem aviso.
- **Solução**:
  - Remove o campo de pasta de destino e a opção de achatar a estrutura
  - Mapeamento de pasta: restaura em `local_path/local_rel_path`
  - Mapeamento de arquivo único: restaura em `local_path` (o próprio arquivo)
  - Mescla pastas existentes; nunca apaga arquivos não selecionados
  - Arquivo no mesmo caminho vira `replace` e é reportado
  - `POST /api/restore/plan` mostra criar/substituir/erros antes de baixar
  - Configuração `restore_confirm_overwrite` (padrão ligada) controla a pergunta
  - `allow_overwrite=false` retorna 409 se houver conflito, sem baixar nada
  - Resolve mapeamento por ID validado, prefixo remoto e nome único (outro PC)
  - Persiste `mappings.is_file` para recriar arquivo único mesmo se apagado
  - Atualiza o cache `files` após restaurar para evitar reenvio desnecessário
  - `backend/restore.py` com resolução de destino e planejamento puros
- **Teste**: 59 testes Python e 10 testes Node; plano real com 5.282 arquivos e 18 mapeamentos: 5.281 `replace`, 1 `create`, 0 erros; migração testada em banco temporário e em cópia do banco real
- **Depende de**: T21, T24

### T26. Configuração remota de mapeamentos para PC novo ✅
- **Status**: Concluída (2026-11-12)
- **Descrição**: Um PC novo sem banco local não sabia para onde cada pasta remota deveria voltar. Era preciso recriar os mapeamentos manualmente.
- **Solução**:
  - `mappings.uid` estável com migração e índice único
  - `backend/remote_config.py` com schema, validação, merge por máquina, hash e plano de importação puros
  - Arquivo padrão `/config-terabox-auto-backup/terabox-auto-backup.json` e atalho fixo `/_terabox_autobackup_config.json`
  - `local_paths` por `machine_id`; cada PC grava só a sua entrada
  - Auto-save com debounce, no fim do sync e botão **Salvar agora**
  - Proteção contra config remota vazia/inválida e contra apagar o caminho de outros PCs
  - Banner de descoberta e diálogo de revisão com seleção por linha, rebase de prefixo e avisos
  - Importação explícita com `config_hash`, detecção por `uid`/fingerprint e adoção do caminho descoberto pelo atalho
  - Manifesto inclui `mapping_uid`/`mapping_remote_path`; Restaurar prioriza o `uid`
  - Arquivo único pode apontar para arquivo inexistente; pasta no lugar do arquivo é rejeitada
  - `remote_config.js` com helpers puros de rebase/seleção
- **Teste**: 90 testes Python e 19 Node; validação real criando o arquivo no Terabox e relendo; simulação de PC novo em banco temporário
- **Depende de**: T25

## Como proceder em cada tarefa

1. Leia a tarefa e suas dependências
2. Leia os arquivos de referência indicados
3. Implemente
4. Teste (se possível)
5. Atualize o status para ✅
6. Commit: `git add -A && git commit -m "feat: T{N} - descrição"`
7. Se encontrar erros, registre em DOCS/ERRORS_LEARNINGS.md