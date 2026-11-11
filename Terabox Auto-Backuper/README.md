# Terabox Auto-Backuper

Aplicativo local (Windows) com interface web para sincronização automática de arquivos para o Terabox.

## Início Rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o app
python app.py

# 3. O navegador abrirá automaticamente em http://127.0.0.1:8765
```

## Funcionalidades

- Configuração de múltiplos mapeamentos (pasta/arquivo local → pasta remota no Terabox)
- Importação de lista colada no formato `origem; destino` (uma por linha)
- Opção de incluir/excluir subpastas por mapeamento
- **Prévia (dry-run)** antes de sincronizar: mostra o que será enviado, substituído ou ignorado
- Sync automático em background (watchdog + scheduler), respeitando a opção "Sync automático"
- Deduplicação por caminho exato + tamanho + MD5
- Arquivo alterado é **substituído no mesmo caminho** (sem pastas/arquivos com data)
- Nomes com emoji são sanitizados no Terabox; o Restaurar devolve o nome original
- Autenticação automática via perfil do navegador (Chrome/Edge/Firefox/Dia)
- Notificações toast do Windows
- Criptografia opcional por mapeamento (upload e restore corrigidos)
- Processo reverso: restaurar arquivos de um novo PC preservando a estrutura
- Autostart com o Windows

> O sync é um **backup unidirecional**: local → Terabox. O app não apaga
> arquivos remotos automaticamente quando um arquivo local é apagado.

## Importar uma lista de pastas/arquivos

Na aba **Configuração**, use o card **Importar lista (CSV)** e cole uma linha
por item:

```
C:\Users\marlo\Documentos; /Backup/Documentos
C:\Users\marlo\Fotos\foto.jpg; /Backup/Fotos
C:\Users\marlo\Projetos; /Backup/Projetos
```

- A origem pode ser uma pasta ou um arquivo.
- O destino é sempre uma pasta no Terabox.
- Linhas em branco e linhas começando com `#` são ignoradas.
- O app valida, mostra quantos mapeamentos serão criados e pede confirmação.

Depois de importar, clique em **Prévia do Sync** para revisar e só então
**Sincronizar Agora**.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Documentação

Toda a documentação está em `DOCS/`. Comece por `AGENTS.md`.

## Licença

MIT