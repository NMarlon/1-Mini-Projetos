# AGENTS.md — Melhor Marlon PC

Este arquivo é a **porta de entrada** do projeto. Leia até o fim antes de
alterar qualquer arquivo. Ele diz o objetivo, as regras, o estado atual e onde
está cada informação.

## 1. Objetivo

Deixar este PC (Windows 11) com funcionalidades específicas do Marlon,
começando por:

1. **Impressora Epson L3150 na rede local** — imprimir **e digitalizar** pelo
   Wi-Fi do roteador, sem cabo USB no dia a dia.
2. Uma CLI única (`bin/marlon.ps1`) para diagnosticar, instalar, verificar e
   consertar a impressora.

O projeto é uma suíte: a impressora é a feature `printer`; novas features
entram em `src/features/<nome>/`.

## 2. Estado atual (2026-11-19)

- **T00 concluída**: estrutura, documentação base e protocolo.
- A impressora **não está na LAN** (varredura de 192.168.0.1–254 nas portas
  9100/631/515: nenhuma aberta).
- Rede do PC: Ethernet `192.168.0.17/24`; Wi-Fi `FamiliaViana_5G` (5 GHz,
  WPA2, sinal 35% / -84 dBm); gateway `192.168.0.1` (Claro/Kaon).
- A rede **2,4 GHz existe** (confirmado pelo usuário), mas o nome exato ainda
  não foi registrado.
- Sem driver Epson instalado; só “Microsoft Print to PDF”.
- Sessão sem privilégio de administrador (UAC necessário para instalar).
- Próxima tarefa: **T01** (inventário) e **T02** (descoberta), depois a
  sessão assistida **T10** (WPS + driver + teste).

> Atualize esta seção ao final de cada tarefa.

## 3. Ordem de leitura obrigatória

1. `AGENTS.md` (este arquivo)
2. [`DOCS/00-OVERVIEW.md`](DOCS/00-OVERVIEW.md) — visão e escopo
3. [`DOCS/06-TASKS.md`](DOCS/06-TASKS.md) — **estado e próxima tarefa**
4. [`DOCS/04-SETUP-RUNBOOK.md`](DOCS/04-SETUP-RUNBOOK.md) — se for mexer na
   impressora
5. [`DOCS/02-HARDWARE-L3150.md`](DOCS/02-HARDWARE-L3150.md) — botões e
   procedimentos oficiais
6. [`DOCS/03-NETWORK-AND-ROUTER.md`](DOCS/03-NETWORK-AND-ROUTER.md) — rede e
   roteador
7. [`DOCS/01-ARCHITECTURE.md`](DOCS/01-ARCHITECTURE.md) — módulos e fluxo
8. [`DOCS/05-OPERATIONS.md`](DOCS/05-OPERATIONS.md) — comandos e logs
9. [`DOCS/08-ERRORS-AND-LESSONS.md`](DOCS/08-ERRORS-AND-LESSONS.md) — erros já
   cometidos
10. [`DOCS/09-DECISIONS.md`](DOCS/09-DECISIONS.md) — decisões arquiteturais
11. [`DOCS/10-VERIFICATION.md`](DOCS/10-VERIFICATION.md) — critérios de aceite
12. [`DOCS/11-REPO-PROTOCOL.md`](DOCS/11-REPO-PROTOCOL.md) — commits,
    autonomia e continuidade
13. [`DOCS/07-BACKLOG.md`](DOCS/07-BACKLOG.md) — futuro
14. [`DOCS/12-TROUBLESHOOTING.md`](DOCS/12-TROUBLESHOOTING.md) — sintomas e
    soluções

## 4. Regras rígidas

### 4.1 Você DEVE

- Trabalhar em **uma tarefa por vez** e commitar ao final.
- Atualizar `DOCS/06-TASKS.md`, `DOCS/08-ERRORS-AND-LESSONS.md` e, se mudar
  decisão, `DOCS/09-DECISIONS.md`.
- Preferir automação; agrupar ações manuais em uma sessão curta.
- Usar fontes oficiais (Epson) e verificar SHA-256 de downloads.
- Manter segredos (senha do Wi-Fi, senha do roteador) fora do repositório e
  dos logs.
- Ser idempotente: rodar duas vezes não pode duplicar impressora ou porta.
- Testar o que mudou antes de commitar.

### 4.2 Você NÃO DEVE

- Fazer `git add .` nem commitar outros projetos.
- Fazer `push` sem pedido explícito.
- Alterar o roteador sem autorização.
- Tentar senha padrão do roteador.
- Imprimir sem confirmação (gasta tinta/papel).
- Usar Wi-Fi Direct como conexão permanente.
- Instalar driver de site de terceiros.
- Apagar `vendor/`, `reports/` ou `logs/` sem motivo.
- Guardar senha em `config/`, `reports/` ou `logs/`.

### 4.3 Pare e pergunte

- Dúvida de escopo (só imprimir × digitalizar).
- Necessidade de senha do roteador ou do Wi-Fi.
- Ação destrutiva (reset de rede da impressora, reset do roteador).
- Conflito entre documentação e realidade.
- Qualquer mudança que possa derrubar a rede.

## 5. Commits

- **Um commit por tarefa concluída.**
- Prefixos: `feat(marlon-pc):`, `fix(marlon-pc):`, `docs(marlon-pc):`,
  `chore(marlon-pc):`.
- Antes de commitar: `git status` e conferir que só há arquivos deste projeto.
- Stage explícito: `git add -- "Marlon/Melhor Marlon PC"`.
- **Nunca** `push`.
- Se o commit falhar, resolva e registre em
  `DOCS/08-ERRORS-AND-LESSONS.md`.

## 6. Autonomia

O usuário pediu autonomia máxima. Faça sozinho tudo que não depende de:

- apertar botão físico da impressora;
- aprovar UAC;
- digitar senha;
- autorizar impressão.

Quando precisar, pare, explique em 3 linhas e agrupe tudo em uma sessão.

## 7. Estrutura do projeto

```text
Melhor Marlon PC/
├─ AGENTS.md              ← este arquivo
├─ README.md
├─ .gitignore
├─ bin/marlon.ps1         ← CLI única
├─ src/MarlonPC.psm1
├─ src/core/              ← log, config, elevação, relatório
├─ src/features/printer/  ← inventário, descoberta, driver, install, verify
├─ src/data/epson-oui.csv
├─ config/                ← printer.json, site.json (sem segredos)
├─ tools/                 ← fetch-driver.ps1, inspect-driver.ps1
├─ tests/run-tests.ps1
├─ DOCS/                  ← toda a documentação
├─ vendor/                ← driver baixado (fora do Git)
├─ reports/               ← relatórios (fora do Git)
└─ logs/                  ← logs (fora do Git)
```

## 8. Fluxo resumido

```powershell
# diagnóstico
.\bin\marlon.ps1 doctor
.\bin\marlon.ps1 printer scan
.\bin\marlon.ps1 printer status -Ip 192.168.0.x

# instalação (admin)
.\bin\marlon.ps1 printer install -Ip 192.168.0.x

# verificação (dry-run por padrão)
.\bin\marlon.ps1 printer verify -Ip 192.168.0.x

# teste de impressão (1 ponto no canto)
.\bin\marlon.ps1 printer test -Ip 192.168.0.x -Print
```

## 9. Definition of Done

Uma tarefa só termina quando:

- o script roda no PowerShell 5.1 sem erro;
- os testes relevantes passam;
- a documentação da tarefa foi atualizada;
- o resultado foi validado (quando aplicável);
- o commit foi feito (ou o motivo de não ter sido registrado).

O projeto (v1) só termina quando `DOCS/10-VERIFICATION.md` estiver cumprido:
impressora na rede, driver instalado, página com um ponto impressa e
digitalização funcionando.
