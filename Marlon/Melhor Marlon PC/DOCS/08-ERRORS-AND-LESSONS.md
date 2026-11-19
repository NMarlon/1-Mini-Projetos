# 08 — Erros e aprendizados

> Este arquivo é obrigatório. Toda IA que trabalhar aqui deve registrar o que
> deu errado, a causa raiz e como evitar. Não apague entradas antigas.

## 2026-11-19 — Planejamento e diagnóstico inicial

### E01 — Concluir “impressora fora da rede” só com ping

**Erro:** a primeira varredura testou as portas 9100/631/515 apenas nos hosts
que responderam a ping. Impressoras podem bloquear ICMP e ainda estar
acessíveis.

**Correção:** varrer as portas de impressão em **todos** os IPs da /24, com
conexões TCP assíncronas. Resultado: realmente não havia nenhuma porta aberta.

**Lição:** ICMP não é prova de ausência. Para impressora, o teste é TCP
9100/631/515.

### E02 — `netsh wlan show networks` só mostrou uma rede

**Erro:** a saída mostrou apenas `FamiliaViana_5G`, o que poderia levar à
conclusão errada de que a rede 2,4 GHz não existe.

**Causa:** o Windows 11 exige permissão de localização para listar redes
vizinhas; sem isso, mostra só a conectada.

**Lição:** não concluir ausência de SSID pelo `netsh`. Confirmar no celular ou
no painel do roteador. O usuário confirmou que a rede 2,4 GHz existe.

### E03 — Sessão sem privilégio de administrador

**Erro:** `Add-PrinterDriver`/`Add-PrinterPort` vão falhar na sessão atual.

**Lição:** diagnóstico roda sem admin; instalação precisa de elevação. O
script deve detectar e gerar um `.cmd` para o usuário rodar como admin, já que
o agente não consegue clicar no UAC.

### E04 — Driver Epson não é o primeiro problema

**Erro de abordagem:** começar baixando o driver. Sem a impressora na LAN, o
instalador falha no passo “procurar impressora”.

**Lição:** ordem correta é rede → driver → porta → teste.

### E05 — L3150 é 2,4 GHz, o PC está em 5 GHz

**Observação:** o PC está em `FamiliaViana_5G` (canal 149, 5 GHz). A L3150 só
tem rádio 2,4 GHz.

**Lição:** não misturar as bandas no diagnóstico. A impressora precisa da rede
2,4 GHz; o PC pode continuar no 5 GHz que a comunicação passa pelo roteador.

### E06 — Windows localizado

**Observação:** `netsh`, `arp -a` e mensagens saem em português.

**Lição:** não parsear texto localizado. Usar objetos .NET/CIM
(`Get-NetAdapter`, `Get-NetIPConfiguration`, `Get-Printer`) e, quando não
houver alternativa, regex tolerante.

### E07 — PowerShell 5.1 tem armadilhas

- `curl` é alias de `Invoke-WebRequest`, não do curl.exe.
- Downloads HTTPS precisam de `[Net.ServicePointManager]::SecurityProtocol =
  [Net.SecurityProtocolType]::Tls12`.
- `ConvertTo-Json` padrão é Depth 2; usar `-Depth 10`.
- Scripts com acento precisam de UTF-8 **com BOM** para o PS 5.1 ler certo.
- Não existe `ForEach-Object -Parallel` (isso é PS 7).

**Lição:** testar sempre no PowerShell 5.1, não no 7.

### E08 — Git com outros projetos sujos

**Observação:** o repo raiz tem alterações em `Alexandre - Videos/` e uma
pasta não rastreada `Reconhecedor de Rostos de  Imagens/`.

**Lição:** nunca `git add .`. Stage explícito de `Marlon/`. Conferir
`git status` antes de cada commit.

### E09 — Dual-homed

**Observação:** Ethernet `192.168.0.17` e Wi-Fi `192.168.0.53` na mesma /24.

**Lição:** a descoberta deve deduplicar IPs e excluir os próprios endereços e
MACs localmente administrados, senão aparecem falsos positivos (ex.:
`192.168.0.76` e `.141` responderam com MAC local e nome do próprio PC).

### E10 — Epson Download Center bloqueia automação

**Observação:** `download-center.epson.com` retornou **403** para requisição
automatizada.

**Lição:** ter fallback: página de suporte do modelo, Epson Setup Navi, ou
driver IPP nativo do Windows. Registrar URL/hash quando obtiver o arquivo.

## Modelo para novas entradas

```markdown
### EXX — Título curto

**Erro:** o que aconteceu.
**Causa raiz:** por quê.
**Correção:** o que foi feito.
**Lição:** como evitar na próxima.
```
