# Como Usar o Terabox Auto-Backuper (Modo Manual)

> Este guia é para quando a conexão automática não funcionar.
> Siga os passos com calma — é mais simples do que parece!

---

## Passo 1: Faça login no Terabox

1. Abra o seu navegador (Chrome, Edge, Firefox, Dia, etc.)
2. Acesse **https://www.terabox.com**
3. Faça login com a sua conta

> ⚠️ **Importante**: Mantenha a aba do Terabox aberta enquanto copia os cookies!

---

## Passo 2: Copiar os cookies

### No Chrome ou Edge:
1. Pressione **F12** (abre as ferramentas de desenvolvedor)
2. Clique na aba **"Application"** (ou "Aplicativo")
3. No menu lateral esquerdo, clique em **"Cookies"** → **"https://www.terabox.com"**
4. Você verá uma lista de cookies. Procure estes:
   - **ndus** (o mais importante!)
   - **csrfToken**
   - **browserid**
   - **lang**
   - **ndut_fmt**
5. Para cada cookie, copie o **Value** (valor) e anote no formato: `nome=valor`

### No Firefox:
1. Pressione **F12**
2. Clique na aba **"Storage"** (ou "Armazenamento")
3. No menu lateral, clique em **"Cookies"** → **"https://www.terabox.com"**
4. Copie os mesmos cookies listados acima

### No navegador Dia:
1. Pressione **F12** ou **Ctrl+Shift+I**
2. Vá para **"Application"** → **"Cookies"** → **"https://www.terabox.com"**
3. Copie os cookies listados acima

---

## Passo 3: Montar a string de cookies

Junte todos os cookies no formato abaixo (separados por ponto-e-vírgula):

```
ndus=SEU_VALOR_NDUS; csrfToken=SEU_VALOR_CSRF; browserid=SEU_VALOR_BROWSERID; lang=en; ndut_fmt=SEU_VALOR_NDUT
```

**Exemplo:**
```
ndus=Y2WGHuyteHuiaUpoEH6hYtux6CgXpzvgKtSae7mn; csrfToken=paly39LI3jaMSTaua21Acihd; browserid=NyE1HVC7KvGFgOGiFOjsHNvca_90Rx; lang=en; ndut_fmt=abc123
```

> ⚠️ **Dica**: Se não encontrar `ndut_fmt`, pode deixar de fora. O `ndus` é o único obrigatório.

---

## Passo 0: Navegador Dia (recomendado se você usa o Dia)

1. Faça login no Terabox no seu navegador **Dia**
2. No app, selecione **"Dia"** no dropdown
3. Escolha o perfil (ex: **Default**). O ícone indica:
   - ✅ = perfil logado no Terabox
   - ❌ = perfil sem login no Terabox
   - ❔ = não foi possível verificar (Dia aberto)
4. Clique em "Conectar ao Terabox"
5. O app vai **fechar e reabrir o Dia automaticamente** para ler os cookies — confirme quando perguntado

> 💡 O Dia é um app da Windows Store, então os dados ficam em uma pasta especial (Packages). O app já sabe onde procurar.

---

## Passo 0b: Selecionar o perfil correto (Chrome/Edge)

Se você tem vários perfis no Chrome (ex: Marlon, Wanderson, etc.):

1. No app, selecione **"Chrome"** no dropdown de navegador
2. Um segundo dropdown aparecerá com os perfis
3. Perfis com ✅ têm cookie do Terabox (estão logados)
4. Selecione o perfil correto (ex: "Marlon")
5. Clique em **"Conectar ao Terabox"**

Se nenhum perfil mostrar ✅, faça login no Terabox nesse perfil primeiro.

---

## Passo 4: Colar no app (modo Manual)

1. Abra o Terabox Auto-Backuper no navegador (http://127.0.0.1:8765)
2. Na aba **"Configuração"**, encontre a seção de autenticação
3. No dropdown **"Navegador"**, selecione **"Manual (colar cookies)"**
4. Cole a string de cookies no campo que aparecer
5. Clique em **"Conectar com cookies manuais"**

---

## Passo 5: Configurar e sincronizar

### Opção A — Um mapeamento por vez

1. Clique em **"Adicionar"** para criar um mapeamento:
   - **Nome**: Dê um nome (ex: "Meus Documentos")
   - **Pasta ou arquivo local**: Caminho da pasta/arquivo no seu PC
     (ex: `C:\Users\Marlon\Documentos` ou `C:\Users\Marlon\foto.jpg`)
   - **Pasta remota**: Onde salvar no Terabox (ex: `/backup/documentos`)
   - **Incluir subpastas**: Marque se quiser incluir subpastas
   - **Criptografar**: Marque se quiser criptografar (opcional)
2. Clique em **"Adicionar"**

### Opção B — Colar uma lista (CSV)

1. No card **"Importar lista (CSV)"**, cole uma linha por item:
   ```
   C:\Users\Marlon\Documentos; /Backup/Documentos
   C:\Users\Marlon\Fotos; /Backup/Fotos
   C:\Users\Marlon\arquivo.pdf; /Backup/Arquivos
   C:\Saves\Meu Mundo; /Backup/Saves; pasta
   C:\Saves\Meu Mundo\level.dat; /Backup/Saves; arquivo
   ```
   A origem pode ainda não existir. Nesse caso, use o terceiro campo opcional
   `pasta` ou `arquivo`; sem ele, o app assume pasta. Pastas são criadas na
   importação e arquivos únicos criam somente a pasta-pai.
2. Clique em **"Validar e importar lista"**
3. O app mostra quantos serão criados, quantos já existem e os erros por linha
4. Confirme para criar os mapeamentos

### Sincronizar com prévia

1. Clique em **"Prévia do Sync"**
2. Revise a lista: ⬆️ novos, ♻️ substituições, ⏭️ ignorados, ⚠️ erros
3. Se estiver tudo certo, confirme para executar
4. Acompanhe o progresso na aba **"Status"**

### Escolher quais mapeamentos entram no backup

Na lista **"Mapeamentos Existentes"**, cada mapeamento tem o checkbox
**Sincronizar**:

- **Marcado** = entra no backup manual, na prévia e no Auto-sync.
- **Desmarcado** = não é enviado. O cartão fica esmaecido e mostra
  "NÃO será sincronizado".
- Use **Selecionar todos** / **Desmarcar todos** para mudar tudo de uma vez.
- Desmarcar **não apaga** o que já está no Terabox; só para de enviar novos
  arquivos daquele mapeamento.
- O contador acima da lista mostra quantos estão selecionados.

> O app mantém **um único arquivo por caminho**. Se o conteúdo mudou, ele
> substitui o arquivo no mesmo lugar; não cria pastas/arquivos com data.
> Emojis são removidos apenas do caminho remoto (o Restaurar devolve o nome
> original).

### Restaurar arquivos (árvore por pastas)

Na aba **"Restaurar"**, depois de clicar em **"Carregar Manifesto"**:

1. A lista abre **recolhida**, agrupada por mapeamento (ex.: `saves`,
   `schematics`, `files`). Clique na seta ou no nome da pasta para abrir.
2. Cada mapeamento mostra o **destino original** logo abaixo do nome, por
   exemplo `📁 Pasta: C:\Users\marlo\AppData\Roaming\Mindustry\saves`.
3. **Todos os arquivos já vêm marcados por padrão.** Desmarque apenas o que não
   quiser restaurar.
4. O checkbox de uma pasta seleciona ou desmarca todos os arquivos dentro dela.
   Ele fica **indeterminado** quando só parte dos arquivos está marcada.
5. Use os botões **Selecionar todos**, **Desmarcar todos**, **Inverter**,
   **Expandir tudo** e **Recolher tudo** para acelerar.
6. A seleção fica salva no navegador: ao recarregar o manifesto, trocar de aba,
   recarregar a página ou reiniciar o app, a mesma escolha continua.
7. Arquivos de mapeamentos desmarcados no backup aparecem com o aviso
   **"⚠️ backup desativado"**, mas ainda podem ser restaurados manualmente.

### Para onde cada arquivo volta

O app **não pede mais uma pasta de destino**. Ele usa o caminho original do
mapeamento que está na aba Configuração:

```text
Mapeamento de pasta:
C:\Users\marlo\AppData\Roaming\Mindustry\saves
+ 0.msav
→ C:\Users\marlo\AppData\Roaming\Mindustry\saves\0.msav

Mapeamento de arquivo único:
C:\Users\marlo\AppData\Roaming\Ditto\Ditto.db
→ C:\Users\marlo\AppData\Roaming\Ditto\Ditto.db
```

- Pastas existentes são **mescladas**; nada que não foi selecionado é apagado.
- Arquivos que já existem no mesmo caminho são **substituídos**.
- Antes de baixar, o app mostra quantos arquivos serão criados, substituídos ou
  ignorados por erro.
- Se o destino tiver uma pasta onde deveria haver um arquivo, o app **não
  apaga** a pasta: mostra um erro e continua com os demais.
- Se o mapeamento não existir mais, o arquivo não é restaurado. Recrie o
  mapeamento na aba Configuração com o mesmo caminho remoto ou importe a
  configuração remota descrita abaixo.

### Migrar para outro PC (configuração remota)

O app salva um arquivo de configuração no Terabox para que um PC novo saiba
quais mapeamentos existiam e onde cada pasta ficava. O arquivo padrão é:

```text
/config-terabox-auto-backup/terabox-auto-backup.json
```

Ele guarda o `uid`, o caminho remoto, o tipo (pasta/arquivo) e o caminho local
de **cada computador**. Cada PC altera apenas a sua própria entrada; o caminho
do outro é preservado. O arquivo **não** guarda cookies, tokens, senhas nem a
chave de criptografia.

Também é criado o atalho fixo na raiz:

```text
/_terabox_autobackup_config.json
```

Ele aponta para o caminho efetivo, então você pode mudar a pasta ou o nome do
arquivo nas Configurações sem perder a descoberta em outros PCs.

No PC novo:

1. Instale o app e conecte ao Terabox.
2. Se o arquivo for encontrado, aparece o banner
   **📦 Configuração encontrada no Terabox**.
3. Clique em **Revisar importação**.
4. Confira cada linha:
   - **novo**: será criado neste PC;
   - **já existe**: já há um mapeamento equivalente;
   - **conflito**: corrija manualmente antes de importar.
5. Ajuste o caminho local de cada linha. Use o **rebase de prefixo** para
   trocar, por exemplo, `C:\Users\Marlon` por `D:\Backup` em lote.
6. Marque o que deseja importar e confirme. **Nada é importado
   automaticamente.**
7. Depois use **Restaurar** para baixar os arquivos nas pastas escolhidas.

Observações:

- O caminho sugerido vem da outra máquina. Se você usar a mesma estrutura de
  pastas, pode manter; senão, troque pelo caminho deste PC.
- Mapeamento de **arquivo único** pode apontar para um arquivo que ainda não
  existe. Basta que a pasta pai exista (ou o app a criará na restauração).
  Exemplo: `D:\Documentos\contrato.pdf`.
- Se o arquivo remoto estiver inválido ou tiver uma lista vazia, o app não
  sobrescreve sem confirmação.
- Em **Configurações → Configuração no Terabox** você pode desativar o
  salvamento remoto, mudar o caminho e usar **Salvar agora**.

### Perguntar antes de sobrescrever

Na aba **Configurações → Restauração** existe a opção:

```text
[x] Perguntar antes de sobrescrever arquivos existentes
```

- **Ligada (padrão):** antes de substituir, o app mostra a quantidade e alguns
  caminhos e pede confirmação.
- **Desligada:** a substituição acontece direto. O relatório final ainda mostra
  quantos e quais arquivos foram substituídos.

> Restaurar altera os arquivos locais. Se você restaurar uma versão antiga, o
> próximo sync pode enviar essa versão de volta ao Terabox. O app atualiza o
> cache local após o restore para evitar reenvios desnecessários de conteúdo
> idêntico.
>
> Para testar em um PC novo, comece com poucos arquivos e confira os caminhos
> mostrados na árvore antes de confirmar.

---

## Dúvidas frequentes

**P: Os cookies expiram?**
R: O cookie `ndus` dura cerca de 1 ano. Os outros expiram mais rápido. Se a conexão falhar, repita o processo.

**P: Posso usar em outro PC?**
R: Sim. Conecte ao Terabox no PC novo e use o banner
**"Configuração encontrada no Terabox" → Revisar importação**. O app lê o
arquivo remoto, mostra os mapeamentos e permite escolher o caminho local de
cada um antes de importar. Depois use **"Restaurar"**. Cada arquivo do
manifesto é casado pelo `uid`, pelo caminho remoto e pelo nome do mapeamento;
se não conseguir, mostra "mapeamento não encontrado" em vez de gravar no lugar
errado.

**P: A sincronização é automática?**
R: Sim, se ativada nas Configurações. O app monitora as pastas e sincroniza automaticamente.

**P: Como parar a sincronização?**
R: Clique em **"Parar"** na aba Configuração, ou feche o app.

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| "Cookie ndus não encontrado" | Certifique-se de copiar o cookie `ndus` corretamente |
| "Não foi possível obter jsToken" | Verifique se está logado no Terabox no navegador |
| "Arquivos não aparecem no Terabox" | Limpe o cache do navegador (Ctrl+Shift+Delete) |
| "Conexão recusada" | Verifique se o app está rodando (python app.py) |

---

*Terabox Auto-Backuper — Guia de uso manual*