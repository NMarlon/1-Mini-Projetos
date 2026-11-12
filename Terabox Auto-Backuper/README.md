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
- Importação de lista colada no formato `origem; destino` (uma por linha), com terceiro campo opcional `pasta`/`arquivo`
- Caminhos locais ainda inexistentes são aceitos: pastas são criadas e arquivos únicos criam só a pasta-pai
- Opção de incluir/excluir subpastas por mapeamento
- **Prévia (dry-run)** antes de sincronizar: mostra o que será enviado, substituído ou ignorado
- Sync automático em background (watchdog + scheduler), respeitando a opção "Sync automático"
- Deduplicação por caminho exato + tamanho + MD5
- Arquivo alterado é **substituído no mesmo caminho** (sem pastas/arquivos com data)
- Nomes com emoji são sanitizados no Terabox; o Restaurar devolve o nome original
- **Seleção de restauração persistente**: os checkboxes da aba Restaurar são lembrados ao recarregar o manifesto e ao reiniciar o app
- **Restaurar nas pastas originais**: cada arquivo volta para o `local_path` do mapeamento, mesclando pastas e substituindo arquivos existentes
- **Aviso de sobrescrita configurável**: pergunta antes de substituir (padrão) ou substitui direto, com relatório final
- **Configuração remota**: salva os mapeamentos e o caminho local de cada PC em um JSON no Terabox, com atalho fixo na raiz e importação assistida em PC novo
- Autenticação automática via perfil do navegador (Chrome/Edge/Firefox/Dia)
- Notificações toast do Windows
- Criptografia opcional por mapeamento (upload e restore corrigidos)
- Processo reverso também funciona em outro PC, casando os mapeamentos por `uid`, caminho remoto/nome
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
- A origem pode ainda não existir. Nesse caso, informe o tipo no terceiro campo:
  `C:\Saves\Meu Mundo; /Backup/Saves; pasta` ou
  `C:\Saves\Meu Mundo\level.dat; /Backup/Saves; arquivo`.
  Sem o terceiro campo, o app assume pasta.
- Pastas são criadas na importação. Arquivo único cria somente a pasta-pai e
  nunca um arquivo vazio.
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

## Configuração remota e PC novo

Em **Configurações → Configuração no Terabox** o app mantém um arquivo JSON
(por padrão `/config-terabox-auto-backup/terabox-auto-backup.json`) com:

- o `uid` estável de cada mapeamento;
- o caminho remoto, o tipo (pasta/arquivo) e as opções;
- o caminho local usado por **cada computador** (nunca cookies, tokens ou a
  chave de criptografia).

O app mescla o arquivo antes de gravar: cada PC altera apenas a sua própria
entrada, sem apagar os caminhos dos outros. Também cria o atalho fixo
`/_terabox_autobackup_config.json` na raiz do Terabox para localizar o arquivo
mesmo se a pasta ou o nome forem alterados.

Em um PC novo:

1. Conecte ao Terabox. Se houver configuração remota, aparece um banner
   **Configuração encontrada no Terabox**.
2. Clique em **Revisar importação** e confira cada mapeamento.
3. Escolha o caminho local de cada linha; use o **rebase de prefixo** para
   trocar `C:\Users\...` por `D:\...` em lote.
4. Marque o que deseja importar e confirme. Nada é importado silenciosamente.
5. Depois, use **Restaurar** para baixar os arquivos nas pastas escolhidas.

Mapeamentos de arquivo único podem apontar para um arquivo que ainda não
existe; basta que a pasta pai exista ou possa ser criada. O Restaurar cria o
arquivo. Configuração remota vazia ou inválida não é sobrescrita sem
confirmação.

## Testes

```bash
python -m unittest discover -s tests -v
node --test tests/test_restore_tree.cjs tests/test_remote_config.cjs
```

## Documentação

Toda a documentação está em `DOCS/`. Comece por `AGENTS.md`.

## Licença

MIT