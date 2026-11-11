# OpenCode Cleaner

Ferramenta para auditar e compactar o banco de sessões do OpenCode **sem apagar nenhuma sessão**.

O problema que ela resolve: o SQLite do OpenCode está com `auto_vacuum=0`. Depois de apagar ou reorganizar dados, o espaço não volta para o Windows. O arquivo `opencode.db` chega a 3,1 GB mesmo com apenas ~516 MB de dados vivos. O `VACUUM` devolve esse espaço.

## Estrutura

| Arquivo | Função |
|---|---|
| `audit.py` | Auditoria somente leitura: tamanho por sessão/projeto, espaço livre interno, idade, versões V1/V2 |
| `vacuum.ps1` | Backup compacto + `VACUUM` + validação de integridade |
| `opencode.json` | Permissões restritas para quando este projeto for aberto no OpenCode |
| `audit.cmd` / `vacuum.cmd` | Atalhos para executar no Windows |
| `backups/` | Backups compactos (ignorado pelo Git) |
| `relatorios/` | CSV/JSON da auditoria (ignorado pelo Git) |

## Pré-requisitos

- Python 3.10 ou superior (testado com 3.14).
- `sqlite3.exe` no `PATH`.
- OpenCode 2.x (o script usa `opencode service stop/start`).

## 1. Auditoria (pode rodar com o OpenCode aberto)

```powershell
cd "C:\MarlonScripts\1-Mini Projetos\opencode-cleaner"
python audit.py
```

O script abre o banco em modo `mode=ro` e nunca escreve nele. Ele mostra:

- tamanho do arquivo, WAL e SHM;
- páginas livres e estimativa do banco compactado;
- sessões por projeto, subagentes e arquivadas;
- top sessões por tamanho;
- divisão V1 (legado) x V2;
- faixas de idade pela última atividade.

Gera também `relatorios/sessoes-AAAAMMDD-HHMMSS.csv` e `relatorios/resumo-AAAAMMDD-HHMMSS.json`.

Opções:

```powershell
python audit.py --json          # também imprime o resumo JSON
python audit.py --no-files      # não grava CSV/JSON
python audit.py --top 30        # lista mais sessões
```

## 2. Compactação (com o OpenCode fechado)

1. Feche o OpenCode (TUI, desktop e qualquer terminal dele).
2. Abra um **PowerShell separado**.
3. Rode:

```powershell
cd "C:\MarlonScripts\1-Mini Projetos\opencode-cleaner"
.\vacuum.ps1
```

Ou dê dois cliques em `vacuum.cmd`.

O script:

1. Mostra o tamanho atual e o espaço livre.
2. Aborta se encontrar processo do OpenCode aberto.
3. Pede confirmação digitando `VACUUM`.
4. Para o serviço com `opencode service stop`.
5. Cria `backups/opencode-AAAAMMDD-HHMMSS.db` usando `VACUUM INTO` (~520 MB, já compacto).
6. Valida o backup com `PRAGMA integrity_check`.
7. Executa `VACUUM` no banco principal e `PRAGMA wal_checkpoint(TRUNCATE)`.
8. Valida o banco principal.
9. Reinicia o serviço e mostra antes/depois.

Para apenas simular, sem alterar nada:

```powershell
.\vacuum.ps1 -DryRun
```

## Resultado esperado

| Item | Antes | Depois |
|---|---:|---:|
| `opencode.db` | ~3.112 MB | ~520 MB |
| `opencode.db-wal` | ~86 MB | ~0–10 MB |
| Total da pasta | ~3,29 GB | ~610 MB |

O ganho vem da compactação, não da exclusão de histórico.

## Restauração

Se algo der errado, o backup está em `backups/`. Para restaurar:

1. Feche o OpenCode.
2. Pare o serviço: `opencode service stop`.
3. Mova `opencode.db`, `opencode.db-wal` e `opencode.db-shm` atuais para uma pasta de segurança.
4. Copie o backup para `C:\Users\marlo\.local\share\opencode\opencode.db`.
5. Inicie o OpenCode.

O backup contém dados sensíveis (prompts, trechos de arquivos). Não versionar e não compartilhar.

## Segurança

- A auditoria é **somente leitura** (`mode=ro` + `PRAGMA query_only`).
- A compactação **não apaga sessões**; só reorganiza o arquivo.
- O script nunca edita o SQLite com o serviço rodando.
- O `opencode.json` deste projeto bloqueia acesso externo, exceto à pasta de dados do OpenCode, e pede confirmação para leitura/escrita nela.
- O backup é criado antes de qualquer alteração e validado com `integrity_check`.

## Solução de problemas

**`sqlite3.exe` não encontrado**
Instale o SQLite e coloque a pasta no `PATH`, ou edite `vacuum.ps1` para apontar o caminho completo.

**"Ainda há processos do OpenCode em execução"**
Feche todas as janelas do OpenCode, inclusive o app desktop. O script precisa do banco sem conexões abertas.

**"database is locked"**
Algum processo ainda está usando o banco. Feche tudo e tente de novo.

**O serviço não reinicia**
Rode manualmente:

```powershell
opencode service start
```

**Quero só ver o espaço sem compactar**
`python audit.py` mostra as páginas livres e a estimativa do banco compactado.
