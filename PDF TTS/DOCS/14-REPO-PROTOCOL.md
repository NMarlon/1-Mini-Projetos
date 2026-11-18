# 14 — Protocolo do repositório e continuidade

Este documento transforma o protocolo pedido pelo usuário em regras
permanentes para qualquer IA ou pessoa que continuar o projeto.

Ele complementa o `AGENTS.md`; se houver conflito, **o `AGENTS.md` vence** e a
divergência deve ser corrigida aqui.

## 1. Papel esperado

Aja como **Desenvolvedor Full-Stack experiente**:

- entenda o fluxo completo (PDF → texto → TTS → MP3/M4B/SRT → app);
- preserve a arquitetura e os padrões existentes;
- prefira soluções simples, testáveis e documentadas;
- não introduza dependências desnecessárias;
- pense em quem vai manter o projeto depois (outra IA ou pessoa).

Não é um projeto só de script: o produto tem CLI, app local, interface web,
fila, empacotamento Windows e documentação. Trate-o como produto.

## 2. Tudo que é fundamental fica no repositório

O repositório deve permitir que outra IA entenda, altere, teste e reconstrua o
projeto **sem depender de arquivos perdidos fora dele**.

### Versionado

- código em `src/pdf_tts/`;
- testes em `tests/`;
- scripts em `scripts/`;
- configuração em `config/`;
- documentação em `DOCS/`;
- `AGENTS.md`, `README.md`, `pyproject.toml`, `requirements.lock.txt`;
- `manifests/` dos projetos curados;
- `samples/` sintéticas;
- scripts de empacotamento em `packaging/`;
- imagens do tutorial em `DOCS/assets/`.

### Gerado localmente (ignorado, mas reconstruível)

| Item | Onde fica | Como reconstruir |
|---|---|---|
| `.venv/` | raiz | `.\scripts\setup.ps1` |
| `input/*.pdf` | raiz | copiar manualmente; ver `input/README.md` |
| `content/` | raiz | `python -m pdf_tts extract --project all` |
| `output/` | raiz | `python -m pdf_tts build/assemble` ou app |
| `cache/` | raiz | recriado pelo build/app |
| `logs/` | raiz/app | recriado ao rodar |
| `dist/` e `build/` | raiz | `packaging/build_*.ps1` |
| `manifests/AUTO-*.json` | raiz | gerado pelo app |
| `temp/` | raiz | arquivos do usuário; ignorado |

### Por que PDFs, texto e áudio não são versionados

- Direitos autorais do material didático.
- Tamanho (áudio ~1,3 GB; PDFs ~73 MB).
- O repositório é público.

Isso é uma **exceção legal deliberada**, não uma falha de organização. Os
manifests e o código permitem reproduzir o build quando os PDFs são colocados
em `input/`.

### Dependências externas

- Python 3.11 instalado na máquina (não versionamos o runtime).
- FFmpeg/ffprobe no `PATH` para o modo curado; o app portátil leva uma cópia.
- Internet para o Edge TTS.

Toda dependência Python deve estar em `pyproject.toml` **e** em
`requirements.lock.txt`. Se adicionar uma nova, atualize os dois e documente.

## 3. `DOCS/` é a fonte da documentação

A pasta `DOCS/` contém toda a documentação. Não crie documentação fundamental
fora dela, exceto `AGENTS.md` e `README.md`.

Mapa:

| Documento | Conteúdo |
|---|---|
| `00-OVERVIEW.md` | visão geral e escopo |
| `01-ARCHITECTURE.md` | arquitetura, módulos, fluxos |
| `02-RESEARCH-TTS.md` | pesquisa de vozes/motores |
| `03-PDF-PIPELINE.md` | extração, perfis e modos de conteúdo |
| `04-AUDIO-PIPELINE.md` | TTS, FFmpeg e montagem |
| `05-OPERATIONS.md` | comandos e troubleshooting |
| `06-TASKS.md` | estado atual, tarefas e diário |
| `07-BACKLOG.md` | ideias futuras e dívidas |
| `08-ERRORS-AND-LESSONS.md` | erros e aprendizados |
| `09-DECISIONS.md` | ADRs |
| `10-VOICE-AND-PRONUNCIATION.md` | voz e pronúncia |
| `11-VERIFICATION.md` | critérios de aceite |
| `12-ONE-CLICK-APP.md` | app, API, empacotamento |
| `13-COMO-BAIXAR-O-PDF.md` | tutorial para o usuário final |
| `14-REPO-PROTOCOL.md` | este protocolo |

Regras:

- linkar documentos entre si, sem duplicar a mesma informação em vários lugares;
- toda tarefa concluída atualiza `06-TASKS.md`;
- todo erro relevante entra em `08-ERRORS-AND-LESSONS.md`;
- toda decisão estrutural entra em `09-DECISIONS.md`;
- mudanças no app/empacotamento atualizam `12-ONE-CLICK-APP.md`;
- se mudar critério de aceite, atualize `11-VERIFICATION.md`.

## 4. `AGENTS.md` é a porta de entrada

O `AGENTS.md` deve sempre ter:

- objetivo do projeto;
- ordem de leitura dos documentos;
- estado atual resumido;
- regras de autonomia, commit e ambiguidade;
- estrutura do repositório;
- comandos essenciais;
- o que não pode regredir;
- Definition of Done.

Quem chega deve conseguir, em menos de 10 minutos:

1. entender o que o projeto faz;
2. saber onde está cada assunto;
3. saber o que pode e o que não pode fazer;
4. saber o próximo comando/tarefa.

## 5. Erros e aprendizados

`DOCS/08-ERRORS-AND-LESSONS.md` é obrigatório. Cada erro relevante deve ter:

- sintoma;
- causa;
- solução;
- como evitar.

Erros já registrados incluem: cache do Edge, WAV/MP3, loudness, sumário virando
capítulo, `Failed to fetch`, Smart App Control e janelas de CMD.

## 6. Tarefas e continuidade

`DOCS/06-TASKS.md` é o quadro vivo. Deve conter:

- estado atual no topo;
- tabela de tarefas com status e commit;
- descrição de cada tarefa;
- critério de aceite;
- diário de progresso;
- próximo passo e comando exato.

Ao parar no meio:

- deixe o status `[~]` e o comando para continuar;
- registre o que já foi feito;
- não deixe uma tarefa “meio feita” sem documentação.

## 7. Backlog

`DOCS/07-BACKLOG.md` guarda o que **não** será feito agora:

- ideias de produto;
- dívidas técnicas;
- bugs não urgentes;
- melhorias de áudio/documentação.

Não implemente item do backlog sem o usuário pedir ou sem mover para
`06-TASKS.md`.

## 8. Commits

- Um commit ao final de **cada tarefa** concluída.
- Mensagens convencionais: `feat`, `fix`, `build`, `docs`, `test`, `chore`.
- Antes do commit: `git status`, `ruff`, `pytest`.
- Commitar apenas arquivos deste projeto. Nunca incluir mudanças de outros
  projetos ou `temp/`.
- Nunca `push` sem pedido explícito.
- Se o commit falhar, resolver e registrar.

O usuário usa os commits como pontos de rollback; um trabalho sem commit é um
trabalho em risco.

## 9. Autonomia

O usuário autorizou autonomia máxima. Continue sem pedir confirmação para:

- ler/editar arquivos do projeto;
- instalar dependências no `.venv`;
- rodar testes, lint, extração, builds;
- gerar áudio e portáteis;
- fazer commits locais;
- atualizar documentação.

Interrompa apenas para:

- ambiguidade real de escopo;
- credencial/conta que você não tem;
- ação destrutiva sem backup;
- mudança de voz/motor/ritmo;
- risco de perda de dados;
- decisão de produto que o usuário precisa tomar.

## 10. Dúvidas e ambiguidades

**Pare e pergunte.** Não invente requisito nem “conserte” algo ambíguo por
conta própria. Exemplos:

- “Tudo” significa referências ou inclusive cabeçalhos/páginas?
- O app deve ser um `.exe` único ou pasta portátil?
- O usuário quer OCR agora ou no backlog?
- Pode apagar `output/`/`cache/`?
- A versão principal é a assinada ou a PyInstaller?

Se a resposta não estiver clara na documentação ou no código, pergunte e
registre a decisão depois.

## 11. Erros, problemas e soluções profissionais

Ao encontrar um problema:

1. reproduza;
2. colete evidência (log, comando, stack trace);
3. identifique a causa raiz;
4. escolha a solução mais simples que não crie dívida;
5. teste a correção;
6. registre em `08-ERRORS-AND-LESSONS.md`;
7. se for decisão estrutural, registre em `09-DECISIONS.md`;
8. commit.

Não faça “gambiarra silenciosa”. Se precisar de workaround, documente o motivo e
o caminho para remover depois.

## 12. Checklist de início de sessão

1. Ler `AGENTS.md`.
2. Ler o topo de `06-TASKS.md`.
3. Ver `git status` e `git log --oneline -5`.
4. Rodar `ruff` e `pytest` se for mexer em código.
5. Identificar a tarefa atual e o próximo comando.
6. Se houver dúvida, perguntar antes de editar.

## 13. Checklist de fim de sessão

1. Código/testes passando.
2. `06-TASKS.md` atualizado.
3. `08-ERRORS-AND-LESSONS.md` atualizado se houve erro.
4. `09-DECISIONS.md` atualizado se houve decisão.
5. `12-ONE-CLICK-APP.md` atualizado se mexeu no app.
6. `git status` revisado.
7. Commit feito.
8. Se parou no meio, comando de continuação registrado.

## 14. Arquivos que nunca devem ser commitados

- `input/*.pdf`;
- `content/`;
- `output/`;
- `cache/`;
- `logs/`;
- `dist/`;
- `build/`;
- `.venv/`;
- `manifests/AUTO-*.json`;
- `temp/`;
- segredos, tokens, arquivos pessoais.

## 15. Definition of Done do repositório

O repositório está saudável quando:

- um clone novo consegue criar o `.venv` com `scripts/setup.ps1`;
- `ruff` e `pytest` passam;
- os comandos do `README`/`AGENTS` funcionam;
- a documentação permite continuar sem o histórico do chat;
- os dois livros continuam verificáveis quando os PDFs são colocados em
  `input/`;
- o app principal pode ser reconstruído por `packaging/build_python_portable.ps1`;
- o tutorial de download pode ser regenerado por
  `python scripts/build_download_tutorial.py`;
- nenhum arquivo fundamental depende de `temp/` ou de uma pasta externa.
