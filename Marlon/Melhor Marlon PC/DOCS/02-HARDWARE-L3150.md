# 02 — Hardware: Epson L3150

## Especificações relevantes

| Item | Valor |
|---|---|
| Modelo | Epson EcoTank L3150 |
| Impressão | Jato de tinta, 4 cores, até A4 |
| Digitalização | Scanner de mesa (flatbed), sem alimentador |
| USB | Sim (USB 2.0) |
| Ethernet | **Não tem** |
| Wi-Fi | **802.11 b/g/n — somente 2,4 GHz** |
| Wi-Fi Direct | Sim (a impressora cria a própria rede) |
| Painel | **Sem LCD**; apenas botões e LEDs |
| WPS | Sim (via botão Wi-Fi) |
| Impressão móvel | Epson Smart Panel / iPrint |

> **Ponto crítico:** a L3150 **não** entra em rede 5 GHz. Ela precisa da rede
> 2,4 GHz do roteador. Ela **suporta** modo infraestrutura (entrar no Wi-Fi do
> roteador) — não é “só Wi-Fi Direct”.

## Botões

| Botão | Função |
|---|---|
| Power | Liga/desliga |
| Wi-Fi | Liga o Wi-Fi; segurar ~5 s inicia WPS |
| Wi-Fi Direct | Liga/desliga o modo direto |
| Network Status (ícone de rede) | Imprime folha de status; usado em resets |
| Stop (triângulo/círculo) | Cancela operação |
| B&W / Color | Copiar em preto e branco / colorido |

## LEDs

| LED | Significado |
|---|---|
| Wi-Fi verde fixo | Conectada ao roteador |
| Wi-Fi piscando | Conectando / WPS em andamento |
| Wi-Fi apagado | Wi-Fi desligado ou sem conexão |
| Wi-Fi Direct ligado | Modo direto ativo |
| Wi-Fi + Wi-Fi Direct piscando alternadamente | WPS/reset em andamento |
| Luz de papel | Sem papel / atolamento |
| Luz de tinta | Tinta baixa / erro |

## Procedimentos oficiais

### Imprimir folha de status de rede

1. Carregue papel.
2. Segure o botão **Network Status** por **pelo menos 7 segundos**.
3. Solte. A folha mostra: nome da rede (SSID), IP, máscara, gateway, MAC,
   sinal e dados do Wi-Fi Direct.

Fonte: [Epson — Printing a Network Status Sheet](https://files.support.epson.com/docid/cpd5/cpd55466/source/printers/source/networking/tasks/l3150/printing_network_status_sheet_l3150.html)

> Se soltar antes de 7 s, sai um **relatório de conexão**, não a folha
> completa.

### Conectar via WPS

1. Pressione o botão **WPS** no roteador (ou ative o WPS no painel do
   roteador).
2. Em até **2 minutos**, segure o botão **Wi-Fi** da impressora por cerca de
   **5 segundos**, até os LEDs **Wi-Fi** e **Wi-Fi Direct** piscarem
   alternadamente.
3. Aguarde. O LED **Wi-Fi** fica **verde fixo** se conectou.

Fonte: [Epson — Using WPS to Connect to a Network](https://files.support.epson.com/docid/cpd6/cpd62154/source/printers/source/networking/tasks/l3150/connecting_wps_l3150.html)

### Ativar Wi-Fi Direct (contingência)

1. Segure o botão **Wi-Fi** e pressione o botão **Network Status** até os LEDs
   Wi-Fi e Wi-Fi Direct piscarem alternadamente. Solte.
2. Segure **Network Status** por ~7 s para imprimir a folha.
3. No PC, conecte na rede `DIRECT-...` usando a senha da folha.

Fonte: [Epson — Enabling Wi-Fi Direct Mode](https://files.support.epson.com/docid/cpd5/cpd55466/source/printers/source/networking/tasks/l3150/wifi_direct_nopanel_l3150.html)

### Resetar configurações de rede

1. Desligue a impressora.
2. Segure **Network Status** e pressione **Power** até os LEDs Wi-Fi e Wi-Fi
   Direct piscarem alternadamente. Solte.
3. Ligue novamente e configure do zero.

> **Atenção:** apaga SSID/senha salvos. Só fazer com autorização do usuário.

## Limitações conhecidas

- Sem LCD: toda configuração é por botões, app ou software no PC.
- Sem Ethernet: depende do Wi-Fi 2,4 GHz.
- Sinal fraco no local pode impedir WPS ou derrubar a conexão.
- O instalador da Epson no PC usa uma conexão Wi-Fi temporária com a
  impressora; se o PC não tiver Wi-Fi, o caminho é USB.
