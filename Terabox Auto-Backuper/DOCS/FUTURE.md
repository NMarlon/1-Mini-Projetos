# Tarefas Futuras, Bugs e Ideias — Terabox Auto-Backuper

> Arquivo de apoio para saber como continuar. Itens não implementados imediatamente.

## Bugs Conhecidos

- **Pastas vazias no restore**: o manifesto guarda `directories`, mas o
  Restaurar ainda cria apenas as pastas necessárias para os arquivos
  selecionados. Pastas vazias não são recriadas.
- **Nome remoto sanitizado**: arquivos/pastas com emoji recebem um hash no
  caminho do Terabox (ex.: `Inbox_a19902`). O Restaurar usa o manifesto e
  devolve o nome original; navegar direto no Terabox mostra o nome sanitizado.
- **Exclusão local não remove remoto**: por segurança, o backup é
  unidirecional e não apaga o arquivo remoto quando o local some.
- **Upload sequencial**: os uploads são feitos um por vez (a configuração de
  concorrência limita chunks, mas não arquivos simultâneos).
- **Fernet carrega o arquivo inteiro em memória**: arquivos muito grandes com
  criptografia ativa podem consumir RAM; o formato atual (Fernet) não é
  streaming. Para arquivos > 2GB, considerar desativar criptografia ou evoluir
  para AES-GCM em blocos.
- **Seleção de restauração é local ao navegador**: fica no `localStorage` do
  perfil e não viaja para outro PC. Para levar a seleção junto com o manifesto,
  seria preciso salvar no banco e incluir um campo `selected` no manifesto.
- **Manifesto vazio ao desmarcar tudo**: se todos os mapeamentos forem
  desmarcados, o próximo sync grava um manifesto vazio. Os arquivos continuam
  no Terabox, mas o Restaurar deixa de listá-los até um mapeamento ser
  reativado e sincronizado.
- **Colisão de nomes sanitizados**: nomes que só diferem por ponto inicial
  podem cair no mesmo caminho remoto. Exemplo real: `.kkrieger.md` e
  `kkrieger.md` viram `.../kkrieger.md`, porque a sanitização remove o ponto
  inicial. O planejador detecta o caminho duplicado e ignora o segundo; o
  manifesto reconstruído prefere o nome natural. Corrigir na raiz exigiria
  anexar hash a nomes que perdem o ponto inicial, mas isso mudaria caminhos já
  enviados (ex.: `.obsidian` → `obsidian`).
- **Arquivo antigo ao mudar o caminho da configuração**: ao trocar
  `remote_config_path`, o app cria o novo arquivo e atualiza o atalho, mas não
  apaga o antigo automaticamente. A limpeza manual evita apagar por engano um
  arquivo que outro PC ainda esteja usando.
- **Merge remoto sem transação entre PCs**: se dois computadores salvarem a
  configuração exatamente ao mesmo tempo, o último upload pode perder a
  alteração do outro. O app baixa e mescla antes de gravar, mas o Terabox não
  oferece uma escrita condicional/transacional. Para uso single-user é
  suficiente; uma evolução possível é detectar o hash remoto imediatamente
  antes do upload e mesclar novamente em caso de mudança.

## Ideias de Implementação Futura

### Alta Prioridade
- **Executável standalone**: Empacotar com PyInstaller para não exigir Python instalado
- **Task Scheduler**: Rodar mesmo sem login do usuário (mais robusto que HKCU\Run)
- **Dashboard de status**: Gráficos de uso, velocidade de upload, histórico visual

### Média Prioridade
- **Sync bidirecional**: Propagar mudanças do Terabox para local (mais complexo)
- **Múltiplos perfis de navegador**: Permitir escolher qual browser usar para auth
- **Proxy support**: Para contornar bloqueios regionais
- **Compressão**: Comprimir arquivos antes do upload para economizar espaço
- **Deduplicação global**: Detectar arquivos duplicados entre mapeamentos

### Baixa Prioridade
- **Mobile companion**: App mobile para verificar status
- **WebDAV**: Expor Terabox como drive WebDAV (como terabox-webdav-worker)
- **Integração com outros clouds**: Google Drive, OneDrive, etc.
- **AI assistant**: Sugestões de organização de arquivos

## Melhorias Técnicas

- **Cache de listagem remota**: Evitar fetch completo a cada sync (usar ETag/last-modified)
- **Streaming upload**: Upload direto sem salvar em disco (para arquivos grandes)
- **Paralelismo de chunks**: Upload de múltiplos chunks simultaneamente
- **Verificação de integridade**: Verificar MD5 remoto após upload
- **Log rotation**: Rotacionar logs para não crescer indefinidamente

## Notas de Compatibilidade

- **rookie-cookies** requer Python ≥ 3.11 (temos 3.14 ✅)
- **Chrome App-Bound Encryption** pode ser bloqueado por antivírus (documentar)
- **jsToken** expira ~5 min, mas é re-mintado automaticamente
- **ndus cookie** vive ~1 ano, depois precisa re-login no navegador