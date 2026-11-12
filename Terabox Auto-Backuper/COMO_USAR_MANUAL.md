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
   ```
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
2. **Todos os arquivos já vêm marcados por padrão.** Desmarque apenas o que não
   quiser restaurar.
3. O checkbox de uma pasta seleciona ou desmarca todos os arquivos dentro dela.
   Ele fica **indeterminado** quando só parte dos arquivos está marcada.
4. Use os botões **Selecionar todos**, **Desmarcar todos**, **Inverter**,
   **Expandir tudo** e **Recolher tudo** para acelerar.
5. A seleção fica salva no navegador: ao recarregar o manifesto, trocar de aba,
   recarregar a página ou reiniciar o app, a mesma escolha continua.
6. Arquivos de mapeamentos desmarcados no backup aparecem com o aviso
   **"⚠️ backup desativado"**, mas ainda podem ser restaurados manualmente.

> A seleção de restauração é local ao navegador/perfil. Ela não é enviada ao
> Terabox e não aparece em outro computador.

### Preservar estrutura de pastas

A opção **"Preservar estrutura de pastas"** já vem marcada. Ela mantém as
subpastas originais dentro da pasta de destino:

```text
5506831188076592432/games/com.mojang/minecraftpe/clientId.txt
→ C:\restore\5506831188076592432\games\com.mojang\minecraftpe\clientId.txt
```

O **nome do mapeamento** (ex.: `saves`, `files`) é usado apenas para organizar
a árvore na tela; ele não vira uma pasta no destino. Se você desmarcar essa
opção, o app avisa que os arquivos serão todos colocados diretamente na pasta
de destino, sem subpastas, e que nomes iguais podem ser sobrescritos.

> Antes de restaurar muitos arquivos, o app pede confirmação. Para testar em um
> PC novo, comece com poucos arquivos e confira a pasta de destino.

---

## Dúvidas frequentes

**P: Os cookies expiram?**
R: O cookie `ndus` dura cerca de 1 ano. Os outros expiram mais rápido. Se a conexão falhar, repita o processo.

**P: Posso usar em outro PC?**
R: Sim! Use a aba **"Restaurar"** para baixar os arquivos em outro computador.

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