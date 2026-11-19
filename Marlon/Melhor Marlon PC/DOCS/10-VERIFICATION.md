# 10 — Verificação (critérios de aceite)

A v1 só termina quando **todos** os itens abaixo estiverem marcados.

## Rede

- [ ] A impressora está no Wi-Fi **2,4 GHz** do roteador (LED Wi-Fi verde
      fixo).
- [ ] A folha de status mostra SSID 2,4 GHz e IP `192.168.0.x`.
- [ ] O IP é estável (fixo na impressora ou reserva de DHCP).
- [ ] `Test-NetConnection <ip> -Port 9100` retorna `True`.
- [ ] `Test-NetConnection <ip> -Port 631` retorna `True`.
- [ ] O IP responde a partir do PC **pelo cabo** (não só pelo Wi-Fi).

## Driver e impressão

- [ ] Driver Epson L3150 instalado (`Get-PrinterDriver`).
- [ ] Impressora criada com porta TCP/IP (`Get-Printer`).
- [ ] Impressora não duplicada ao rodar `install` duas vezes.
- [ ] Fila vazia/sem erro (`Get-PrintJob`).
- [ ] **Página com um ponto preto no canto impressa** e conferida.
- [ ] `marlon.ps1 printer verify` retorna sucesso.

## Digitalização

- [ ] Epson Scan 2 (ou WSD) encontra a impressora pela rede.
- [ ] Digitalização de 1 página gera arquivo legível.
- [ ] O arquivo é salvo em pasta conhecida e o caminho é informado.

## Automação

- [ ] `marlon.ps1 doctor` sem erros.
- [ ] `marlon.ps1 printer scan` acha a impressora pelo IP/MAC.
- [ ] `marlon.ps1 printer status -Ip <ip>` mostra modelo/estado.
- [ ] Logs em `logs/` e relatórios em `reports/`.
- [ ] Rodar `install` de novo não quebra nada (idempotência).

## Documentação

- [ ] `config/printer.json` atualizado com IP, MAC, modelo, driver e porta.
- [ ] `DOCS/03-NETWORK-AND-ROUTER.md` com o SSID 2,4 GHz e o IP final.
- [ ] `DOCS/06-TASKS.md` com T10 concluída.
- [ ] `DOCS/08-ERRORS-AND-LESSONS.md` com o que funcionou e o que falhou.
- [ ] Commit final feito.

## Evidências

Guardar em `reports/` (fora do Git):

- saída de `Get-Printer`;
- `Test-NetConnection` das portas;
- foto/scan da folha de status (sem dados sensíveis);
- foto da página com o ponto.
