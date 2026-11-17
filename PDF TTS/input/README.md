# input/ — PDFs de origem (NÃO versionados)

Por direitos autorais, os PDFs **não entram no Git**. Esta pasta existe para
que o pipeline seja reproduzível na máquina local.

## Arquivos esperados

| Arquivo | Tamanho | SHA-256 |
|---|---|---|
| `MKT 120.pdf` | 20.855.150 bytes | `EA08D740BCC68EC1317AD3CE8D1C6A5C07A706C9821F1E62C02062FDAAC242F1` |
| `Livro texto COM 150-1.pdf` | 52.079.617 bytes | `ACA653AC0049D373DF3ECCE00C24E026ECC4808FFF67F8DFD712D2BCF3C7DD42` |

## Como validar

```powershell
Get-FileHash "input\MKT 120.pdf" -Algorithm SHA256
Get-FileHash "input\Livro texto COM 150-1.pdf" -Algorithm SHA256
```

Se o hash não bater, **pare** e confirme com o usuário. Um PDF diferente pode
mudar a numeração das páginas e quebrar a estrutura das semanas.

## Onde conseguir

Os PDFs foram fornecidos pelo usuário. Este projeto não baixa, não descriptografa
e não redistribui material protegido.
