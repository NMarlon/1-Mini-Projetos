# 05 — Operações

## Comandos

> A CLI será criada em T08. Até lá, os comandos abaixo são o contrato.

| Comando | O que faz | Admin? |
|---|---|---|
| `marlon.ps1 doctor` | Checa sistema, rede, spooler, driver, impressora | não |
| `marlon.ps1 printer scan` | Varre a LAN e lista candidatas | não |
| `marlon.ps1 printer status -Ip <ip>` | Portas, HTTP, modelo, estado | não |
| `marlon.ps1 printer driver` | Baixa/verifica o driver oficial | não |
| `marlon.ps1 printer install -Ip <ip>` | Cria porta TCP/IP, driver e impressora | **sim** |
| `marlon.ps1 printer verify -Ip <ip>` | Valida porta, fila e driver (dry-run) | não |
| `marlon.ps1 printer test -Ip <ip> -Print` | Imprime 1 página com um ponto | não* |
| `marlon.ps1 printer setup` | Wizard guiado (WPS etc.) | parcial |
| `marlon.ps1 report` | Gera relatório Markdown/JSON | não |

\* A impressão em si não exige admin, mas o driver precisa estar instalado.

## Onde ficam as coisas

| Caminho | Conteúdo | Git |
|---|---|---|
| `config/printer.json` | IP, MAC, modelo, driver, porta | sim |
| `config/site.json` | rede, gateway, SSID 2,4, roteador | sim |
| `vendor/` | instalador baixado + hash | não |
| `reports/inventory-*.json/md` | inventário do PC | não |
| `reports/scan-*.json` | descobertas na LAN | não |
| `reports/status-*.json` | status da impressora | não |
| `logs/marlon-*.log` | log de execução | não |

## Segurança

- Nenhum comando grava senha de Wi-Fi ou do roteador.
- O driver é baixado só de domínio oficial da Epson e conferido por SHA-256.
- `install` e `test -Print` pedem confirmação.
- Nada de `Invoke-Expression` em conteúdo baixado.

## Fluxo típico

```powershell
# 1. Diagnóstico
.\bin\marlon.ps1 doctor

# 2. Achar a impressora (depois do WPS)
.\bin\marlon.ps1 printer scan

# 3. Status
.\bin\marlon.ps1 printer status -Ip 192.168.0.50

# 4. Instalar (abre UAC)
.\bin\marlon.ps1 printer install -Ip 192.168.0.50

# 5. Verificar sem imprimir
.\bin\marlon.ps1 printer verify -Ip 192.168.0.50

# 6. Imprimir um ponto (com confirmação)
.\bin\marlon.ps1 printer test -Ip 192.168.0.50 -Print
```

## Solução de problemas

Ver [`12-TROUBLESHOOTING.md`](12-TROUBLESHOOTING.md).
