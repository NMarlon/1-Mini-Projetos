# 11 — Verificação

Checklist para considerar o projeto concluído. Rode as verificações ao final de
cada build e registre os resultados em `manifests/` ou no diário de
`06-TASKS.md`.

## 1. Ambiente

- [ ] `python -m pdf_tts doctor` retorna 0.
- [ ] Python 3.11 no `.venv`.
- [ ] `ffmpeg`/`ffprobe` com `libmp3lame` e `aac`.
- [ ] `edge-tts` importável; vozes pt-BR listadas.
- [ ] PDFs presentes e SHA-256 corretos.
- [ ] Espaço em disco > 3 GB.

## 2. Extração

- [ ] `content/mkt120/` e `content/com150/` existem.
- [ ] 7 semanas por projeto, com páginas corretas.
- [ ] `manuscript.md` legível.
- [ ] Nenhum caractere PUA (`\ue000`–`\uf8ff`) ou ligadura (`\ufb00`–`\ufb06`).
- [ ] Nenhuma URL/email no texto falado.
- [ ] Bibliografia removida; exercícios/quizzes presentes.
- [ ] `skipped.jsonl` com motivos coerentes.
- [ ] Contagem de caracteres por semana próxima de `03-PDF-PIPELINE.md`
      (variação < 15% após limpeza).

## 3. Segmentação

- [ ] `lessons/S01.json`…`S07.json` existem.
- [ ] Cada aula tem título, páginas, seções e chunks.
- [ ] Nenhum chunk vazio.
- [ ] Chunks entre 80 e 1200 caracteres (exceto títulos).
- [ ] `S01`, `MKT 120`, `COM 150` normalizados.
- [ ] Números/datas/moedas por extenso.
- [ ] Lacunas e opções tratadas.

## 4. Síntese

- [ ] Todos os chunks `done` no SQLite.
- [ ] Nenhum chunk `failed`/`invalid`.
- [ ] Nenhum MP3 com 0 bytes ou duração < 0,2 s.
- [ ] Cache reutilizado em uma segunda execução (`--resume` não re-sintetiza).
- [ ] Interromper e retomar funciona.

## 5. Arquivos finais

Para cada projeto:

- [ ] `S01.mp3`…`S07.mp3` existem.
- [ ] `S01.m4b`…`S07.m4b` existem.
- [ ] `S01.srt`…`S07.srt` existem.
- [ ] `<SLUG>-completo.mp3` e `.m4b` existem.
- [ ] `cover.jpg` existe.
- [ ] `manifest.json` existe e está atualizado.
- [ ] `README.md` com tracklist existe (opcional).

## 6. Áudio

- [ ] Codec/sample rate/canais corretos (`ffprobe`).
- [ ] Duração de cada aula > 90% da estimativa.
- [ ] Loudness ~-16 LUFS (±1) em uma amostra de cada aula.
- [ ] Sem silêncios longos inesperados (> 5 s) entre seções.
- [ ] Sem cortes no meio de palavras perceptíveis.
- [ ] Volume consistente entre aulas.

## 7. Capítulos (M4B)

- [ ] `ffprobe -show_chapters` lista os capítulos.
- [ ] Capítulos em ordem crescente.
- [ ] Primeiro começa em 0.
- [ ] Último termina <= duração.
- [ ] Títulos legíveis (`Semana 1 — …`, `S01 …`).
- [ ] Capa embutida (`attached_pic`).

## 8. SRT

- [ ] Primeira cue começa em 00:00:00,000 (ou perto).
- [ ] Última cue <= duração do áudio.
- [ ] Sem cues sobrepostas.
- [ ] Texto legível e sem marcações estranhas.
- [ ] Número de cues == número de chunks (ou menos, se algum foi omitido).

## 9. Conteúdo

- [ ] Início de cada semana corresponde ao título correto.
- [ ] Nenhum trecho grande faltando (comparar `manuscript.md`).
- [ ] Exercícios/quizzes presentes.
- [ ] Tarefas/estudos de caso presentes.
- [ ] Bibliografia ausente.
- [ ] Nenhum cabeçalho/rodapé/número de página falado.
- [ ] Nenhuma URL soletrada.

## 9.1 App Pathway PDF TTS

- [ ] Opções de modo visíveis antes do upload.
- [ ] Perfil Pathway encontra Semanas/S01–S07 no MKT 120 e COM 150.
- [ ] PDF fora do Pathway funciona no perfil Genérico ou cai para blocos com aviso.
- [ ] “Tudo útil” remove cabeçalho/página/link; “Tudo literal” mantém.
- [ ] Upload de PDF grande mostra progresso e não estoura a memória.
- [ ] Fechar a janelinha mostra confirmação; reabrir o `.exe` usa a instância existente.
- [ ] Queda do servidor mostra “O programa não está respondendo”, não “Failed to fetch”.
- [ ] `logs/app.log` registra upload, análise e jobs.
- [ ] Nenhuma janela de CMD aparece durante a montagem (`run_hidden`).
- [ ] O ZIP principal extraído abre e responde em `/api/health`.
- [ ] A versão principal passa no Smart App Control; a PyInstaller é a alternativa.

## 9.2 Tutorial de download

- [ ] `DOCS/13-COMO-BAIXAR-O-PDF.md` abre com as quatro imagens na ordem.
- [ ] `DOCS/13-COMO-BAIXAR-O-PDF.pdf` tem 6 páginas e está legível.
- [ ] O texto menciona o app e o aviso de uso pessoal.
- [ ] `python scripts/build_download_tutorial.py` regenera o PDF.

## 10. Git

- [ ] `git status` limpo (exceto arquivos ignorados).
- [ ] Nenhum PDF em `git ls-files`.
- [ ] Nenhum arquivo em `content/` ou `output/` versionado.
- [ ] `manifests/` versionados.
- [ ] `samples/` versionadas (se geradas).
- [ ] Commits por tarefa.
- [ ] Nenhum push não autorizado.

## Comandos úteis

```powershell
# Duração de todos os MP3
Get-ChildItem "output\MKT-120\*.mp3" | ForEach-Object {
  $d = & ffprobe -v error -show_entries format=duration -of csv=p=0 $_.FullName
  "{0}: {1:N1}s" -f $_.Name, [double]$d
}

# Capítulos de um M4B
ffprobe -v error -show_chapters -of json "output\MKT-120\S01.m4b"

# Loudness de uma aula
ffmpeg -hide_banner -i "output\MKT-120\S01.mp3" -af loudnorm=print_format=json -f null - 2>&1 | Select-String "input_i|input_tp|input_lra"

# Procurar PUA/ligaduras no conteúdo
Select-String -Path "content\mkt120\*.jsonl" -Pattern "[\ue000-\uf8ff\ufb00-\ufb06]"

# App: servidor e defaults
Invoke-RestMethod "http://127.0.0.1:8765/api/health"
Invoke-RestMethod "http://127.0.0.1:8765/api/defaults"

# App: capítulos de um PDF (Pathway primeiro)
python -m pdf_tts detect "input\Livro texto COM 150-1.pdf" --profile pathway

# Testes e lint
.\.venv\Scripts\python.exe -m ruff check src tests packaging
.\.venv\Scripts\python.exe -m pytest -q
```

## Critério de aceite final

O projeto está pronto quando:

1. Todos os itens acima estão marcados.
2. Os dois livros têm 7 aulas + completo, em MP3/M4B/SRT.
3. O usuário consegue ouvir sem falhas graves.
4. A documentação permite que outra IA reproduza o build.
5. Não há PDFs/texto/áudio no Git.

## Critério de aceite do app

- [ ] App principal abre e responde em `/api/health`.
- [ ] COM 150 e MKT 120 são detectados como Abertura + Semanas 1–7.
- [ ] PDF fora do Pathway funciona no perfil genérico ou cai para blocos com aviso.
- [ ] “Tudo útil” e “Tudo literal” se comportam como documentado.
- [ ] Nenhuma janela de CMD aparece durante a montagem.
- [ ] ZIP principal extraído abre em máquina com Smart App Control.

## Registro

| Data | Projeto | Resultado | Observações |
|---|---|---|---|
| 2026-11-17 | MKT-120 S01 | OK técnico | 23:05; 11 capítulos; 163 cues; -16,46 LUFS; TP -1,46; MP3 11,1 MB; M4B 11,2 MB; capa 1081x1400. |
| 2026-11-17 | MKT-120 completo | **OK** | 7 aulas + livro 3:39:26; 1.473 cues; 68 capítulos; loudness -16,45/-16,46 LUFS; TP ≤ -0,94; nenhum silêncio >5 s. |
| 2026-11-17 | COM-150 completo | **OK** | 7 aulas + livro 7:50:42; 3.457 cues; 92 capítulos; loudness -16,45 LUFS; TP ≤ -0,79; nenhum silêncio >5 s. |
| 2026-11-18 | Pathway PDF TTS | **OK** | 59 testes; ruff limpo; COM 150 Pathway em ~20 s / 8 capítulos; MKT 120 Pathway / 8 capítulos; job `raw` com 15 arquivos; ZIP principal extraído e executado; `run_hidden` sem novos cmd/conhost. |
| 2026-11-18 | App — Smart App Control | **OK na versão principal** | PyInstaller bloqueado por política de aplicativo nesta máquina; versão com `pythonw.exe` assinado pela PSF abriu e passou no health check. |
