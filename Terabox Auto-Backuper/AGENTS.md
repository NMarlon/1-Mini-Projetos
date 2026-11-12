# AGENTS.md — Terabox Auto-Backuper

> **Leia este arquivo primeiro.** Ele é o ponto de entrada para qualquer IA/agente que continue este projeto.
> Referência rápida para regras, objetivo, estrutura e onde encontrar cada informação.

---

## 1. Objetivo do Projeto

Criar um aplicativo local (Windows) com interface web aberta no navegador, que:

1. Permite configurar **múltiplos mapeamentos** de pasta/arquivo local → pasta remota no Terabox (com opção de incluir subpastas)
2. Sincroniza automaticamente em background (otimizado: fila, rate-limit, retry, deduplicação por MD5)
3. Inicia com o Windows (autostart via registro HKCU)
4. Extrai credenciais do Terabox automaticamente a partir do perfil do navegador local (Chrome/Edge/Firefox) via `rookie-cookies` (suporta App-Bound Encryption v20)
5. jsToken obtido raspando o HTML de `/main` do Terabox
6. Notificações toast do Windows ao concluir/falhar sync
7. Criptografia opcional por mapeamento (Fernet)
8. Botão "Restaurar": lê manifesto no Terabox e permite download seletivo para um novo PC

## 2. Regras Obrigatórias (LEIA ANTES DE QUALQUER COISA)

1. **Tudo relacionado a este projeto DEVE estar na pasta do projeto**: `C:\MarlonScripts\1-Mini Projetos\Terabox Auto-Backuper`
2. **Toda documentação está em `DOCS/`**. Consulte os arquivos listados na seção 4.
3. **Commit ao final de cada tarefa concluída.** Sem exceção. Use mensagens descritivas.
4. **Autonomia máxima**: execute o máximo possível sem ação humana. O usuário pode estar ausente.
5. **DÚVIDAS ou AMBIGUIDADES**: PARE e PERGUNTE ao usuário antes de prosseguir. Não assuma.
6. **Se encontrar erros/problemas**: pesquise soluções, apresente os melhores métodos profissionais. Registre em `DOCS/ERRORS_LEARNINGS.md`.
7. **Não modificar arquivos fora da pasta do projeto** (exceto registro do Windows para autostart, que é necessário).
8. **Idioma da interface e logs**: Português (BR).

## 3. Estrutura de Pastas

```
Terabox Auto-Backuper/
├── AGENTS.md                 # Este arquivo (ponto de entrada)
├── README.md                 # Visão geral para humanos
├── requirements.txt          # Dependências Python
├── .gitignore
├── app.py                    # Entry point: inicia servidor + abre navegador
├── backend/                  # Código backend (FastAPI)
│   ├── __init__.py
│   ├── api.py                # Rotas FastAPI
│   ├── config.py             # Configurações globais
│   ├── database.py           # SQLite (aiosqlite)
│   ├── models.py             # Pydantic + tabelas
│   ├── terabox_client.py     # Cliente Terabox (list/upload/download/precreate/create)
│   ├── auth.py               # rookie-cookies + jsToken scraping/refresh
│   ├── sync_engine.py        # Motor de sync (plano, execução, manifesto v2)
│   ├── sync_plan.py          # Decisão pura de dedup (upload/replace/skip)
│   ├── paths.py              # Normalização POSIX + sanitização de nomes remotos
│   ├── csv_import.py         # Importação de lista "origem; destino"
│   ├── file_monitor.py       # Watchdog
│   ├── scheduler.py          # APScheduler
│   ├── notifications.py      # Toast Windows
│   └── windows_startup.py    # Autostart Windows
├── frontend/                 # SPA (HTML/CSS/JS vanilla)
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── js/restore_tree.js  # Árvore/seleção pura da aba Restaurar
├── DOCS/                     # Toda documentação
├── data/                     # SQLite DB, logs (gitignored)
├── tests/                    # Testes
└── scripts/                  # Scripts auxiliares
```

## 4. Mapa de Documentação (DOCS/)

| Arquivo | Conteúdo | Quando ler |
|---|---|---|
| `DOCS/README.md` | Índice da documentação | Sempre primeiro após AGENTS.md |
| `DOCS/ARCHITECTURE.md` | Arquitetura detalhada, decisões de design, fluxos | Antes de implementar qualquer feature |
| `DOCS/TASKS.md` | Lista de tarefas com descrição e como proceder | Para saber o que fazer a seguir |
| `DOCS/FUTURE.md` | Tarefas futuras, bugs conhecidos, ideias | Para contexto de longo prazo |
| `DOCS/ERRORS_LEARNINGS.md` | Erros cometidos e aprendizados | Antes de implementar, para evitar repetir erros |
| `DOCS/API_REFERENCE.md` | Referência dos endpoints da API local | Ao trabalhar no frontend ou integrações |
| `DOCS/TERABOX_API.md` | Endpoints e comportamento da API do Terabox | Ao trabalhar no terabox_client |

## 5. Stack Tecnológica

| Camada | Escolha |
|---|---|
| Backend | Python 3.14 + FastAPI (async) + uvicorn |
| Frontend | HTML/CSS/JS vanilla (sem build step) |
| DB | SQLite via aiosqlite |
| HTTP | httpx (async) + curl (subprocess para upload binário) |
| File monitor | watchdog |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Cookies | rookie-cookies (suporta Chrome App-Bound v20) |
| Criptografia | cryptography (Fernet) |
| Notificações | winotify |
| Autostart | Registro Windows (HKCU\Run) |

## 6. Fases de Implementação

- **Fase 1 — Fundação (MVP)**: estrutura, backend básico, frontend básico, cliente Terabox, auth automática, sync manual, notificações
- **Fase 2 — Automação**: watchdog, APScheduler, fila otimizada, autostart, manifesto + restaurar
- **Fase 3 — Polimento**: criptografia, histórico, testes

Consulte `DOCS/TASKS.md` para a lista detalhada.

## 7. Comandos Úteis

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o app
python app.py

# Rodar testes
python -m pytest tests/

# Git: commit ao final de cada tarefa
git add -A && git commit -m "feat: descrição da tarefa"
```

## 8. Histórico de Commits

Consulte `git log` para o histórico completo. Cada commit corresponde a uma tarefa concluída.