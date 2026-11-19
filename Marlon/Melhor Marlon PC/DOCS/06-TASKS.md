# 06 — Tarefas

> **Estado atual:** T00 concluída. Próxima: T01.
> Atualize esta tabela ao final de cada tarefa.

## Legenda

- `[ ]` pendente
- `[~]` em andamento
- `[x]` concluída
- `[!]` bloqueada por ação humana

| ID | Status | Tarefa | Depende de você? | Commit |
|---|---|---|---|---|
| T00 | `[x]` | Estrutura, AGENTS, docs base, .gitignore | não | `docs(marlon-pc): estrutura inicial e protocolo` |
| T01 | `[ ]` | Inventário do PC + baseline da rede | não | `feat(marlon-pc): inventario e baseline do pc` |
| T02 | `[ ]` | Descoberta de impressora na LAN | não | `feat(marlon-pc): descoberta de impressora na lan` |
| T03 | `[ ]` | Status/diagnóstico da impressora | não | `feat(marlon-pc): diagnostico de status da impressora` |
| T04 | `[ ]` | Runbook + troubleshooting (revisão) | não | `docs(marlon-pc): runbook da l3150 e troubleshooting` |
| T05 | `[ ]` | Download verificado do driver Epson | não | `feat(marlon-pc): download verificado do driver epson` |
| T06 | `[ ]` | Instalação idempotente da impressora | sim, teste real | `feat(marlon-pc): instalacao idempotente da impressora` |
| T07 | `[ ]` | Verificação + página de teste | sim, autorizar | `feat(marlon-pc): verificacao e teste de impressao` |
| T08 | `[ ]` | CLI `marlon.ps1` + doctor | não | `feat(marlon-pc): cli e doctor` |
| T09 | `[ ]` | Wizard `printer setup` | não | `feat(marlon-pc): wizard de setup da impressora` |
| T10 | `[!]` | Sessão assistida: WPS + driver + teste + scan | **sim (~10 min)** | `feat(marlon-pc): l3150 operacional na rede` |

## Detalhe das tarefas

### T01 — Inventário do PC + baseline

**Como proceder:**
1. Criar `src/core/` (log, config, relatório) e `src/features/printer/inventory.ps1`.
2. Coletar: OS/build, admin, adaptadores, IPs, gateway, DNS, métricas, Wi-Fi
   (SSID/banda/sinal), spooler, impressoras, drivers, portas.
3. Salvar `reports/inventory-<data>.json` e `.md`.
4. Atualizar `03-NETWORK-AND-ROUTER.md` com o baseline.
5. Testar no PowerShell 5.1 e commitar.

**Referências:** `03-NETWORK-AND-ROUTER.md`, comandos `Get-NetAdapter`,
`Get-NetIPConfiguration`, `Get-Printer`, `Get-PrinterDriver`.

### T02 — Descoberta na LAN

**Como proceder:**
1. Ler IPs/gateway do inventário.
2. Fazer ping assíncrono (`Ping.SendPingAsync`) na /24, sem depender de ICMP
   para concluir (probe TCP também).
3. Probe TCP 9100, 631, 515, 80 em paralelo.
4. Pontuar candidatos: Epson OUI + portas + hostname.
5. Excluir os próprios IPs e MACs localmente administrados.
6. Salvar `reports/scan-<data>.json`; imprimir tabela.
7. Commitar.

**Referências:** `03-NETWORK-AND-ROUTER.md`, `src/data/epson-oui.csv`.

### T03 — Status da impressora

**Como proceder:**
1. Dado um IP: testar 9100/631/515/80.
2. Tentar HTTP GET e IPP `Get-Printer-Attributes` (best effort).
3. SNMP v1 (sysDescr, nome, estado) se responder; senão, seguir sem.
4. Nunca imprimir nesta tarefa.
5. Salvar `reports/status-<data>.json`; commitar.

### T04 — Runbook

Revisar `04-SETUP-RUNBOOK.md` e `12-TROUBLESHOOTING.md` com o que foi
descoberto nas tarefas anteriores. Commitar.

### T05 — Driver

**Como proceder:**
1. Localizar o pacote oficial para Windows 11 x64 no Epson Download Center.
2. Registrar URL, versão e SHA-256 em `driver.lock.json`.
3. `tools/fetch-driver.ps1`: TLS 1.2, download, hash, cache em `vendor/`.
4. `tools/inspect-driver.ps1`: extrair e achar o INF, se possível.
5. Fallback: Microsoft IPP Class Driver (sem download).
6. Commitar.

**Atenção:** o Epson Download Center pode retornar 403 para automação; nesse
caso, documentar o caminho manual e seguir com o fallback IPP.

### T06 — Instalação

**Como proceder:**
1. Detectar admin; se não, auto-elevar (`Start-Process -Verb RunAs`) ou gerar
   `INSTALAR-IMPRESSIONORA-ADMIN.cmd`.
2. Se a impressora/porta já existir com o mesmo IP → no-op.
3. Criar porta TCP/IP (`Add-PrinterPort`), instalar driver (`pnputil` ou
   driver store) e criar impressora (`Add-Printer`).
4. Definir como padrão só com `-SetDefault`.
5. Commitar.

### T07 — Verificação

1. Testar portas, fila, driver e impressora.
2. `-Print` gera uma página A4 com **um ponto preto no canto** (custo mínimo).
3. Sem `-Print`: dry-run e relatório.
4. Commitar.

### T08 — CLI

1. `bin/marlon.ps1` com dispatch, help, cores, log.
2. `doctor` agrega inventário + rede + spooler + impressora.
3. `Marlon.cmd` para duplo clique.
4. Commitar.

### T09 — Wizard

1. `printer setup`: explica WPS, espera, detecta, instala, verifica.
2. Modo `-DiagnoseOnly` sem ação manual.
3. Commitar.

### T10 — Sessão assistida

1. Usuário faz WPS / Smart Panel / USB.
2. `printer scan` acha o IP.
3. `printer install` (UAC).
4. `printer test -Print` (um ponto).
5. Digitalização.
6. Registrar IP/MAC/SSID; atualizar docs; commitar.

## Se parar no meio

Deixe aqui o comando exato para continuar e o que falta. Exemplo:

```powershell
# continuar da T02
.\tests\run-tests.ps1
.\bin\marlon.ps1 printer scan
```
