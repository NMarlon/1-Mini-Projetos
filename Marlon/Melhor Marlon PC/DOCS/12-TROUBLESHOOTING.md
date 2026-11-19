# 12 — Troubleshooting

## A impressora não aparece na rede

| Sintoma | Causa provável | Ação |
|---|---|---|
| LED Wi-Fi apagado | Wi-Fi desligado | Pressionar o botão Wi-Fi |
| LED Wi-Fi piscando | Tentando conectar / WPS | Aguardar; se passar de 2 min, repetir WPS |
| Folha de status sem SSID | Não conectada | Método A/B/C/D do runbook |
| Folha mostra IP, mas o PC não pinga | Sub-rede diferente / AP isolation | Verificar IP/gateway; desligar isolamento no roteador |
| Scan não acha | Impressora desligada ou em outra sub-rede | Ligar; conferir folha; varrer a sub-rede correta |

## WPS não funciona

- O roteador pode não ter WPS físico; verificar o painel `192.168.0.1`.
- A rede 2,4 GHz pode estar desligada ou oculta.
- Segurança WPA3 pura: a L3150 pode não conectar; usar WPA2-PSK (AES).
- Distância/sinal: aproximar a impressora do roteador para configurar.
- Repetir: WPS no roteador → em até 2 min, segurar Wi-Fi ~5 s.

## A impressora conecta mas o Windows não instala

| Sintoma | Causa | Ação |
|---|---|---|
| “Driver não encontrado” | Driver não instalado | `printer install` com pacote oficial |
| Erro de permissão | Sessão sem admin | Rodar `INSTALAR-IMPRESSIONORA-ADMIN.cmd` |
| Porta existe com IP antigo | DHCP mudou o IP | `printer scan` + recriar porta |
| Impressora duplicada | Instalação repetida | Remover duplicata; `install` é idempotente |
| Fila travada | Job preso | `Get-PrintJob` e cancelar; reiniciar spooler |

## Imprime mas sai lento ou some

- Preferir porta TCP/IP a WSD.
- Verificar sinal 2,4 GHz no local.
- Desligar “SNMP status” se o driver ficar consultando e demorar.
- Verificar se o IP não conflita com outro dispositivo.

## Digitalização não funciona

- Confirmar que o Epson Scan 2 está instalado.
- Testar WSD: “Painel de Controle → Dispositivos → Adicionar”.
- Firewall: rede precisa estar como **Privada**.
- Alguns firmwares exigem o driver de rede instalado, não só o USB.

## Erros comuns do Windows

| Código | Significado | Ação |
|---|---|---|
| `0x0000011b` | RPC/point-and-print | Não é o caso de porta TCP/IP local; documentar |
| `0x00000709` | Impressora padrão | Definir manualmente |
| `0x00000bcb` | Driver/serviço | Reinstalar driver |

## Reset de rede da impressora

Só com autorização:

1. Desligar.
2. Segurar **Network Status** + **Power** até os LEDs Wi-Fi e Wi-Fi Direct
   piscarem alternadamente.
3. Soltar; ligar; configurar de novo.

## Coleta para suporte

```powershell
.\bin\marlon.ps1 doctor
.\bin\marlon.ps1 printer scan
.\bin\marlon.ps1 printer status -Ip <ip>
```

Anexar os arquivos de `reports/` (sem dados sensíveis).
