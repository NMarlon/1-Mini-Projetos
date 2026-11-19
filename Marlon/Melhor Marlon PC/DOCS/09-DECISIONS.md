# 09 — Decisões (ADRs)

> Formato curto: contexto → decisão → consequência.

## ADR-001 — PowerShell 5.1, sem dependências

**Contexto:** automação só de Windows, precisa rodar em qualquer máquina sem
instalar runtime.

**Decisão:** usar PowerShell 5.1 nativo e módulos do Windows
(`PrintManagement`, `NetTCPIP`). Sem Python/Node.

**Consequência:** nada para instalar; limitações de sintaxe (sem `??`,
`-Parallel`, etc.). Testar sempre no 5.1.

## ADR-002 — Porta TCP/IP, não WSD

**Contexto:** WSD descobre sozinho, mas “some” e depende de multicast.

**Decisão:** criar porta TCP/IP (`Add-PrinterPort -PrinterHostAddress`) com IP
fixo.

**Consequência:** mais estável; exige IP previsível (fixo ou reencontrado pelo
MAC).

## ADR-003 — Driver oficial em `vendor/`, fora do Git

**Contexto:** pacote de ~30 MB, licença Epson, mas precisa ser reproduzível.

**Decisão:** `tools/fetch-driver.ps1` baixa do site oficial, confere SHA-256 e
guarda em `vendor/`; `driver.lock.json` (versionado) tem URL, versão e hash.

**Consequência:** repo leve e reproduzível; se o site bloquear, usar fallback
IPP ou download manual documentado.

## ADR-004 — Nenhum segredo no repositório

**Contexto:** senha do Wi-Fi e do roteador são necessárias para configuração.

**Decisão:** senhas são digitadas pelo usuário no app/instalador oficial;
scripts nunca gravam nem logam.

**Consequência:** configuração menos “mágica”, porém segura.

## ADR-005 — Teste de impressão com um ponto

**Contexto:** testar impressão gasta tinta e papel.

**Decisão:** a página de teste desenha **um único ponto preto** no canto
superior esquerdo, via `System.Drawing.Printing.PrintDocument`.

**Consequência:** verificação real com custo mínimo; o usuário confirma
visualmente.

## ADR-006 — Digitalização incluída na v1

**Contexto:** o usuário quer imprimir **e** digitalizar.

**Decisão:** instalar o pacote Epson completo (driver + Epson Scan 2) e testar
digitalização. Se o Scan 2 não funcionar, tentar WSD/eSCL.

**Consequência:** v1 um pouco maior; o critério de aceite inclui scan.

## ADR-007 — IP fixo na impressora (sem admin do roteador)

**Contexto:** o usuário não lembra a senha do roteador; sem reserva de DHCP.

**Decisão:** tentar IP fixo na impressora via EpsonNet Config/Setup, fora da
faixa do DHCP (ex.: `192.168.0.240`). Se não for possível, usar o IP atual e o
`scan` por MAC para corrigir a porta.

**Consequência:** independência do roteador; risco baixo de conflito se o IP
escolhido estiver fora da faixa.

## ADR-008 — Wi-Fi Direct só como contingência

**Contexto:** Wi-Fi Direct funciona sem roteador, mas tira a impressora da
rede e limita dispositivos.

**Decisão:** não usar como padrão; só se WPS/Smart Panel/USB falharem.

**Consequência:** plano B documentado, sem virar dívida.

## ADR-009 — Testes com runner próprio

**Contexto:** Pester 3.4 é antigo e não está garantido em outras máquinas.

**Decisão:** `tests/run-tests.ps1` com asserts simples, zero dependência.

**Consequência:** roda em qualquer Windows; menos recursos que Pester 5.
