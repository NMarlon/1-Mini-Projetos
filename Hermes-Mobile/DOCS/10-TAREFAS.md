# 10 — Tarefas do projeto

Última atualização: **2026-11-16**

> **Para a próxima IA:** encontre a tarefa 🟡, leia o “como proceder” e
> continue. Atualize o status e faça commit ao terminar.

---

## Legenda

| Símbolo | Significado |
|---|---|
| 🟢 | Feito e validado |
| 🟡 | Em andamento |
| 🔴 | Bloqueado |
| ⚪ | Não iniciado |

---

## Fase 0 — Estrutura e documentação base

**Status:** 🟢

- [x] Criar `Hermes-Mobile/`.
- [x] Criar `.gitignore`.
- [x] Criar `README.md`.
- [x] Criar `AGENTS.md`.
- [x] Criar `DOCS/00` a `DOCS/12`.
- [x] Commit inicial.

**Como proceder se precisar refazer:** copiar a estrutura de
`DOCS/00-INDICE.md`; manter o padrão do projeto OpenCode.

---

## Fase 1 — Auth + `hermes serve` local

**Status:** 🟡

- [ ] Criar `scripts/lib/common.ps1`.
- [ ] Criar `scripts/Configurar-Hermes.ps1`.
- [ ] Gerar usuário/senha/hash/secret.
- [ ] Gravar no `.env` com backup e ACL.
- [ ] Definir `dashboard.public_url`.
- [ ] Subir `hermes serve` em `127.0.0.1:9119`.
- [ ] Validar `/api/status` com `auth_required: true` e `auth_providers`.
- [ ] Validar login local.
- [ ] Criar `scripts/Status-Diagnostico.ps1`.
- [ ] Commit.

**Critério de aceite:**

```json
{
  "version": "0.23.1",
  "auth_required": true,
  "auth_providers": ["basic"],
  "profiles": ["..."]
}
```

**Como proceder:**

1. Ler `DOCS/02-ARQUITETURA-E-CONEXAO.md` (ADRs 002, 004, 005).
2. Rodar `hermes config get dashboard.public_url`.
3. Ver `DOCS/04-SCRIPTS-E-COMANDOS.md` seção 3.
4. Se o servidor não subir, ver `DOCS/06-TROUBLESHOOTING.md` seção 2.

---

## Fase 2 — Tailscale Serve `:8443`

**Status:** ⚪

- [ ] Criar `scripts/Configurar-Tailscale.ps1`.
- [ ] Criar handler `:8443 → 127.0.0.1:9119`.
- [ ] Confirmar que `:443 → 127.0.0.1:28894` continua.
- [ ] Testar `/api/status` via HTTPS.
- [ ] Testar login via HTTPS.
- [ ] Commit.

**Critério de aceite:**

```powershell
tailscale serve status
# deve mostrar 443 (OpenCode) e 8443 (Hermes)
curl.exe -s https://marlon-dell-pc.tail6ded59.ts.net:8443/api/status
# JSON com auth_required: true
```

---

## Fase 3 — Autostart + scripts operacionais

**Status:** ⚪

- [ ] Criar `scripts/Iniciar-Servidor.ps1`.
- [ ] Criar `scripts/Iniciar-Mobile.ps1`.
- [ ] Criar `scripts/Parar-Mobile.ps1`.
- [ ] Criar `scripts/Instalar-Autostart.ps1`.
- [ ] Criar `scripts/Remover-Autostart.ps1`.
- [ ] Criar `scripts/Ver-Credenciais.ps1`.
- [ ] Criar `scripts/Manter-Acordado.ps1` (não rodar).
- [ ] Criar `scripts/Instalar-Tudo.ps1`.
- [ ] Testar parar/subir e autostart.
- [ ] Commit.

**Critério de aceite:**

- `Get-ScheduledTask -TaskName "Hermes Mobile - Servidor"` existe.
- Após `Parar-Mobile.ps1` + `Iniciar-Servidor.ps1`, a URL volta.
- `Ver-Credenciais.ps1 -Revelar` mostra a senha.

---

## Fase 4 — Validação no celular e fechamento

**Status:** ⚪

- [ ] Gerar checklist do Pomelu (`DOCS/03-GUIA-RAPIDO.md`).
- [ ] Testar a URL no Chrome do PC (tela de login).
- [ ] Preencher `DOCS/12-VERIFICACAO-E-TESTES.md` com evidências.
- [ ] Atualizar `DOCS/09-ERROS-E-APRENDIZADOS.md`.
- [ ] Atualizar `DOCS/01-VISAO-GERAL.md` (estado atual).
- [ ] Atualizar `AGENTS.md` (data/estado).
- [ ] Commit final.

**Ação humana necessária:** instalar o Pomelu no celular e conectar.

---

## Fase 5 — Plugin Pomelu (backlog)

**Status:** ⚪ (backlog)

- [ ] Avaliar o plugin `ateymoori/pomelu-hermes-plugin`.
- [ ] Instalar `hermes plugins install ateymoori/pomelu-hermes-plugin --enable`.
- [ ] Rodar `hermes pomelu setup`.
- [ ] Reiniciar o `hermes serve`.
- [ ] Testar push com o app fechado.
- [ ] Documentar em `DOCS/11-BACKLOG-E-IDEIAS.md`.

**Decisão do Marlon em 16/11/2026:** deixar no backlog.

---

## Tarefas avulsas

### T-01 — Investigar `install out of sync`

**Status:** ⚪

- O `hermes` imprime aviso em todo comando.
- `hermes doctor` mostra o runtime staged ativo.
- **Não** rodar update/rebuild sem backup (REGRA 13).
- Ideia: `hermes update` em uma janela com backup do `.env` e da home.

### T-02 — Revisar o plugin de push

**Status:** ⚪

- Ler `ateymoori/pomelu-hermes-plugin` e o `relay/`.
- Verificar o que sai da máquina.
- Decidir com o Marlon.

### T-03 — Documentar o Desktop coexistindo

**Status:** ⚪

- Testar abrir o Hermes Desktop enquanto o `hermes serve` do projeto roda.
- Verificar se ele anexa ao mesmo servidor ou sobe outro.
- Documentar em `02-ARQUITETURA`.
