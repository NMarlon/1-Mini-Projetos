# 03 — Rede e roteador

## Fatos medidos em 2026-11-19

| Item | Valor |
|---|---|
| PC | `DESKTOP-P05PR2E` |
| Ethernet | `192.168.0.17/24`, link 1 Gbps |
| Wi-Fi | `192.168.0.53/24` |
| SSID conectado | `FamiliaViana_5G` |
| Banda | **5 GHz**, canal 149, 802.11ac |
| Segurança | WPA2-Personal (CCMP) |
| Sinal | **35% / -84 dBm** (fraco) |
| Gateway | `192.168.0.1` |
| Roteador | **Claro / Kaon** (MAC `74:3A:EF:5D:CE:D5`) |
| Admin do roteador | `http://192.168.0.1` — **senha desconhecida** |
| Rede 2,4 GHz | **`FamiliaViana`**, WPA2-PSK(AES) — confirmado pela impressora |
| Impressora na LAN | **Sim**: `192.168.0.227` (descoberta em 19/11/2026) |
| MAC da impressora | `50:57:9C:7E:9C:F4` (Seiko Epson) |
| Link da impressora | Wi-Fi 72 Mbps, sinal “Excellent”, SSID `FamiliaViana` |
| Driver Epson | Instalado: `EPSON L3150 Series` (EpsonNet Print, LPR 515) |

## Implicações

1. **A impressora precisa entrar na rede 2,4 GHz.** A L3150 não vê 5 GHz.
2. **Sem senha do admin do roteador**, não dá para:
   - confirmar o nome/segurança da rede 2,4 GHz;
   - habilitar WPS pelo painel;
   - criar reserva de DHCP.
3. **Alternativas sem admin:**
   - WPS pelo botão físico do roteador (se existir);
   - Epson Smart Panel no celular (o celular já tem a senha do Wi-Fi);
   - USB + EpsonNet Setup;
   - IP estático configurado na própria impressora (EpsonNet Config), se
     suportado;
   - script que reencontra a impressora pelo MAC e corrige a porta.
4. **Sinal fraco:** `-84 dBm` no 5 GHz indica distância. O 2,4 GHz penetra
   melhor, mas o local da impressora precisa ser testado. Se ficar marginal,
   aproximar do roteador ou usar repetidor/AP.

## Cuidados

- **Não** tentar senha padrão do roteador: pode bloquear o acesso.
- **Não** resetar o roteador: derruba a internet e muda a senha do Wi-Fi.
- O PC tem Ethernet e Wi-Fi na mesma sub-rede (dual-homed). Isso é ok, mas o
  script de descoberta deve excluir os próprios IPs e MACs localmente
  administrados para não gerar falso positivo.
- O Windows 11 esconde a lista de redes sem permissão de localização; o
  `netsh wlan show networks` mostrando só a rede conectada **não** prova que a
  2,4 GHz está desligada.

## O que confirmar no roteador (quando houver acesso)

- [ ] Nome exato da rede 2,4 GHz.
- [ ] Segurança: WPA2-PSK (AES). Evitar WPA3 puro ou “WPA2/WPA3 misto”.
- [ ] WPS habilitado (se formos usar).
- [ ] Faixa do DHCP (para escolher IP fixo fora dela).
- [ ] Isolamento de clientes (AP isolation) desligado.

## DHCP × IP fixo

Sem acesso ao roteador, a opção mais estável é configurar **IP fixo na
impressora** (ex.: `192.168.0.240`) via EpsonNet Config/Setup, desde que
esteja fora da faixa do DHCP. Se não for possível, o `printer install` usará o
IP atual e o `printer scan` reencontrará a impressora pelo MAC quando o IP
mudar.
