# samples/ — amostras de voz (versionado)

Amostras curtas, com texto **sintético** (sem conteúdo do curso), para comparar
vozes e validar pronúncia antes do build completo.

Arquivos esperados:

- `francisca.mp3` — voz principal (`pt-BR-FranciscaNeural`);
- `antonio.mp3` — comparação masculina;
- `thalita.mp3` — comparação multilíngue;
- `pronunciation-test.mp3` — números, siglas, datas e termos em inglês.

Essas amostras são geradas por `python -m pdf_tts samples` e podem ser
commitadas (são pequenas e não contêm material protegido).
