# API do Terabox — Referência

> Base URL: `https://www.terabox.com`
> Autenticação: cookies (ndus obrigatório) + jsToken (scraped do HTML /main)

## Endpoints Utilizados

### GET /main
Página principal. Usada para raspar jsToken.
- **Headers**: Cookie (com ndus, etc.)
- **Response**: HTML contendo jsToken

### GET /api/list
Lista arquivos de um diretório.
- **Params**: `app_id=250528`, `web=1`, `channel=dubox`, `clienttype=5`, `jsToken=...`, `dir=/path`, `num=1000`, `page=1`, `order=time`, `desc=1`, `showempty=0`
- **Response**: `{ "errno": 0, "list": [{ "server_filename", "path", "size", "isdir", "md5", "server_mtime", ... }] }`
- **Erros**: errno -7/-9 (dir/arquivo não existe), errno -6 (cookies inválidos)
- **Paginação obrigatória**: repetir com `page=2,3...` até vir menos de `num`
  itens. O código antigo lia só a página 1 e "esquecia" arquivos em pastas
  com mais de 1000 itens.

### POST /api/precreate
Pré-cria arquivo para upload.
- **Body (form)**: `app_id`, `web`, `channel`, `clienttype`, `jsToken`, `path`, `autoinit=1`, `target_path`, `block_list` (JSON array de MD5s)
- **Response**: `{ "uploadid": "..." }` ou `{ "errmsg": "need verify" }`

### POST /rest/2.0/pcs/superfile2
Upload de arquivo/chunk (via curl).
- **URL**: `https://c-jp.terabox.com:443/rest/2.0/pcs/superfile2?method=upload&type=tmpfile&app_id=250528&path=...&uploadid=...&partseq=N`
- **Method**: POST multipart/form-data
- **Body**: file=@local_path
- **Response**: `{ "md5": "..." }` (sem error_code = sucesso)

### POST /api/create
Cria pasta ou finaliza criação de arquivo.
- **Params**: `isdir=0|1`, `rtype`, `app_id=250528`, `jsToken=...`
- **Body (form)**: `path`, `uploadid`, `target_path`, `size`, `block_list`
- **Response**: `{ "errno": 0 }` (sucesso)

#### Semântica do `rtype` (importante)

| `rtype` | Comportamento | Uso no app |
|---|---|---|
| `0` | Não renomeia; falha/ignora se já existe | **Pastas** e arquivo novo |
| `1` | Renomeia em qualquer conflito | ❌ Nunca usar |
| `2` | Renomeia se conflito e block list diferente | Não usado |
| `3` | Sobrescreve | **Substituir arquivo alterado** |

`rtype=1` era a causa das pastas `Marlon Desktop_20261109_190922`: cada arquivo
chamava "criar pasta" e o Terabox renomeava a pasta existente.

### GET /api/filemetas
Obtém metadados e link de download de um arquivo.
- **Params**: `app_id=250528`, `jsToken=...`, `target=["/path/arquivo"]`, `dlink=1`
- **Response**: `{ "errno": 0, "info": [{ "dlink": "...", "size": ..., "md5": "..." }] }`
- É o endpoint usado pelo Restaurar. O `/api/download` com `fidlist` retornava
  `errno=2` para conta própria.

### GET /rest/2.0/pcs/file (fallback de download)
- **Params**: `method=download`, `app_id=250528`, `path=/arquivo`, `jsToken=...`
- Responde `302` com `Location` = dlink. Usado como fallback do `/api/filemetas`.

### GET /api/quota
Verifica quota disponível.
- **Params**: `checkfree=1`
- **Response**: `{ "total": ..., "used": ... }`

### GET /rest/2.0/membership/proxy/user
Verifica se é VIP.
- **Params**: `method=query`
- **Response**: `{ "data": { "member_info": { "is_vip": 0|1 } } }`

### GET /api/download (para processo reverso)
Obtém link de download de um arquivo.
- (endpoint a ser pesquisado durante implementação de T12)

## Arquivos de Configuração e Atalho

O cadastro remoto usa os mesmos endpoints de listagem, upload e download:

- `GET /api/list` no diretório pai para descobrir/verificar o arquivo;
- `POST /api/precreate` + upload via curl + `POST /api/create` com `rtype=3`
  para gravar o JSON;
- `GET /api/filemetas` para baixar e validar o conteúdo.

Caminho padrão:
`/config-terabox-auto-backup/terabox-auto-backup.json`.

Atalho fixo na raiz:
`/_terabox_autobackup_config.json` (JSON pequeno com `config_path`).

Se o caminho configurado for uma pasta, o app **não** tenta substituí-la.
Se o arquivo já existir, o fluxo de `precreate` pode indicar conflito; nesse
caso o app remove apenas aquele arquivo de configuração e recria.

## Notas Importantes

1. **jsToken** expira em ~5 minutos. O app renova antes (240s) e em erro de
   autenticação (-6, 4000023, 400141, 450016).
2. **ndus cookie** é httpOnly — não acessível via JS. Usar rookie-cookies.
3. **Upload via curl**: mais confiável que requests para multipart grande.
4. **Chunking**: arquivos ≥ 2GB divididos em chunks de 120MB.
5. **Limite de tamanho**: 4GB (free) / 20GB (VIP).
6. **Rate limiting**: mínimo 400ms entre chamadas (recomendado).
7. **Regional mirrors**: alguns accounts usam dm.terabox.com ou dm.1024terabox.com. Detectar via erro -6.
8. **Emojis em nomes**: o Terabox rejeita `📥`, `📚`, etc. em pastas
   (`errno=-7 param path file name is invalid`). O app sanitiza o caminho
   remoto (hash curto) e mantém o nome original no manifesto.
9. **Acentos e `;` funcionam**: `Ação`, `Realidade; Verdade` são aceitos.
10. **Caminhos POSIX**: `target_path` e `path` devem usar `/`, nunca `\`.
11. **`precreate` sem uploadid**: pode significar "arquivo já existe"; o app
    confere tamanho/MD5 e trata como skip se for o mesmo conteúdo.