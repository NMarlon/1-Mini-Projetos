# manifests/ — registro dos builds (versionado)

Cada arquivo `<slug>.json` descreve o que foi gerado para um projeto:

- voz, motor e ritmo usados;
- SHA-256 do PDF de origem;
- páginas e títulos das semanas;
- duração de cada aula;
- quantidade de chunks;
- caminhos dos MP3/M4B/SRT;
- hashes dos arquivos de áudio.

**Não contém o texto do curso.** É seguro versionar.

## Regra

Atualize o manifest ao final de cada build (mesmo parcial). Se o áudio for
apagado, o manifest continua sendo a referência do que existia e do comando
necessário para regenerar.

Formato completo em `DOCS/04-AUDIO-PIPELINE.md`.
