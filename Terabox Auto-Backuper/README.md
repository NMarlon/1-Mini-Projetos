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
- Checkbox **Sincronizar** por mapeamento; o que estiver desmarcado não entra no backup manual nem no Auto-sync
- Importação de lista colada no formato `origem; destino` (uma por linha)
- Opção de incluir/excluir subpastas por mapeamento
- **Prévia (dry-run)** antes de sincronizar: mostra o que será enviado, substituído ou ignorado
- Sync automático em background (watchdog + scheduler), respeitando a opção "Sync automático"
- Deduplicação por caminho exato + tamanho + MD5
- Arquivo alterado é **substituído no mesmo caminho** (sem pastas/arquivos com data)
- Nomes com emoji são sanitizados no Terabox; o Restaurar devolve o nome original
- **Seleção de restauração persistente**: os checkboxes da aba Restaurar são lembrados ao recarregar o manifesto e ao reiniciar o app
- **Restaurar nas pastas originais**: cada arquivo volta para o `local_path` do mapeamento, mesclando pastas e substituindo arquivos existentes
- **Aviso de sobrescrita configurável**: pergunta antes de substituir (padrão) ou substitui direto, com relatório final
- Autenticação automática via perfil do navegador (Chrome/Edge/Firefox/Dia)
- Notificações toast do Windows
- Criptografia opcional por mapeamento (upload e restore corrigidos)
- Processo reverso também funciona em outro PC, casando os mapeamentos pelo caminho remoto/nome
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

## Selecionar o que entra no backup

Em **Mapeamentos Existentes**, cada mapeamento tem o checkbox **Sincronizar**:

- Marcado → entra no botão **Sincronizar Agora**, na **Prévia** e no **Auto-sync**.
- Desmarcado → não é enviado nem pelo botão nem pelo Auto-sync.
- **Selecionar todos** / **Desmarcar todos** mudam todos de uma vez.
- Desmarcar não apaga nada no Terabox; apenas para de enviar novos arquivos.
- O contador mostra quantos mapeamentos estão selecionados.

## Restaurar arquivos

Na aba **Restaurar**, depois de carregar o manifesto:

- A árvore abre agrupada por mapeamento e mostra o **destino original** de cada
  um. Não existe campo de pasta de destino manual.
- **Todos os arquivos já vêm marcados**; desmarque o que não quiser restaurar.
- Pastas existentes são mescladas; arquivos no mesmo caminho são substituídos.
- Antes de baixar, o app mostra quantos arquivos serão criados, substituídos ou
  ignorados por erro.
- Em **Configurações → Restauração**, a opção
  **“Perguntar antes de sobrescrever arquivos existentes”** vem ligada.
- A seleção fica salva no navegador e é restaurada ao recarregar o manifesto,
  trocar de aba, recarregar a página ou reiniciar o app.
- Arquivos de mapeamentos desmarcados no backup aparecem com o aviso
  **⚠️ backup desativado**, mas ainda podem ser restaurados manualmente.
- A seleção é local ao navegador/perfil; ela não é enviada ao Terabox.

## Testes

```bash
python -m unittest discover -s tests -v
node --test tests/test_restore_tree.cjs
```

## Documentação

Toda a documentação está em `DOCS/`. Comece por `AGENTS.md`.

## Licença

MIT