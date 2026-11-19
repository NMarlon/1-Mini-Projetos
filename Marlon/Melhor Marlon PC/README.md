# Melhor Marlon PC

Suíte de utilitários deste PC, começando pela **impressora Epson L3150 na rede
local** (impressão + digitalização).

## Estado

Em construção. A impressora ainda **não está na LAN**; o primeiro objetivo é
colocá-la no Wi-Fi 2,4 GHz do roteador Claro/Kaon e instalar o driver.

Acompanhe o estado real em [`DOCS/06-TASKS.md`](DOCS/06-TASKS.md).

## Documentação

A porta de entrada é [`AGENTS.md`](AGENTS.md). Ele aponta para toda a pasta
[`DOCS/`](DOCS/):

- [`DOCS/00-OVERVIEW.md`](DOCS/00-OVERVIEW.md) — objetivo e escopo
- [`DOCS/04-SETUP-RUNBOOK.md`](DOCS/04-SETUP-RUNBOOK.md) — passo a passo
- [`DOCS/08-ERRORS-AND-LESSONS.md`](DOCS/08-ERRORS-AND-LESSONS.md) — erros e
  aprendizados
- [`DOCS/11-REPO-PROTOCOL.md`](DOCS/11-REPO-PROTOCOL.md) — commits e
  autonomia

## Comandos (previstos)

```powershell
.\bin\marlon.ps1 doctor
.\bin\marlon.ps1 printer scan
.\bin\marlon.ps1 printer status -Ip 192.168.0.50
.\bin\marlon.ps1 printer install -Ip 192.168.0.50
.\bin\marlon.ps1 printer verify -Ip 192.168.0.50
.\bin\marlon.ps1 printer test -Ip 192.168.0.50 -Print
```

## Requisitos

- Windows 11 com PowerShell 5.1 (nativo).
- Acesso de administrador apenas para instalar driver/porta.
- Impressora ligada e conectada à rede 2,4 GHz do mesmo roteador.

## Privacidade

Nenhuma senha de Wi-Fi ou do roteador é armazenada no repositório ou nos logs.
Relatórios e logs ficam em `reports/` e `logs/`, fora do Git.
