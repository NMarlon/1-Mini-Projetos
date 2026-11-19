# 04 — Runbook de conexão da L3150

Este é o documento que o humano (ou a próxima IA) segue para colocar a
impressora na rede. Marque `[VOCÊ]` para ação manual e `[SCRIPT]` para
automação.

## Pré-requisitos

- Impressora ligada e com papel.
- Roteador ligado; rede 2,4 GHz ativa.
- Senha do Wi-Fi 2,4 GHz em mãos (se o método não for WPS).
- Cabo USB (só para o método D).
- ~10 minutos.

## Árvore de decisão

```text
A impressora responde na LAN?
├─ SIM → instalar driver (T06) → verificar (T07)
└─ NÃO
   ├─ Está ligada?  ── não → ligar e repetir
   └─ sim
      ├─ Folha de status mostra SSID/IP? 
      │  ├─ SIM → investigar sub-rede/firewall (T12)
      │  └─ NÃO → método A (WPS)
      └─ WPS
         ├─ funcionou → folha de status → instalar
         └─ falhou
            ├─ método B (Smart Panel)
            ├─ método C (instalador Epson no PC)
            ├─ método D (USB + EpsonNet Setup)
            └─ método E (Wi-Fi Direct, contingência)
```

## Método A — WPS (recomendado)

**Pré-requisito:** botão WPS no roteador (atrás, às vezes pequeno) **ou** WPS
habilitado no painel.

1. `[VOCÊ]` Pressione o botão **WPS** do roteador. Alguns piscam um LED.
2. `[VOCÊ]` Em até **2 minutos**, segure o botão **Wi-Fi** da impressora por
   ~5 s, até os LEDs **Wi-Fi** e **Wi-Fi Direct** piscarem alternadamente.
3. `[VOCÊ]` Aguarde até o LED **Wi-Fi** ficar **verde fixo**.
4. `[VOCÊ]` Segure **Network Status** por 7 s e imprima a folha de status.
5. `[SCRIPT]` Rodar `marlon.ps1 printer scan` e confirmar o IP.

**Se falhar:** LED Wi-Fi continua piscando/apagado → método B ou C.

## Método B — Epson Smart Panel (celular)

**Pré-requisito:** celular conectado ao Wi-Fi 2,4 GHz ou 5 GHz (o app troca de
rede sozinho) e app instalado.

1. `[VOCÊ]` Instale **Epson Smart Panel** (Play Store/App Store).
2. `[VOCÊ]` Abra o app e escolha “Configurar nova impressora” → L3150.
3. `[VOCÊ]` O app conecta na rede temporária da impressora e pede a senha do
   Wi-Fi 2,4 GHz. Digite.
4. `[VOCÊ]` Aguarde a confirmação e imprima a folha de status.
5. `[SCRIPT]` `marlon.ps1 printer scan`.

> A senha é digitada **no app**, não no repositório nem no chat.

## Método C — Instalador Epson no PC

**Pré-requisito:** PC com Wi-Fi (este tem: Intel AX211). O instalador usa uma
conexão temporária com a impressora.

1. `[SCRIPT]` Baixar o pacote oficial (T05).
2. `[VOCÊ]` Executar o instalador e escolher “Conexão sem fio”.
3. `[VOCÊ]` Selecionar a rede 2,4 GHz e digitar a senha.
4. `[VOCÊ]` Concluir; o driver já fica instalado.
5. `[SCRIPT]` Verificar IP e porta.

## Método D — USB + EpsonNet Setup (mais determinístico)

**Pré-requisito:** cabo USB e impressora perto do PC.

1. `[VOCÊ]` Conecte o cabo USB.
2. `[VOCÊ]` O Windows reconhece; o instalador Epson configura o Wi-Fi pelo
   cabo.
3. `[VOCÊ]` Informe a rede 2,4 GHz e a senha.
4. `[SCRIPT]` Confirmar que o IP aparece na LAN e remover o cabo.

## Método E — Wi-Fi Direct (contingência)

Use só se os anteriores falharem. A impressora sai da rede do roteador.

1. `[VOCÊ]` Segure **Wi-Fi** e pressione **Network Status** até os LEDs
   piscarem alternadamente.
2. `[VOCÊ]` Imprima a folha (Network Status 7 s) e pegue SSID/senha.
3. `[VOCÊ]` No PC, conecte na rede `DIRECT-...`.
4. `[SCRIPT]` Instalar a impressora no IP do Wi-Fi Direct.

> O PC mantém internet pelo cabo Ethernet; só a impressão vai pelo Wi-Fi.

## Depois de conectar

1. `[SCRIPT]` `printer status` — confirmar portas 9100/631.
2. `[SCRIPT]` `printer install` — driver + porta TCP/IP (admin).
3. `[SCRIPT]` `printer verify` — dry-run.
4. `[VOCÊ]` Autorizar `printer test -Print` — página com um ponto.
5. `[SCRIPT]` Digitalização: Epson Scan 2 ou WSD.
6. `[SCRIPT]` Registrar IP/MAC/SSID em `config/printer.json` e na doc.

## Checklist de aceite

- [ ] LED Wi-Fi verde fixo.
- [ ] Folha de status mostra IP `192.168.0.x` e SSID 2,4 GHz.
- [ ] `Test-NetConnection <ip> -Port 9100` = True.
- [ ] Impressora aparece em `Get-Printer`.
- [ ] Página com um ponto impressa.
- [ ] Digitalização concluída.
- [ ] `marlon.ps1 doctor` sem erros.
