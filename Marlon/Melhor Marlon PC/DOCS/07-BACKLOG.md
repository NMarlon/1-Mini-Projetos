# 07 — Backlog (futuro, não implementar agora)

## Impressão e digitalização

- [ ] Digitalização por WSD/eSCL sem depender do Epson Scan 2.
- [ ] Perfis de digitalização (PDF/A, 300 dpi, frente/verso manual).
- [ ] Digitalizar direto para uma pasta monitorada.
- [ ] Ver nível de tinta via SNMP.
- [ ] Contador de páginas e alerta de manutenção.
- [ ] Fila de impressão: pausar/retomar/limpar jobs com segurança.

## Rede

- [ ] Reserva de DHCP automatizada (se o roteador Claro/Kaon expuser API).
- [ ] Tarefa agendada que reencontra a impressora pelo MAC e corrige a porta.
- [ ] Suporte a múltiplas sub-redes/repetidores.
- [ ] Detecção de AP isolation e WPA3.
- [ ] Teste de sinal 2,4 GHz no local da impressora.

## Produto

- [ ] GUI WPF/bandeja com status e botão “imprimir teste”.
- [ ] Instalador único (`.exe`) assinado.
- [ ] Atualização automática do driver.
- [ ] Logs rotativos e envio de relatório por e-mail.
- [ ] Outras features do “Melhor Marlon PC”: backup, limpeza, atalhos.

## Dívidas técnicas

- [ ] Testes de integração reais (hoje só lógica pura).
- [ ] Pester 5 (hoje Pester 3.4 é antigo; usamos runner próprio).
- [ ] Suporte a PowerShell 7 (hoje só 5.1).
- [ ] Assinatura de scripts para evitar bloqueio de ExecutionPolicy/SAC.

## Ideias descartadas por enquanto

- Wi-Fi Direct como conexão permanente: a impressora sai da rede do roteador.
- Reset de fábrica do roteador: derruba internet e muda a senha do Wi-Fi.
- Driver de site de terceiros: risco de malware.
