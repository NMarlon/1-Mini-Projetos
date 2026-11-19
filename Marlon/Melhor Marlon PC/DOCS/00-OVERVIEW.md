# 00 — Visão geral

## Objetivo

Conectar este PC (Windows 11) à impressora **Epson L3150** que está na rede
local, permitindo **imprimir e digitalizar** sem cabo USB no dia a dia, e
automatizar diagnóstico, instalação e verificação.

## Por que este projeto existe

O usuário tentou configurar a L3150 em outro notebook e não conseguiu. Nesta
máquina, a impressora **não está respondendo na LAN**, e não há driver Epson
instalado. O projeto organiza o diagnóstico, o passo a passo e a automação
para que o problema não se repita.

## Escopo da v1

1. Colocar a L3150 no Wi-Fi **2,4 GHz** do roteador Claro/Kaon.
2. Instalar o driver Epson (impressão) e o software de digitalização.
3. Criar porta TCP/IP fixa e impressora no Windows.
4. Imprimir uma página de teste com **um único ponto no canto**.
5. Digitalizar uma página pela rede.
6. CLI `marlon.ps1` com `doctor`, `printer scan`, `printer status`,
   `printer install`, `printer verify` e `printer test`.
7. Documentação completa em `DOCS/`.

## Fora de escopo (v1)

- Trocar o roteador ou o plano de internet.
- Imprimir a partir de outros computadores.
- Wi-Fi Direct como conexão permanente.
- Aplicativo gráfico/GUI (fica no backlog).
- Monitoramento de tinta em tempo real (backlog).

## Glossário

| Termo | Significado |
|---|---|
| **WPS** | Wi-Fi Protected Setup: conecta a impressora ao roteador sem digitar a senha, apertando um botão. |
| **Wi-Fi Direct** | A impressora cria uma rede própria; o PC conecta direto nela. Não é o modo desejado. |
| **Modo infraestrutura** | A impressora entra na rede do roteador, como um celular. É o modo correto. |
| **TCP/IP port** | Porta de impressão do Windows apontando para um IP fixo. Mais estável que WSD. |
| **WSD** | Descoberta automática de impressoras do Windows; pode “sumir”. |
| **IPP** | Internet Printing Protocol; o Windows 11 tem driver genérico (IPP class). |
| **SNMP** | Protocolo de leitura de status/tinta de impressoras de rede. |
| **UAC** | Janela de permissão de administrador do Windows. |

## Critério de sucesso

Ver [`10-VERIFICATION.md`](10-VERIFICATION.md). Resumo: impressora com IP
estável, portas 9100/631 acessíveis, driver instalado, página com um ponto
impressa, digitalização funcionando e `marlon.ps1 doctor` sem erros.
