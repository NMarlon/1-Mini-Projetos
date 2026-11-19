# 01 — Arquitetura

> Status: planejada. Os arquivos de código serão criados nas tarefas T01–T09.

## Decisão principal

**PowerShell 5.1 nativo**, sem dependências externas. Motivos:

- já vem no Windows 11;
- tem `PrintManagement`, `NetTCPIP`, `NetAdapter`, `CimInstance`;
- não precisa de Python, Node ou instalação;
- é o que o Windows usa para impressão.

GUI fica para o backlog; a v1 é CLI.

## Visão de módulos

```text
bin/marlon.ps1
  └─ importa src/MarlonPC.psm1
       ├─ src/core/            log, config, elevação, relatório
       └─ src/features/
            └─ printer/        inventário, descoberta, status, driver,
                               instalação, verificação, wizard
```

### Contrato de uma feature

Cada pasta em `src/features/<nome>/`:

- expõe funções com verbo aprovado (`Get-`, `Find-`, `Test-`, `Install-`,
  `Invoke-`, `New-`);
- tem um `feature.json` com nome, comandos e descrição;
- não acessa recursos de outra feature diretamente (usa `core/`);
- é carregada automaticamente pelo módulo.

## Fluxo da feature `printer`

```text
1. Inventário       Get-MarlonInventory
   └─ sistema, adaptadores, IP, gateway, Wi-Fi, spooler, drivers

2. Descoberta       Find-MarlonPrinter
   └─ ARP + ping assíncrono + portas 9100/631/515 + OUI Epson

3. Status           Get-MarlonPrinterStatus
   └─ TCP, HTTP, IPP/SNMP (best effort), modelo, estado

4. Driver           Get-MarlonDriver
   └─ vendor/ + driver.lock.json (URL, versão, SHA-256)
   └─ fallback: Microsoft IPP Class Driver

5. Instalação       Install-MarlonPrinter
   └─ porta TCP/IP + Add-PrinterDriver + Add-Printer (idempotente)

6. Verificação      Test-MarlonPrinter
   └─ portas, fila, job, página de teste (opt-in)
```

## Pastas de dados

| Pasta | Conteúdo | Git? |
|---|---|---|
| `config/` | IP/MAC/modelo/driver, fatos da rede (sem segredos) | sim |
| `vendor/` | instalador do driver + hash | **não** |
| `reports/` | inventário, descobertas, status (JSON/MD) | **não** |
| `logs/` | log de execução | **não** |
| `DOCS/` | documentação viva | sim |

## Princípios

1. **Idempotência** — rodar `install` duas vezes não duplica nada.
2. **Dry-run por padrão** no teste de impressão.
3. **Sem segredos** — senha do Wi-Fi/roteador nunca é gravada.
4. **Falha explícita** — se a impressora não for encontrada, o script diz o que
   fazer, não fica em loop.
5. **Diagnóstico separado de ação** — `status`/`scan` não pedem admin;
   `install` pede.
6. **Cultura-independente** — não parsear texto localizado do `netsh`;
   preferir objetos do .NET/CIM.

## Compatibilidade

- Windows PowerShell 5.1 (não usar sintaxe de PowerShell 7).
- Sem `ForEach-Object -Parallel`, sem `??`, sem `-AsHashtable`.
- Saída em UTF-8; scripts com acentos salvos com BOM.
