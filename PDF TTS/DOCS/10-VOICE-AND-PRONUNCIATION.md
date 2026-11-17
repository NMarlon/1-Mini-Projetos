# 10 — Voz e pronúncia

## Voz escolhida

| Item | Valor |
|---|---|
| Motor | Edge TTS (`edge-tts`) |
| Voz | `pt-BR-FranciscaNeural` |
| Gênero | Feminino |
| Idioma | Português brasileiro |
| Rate | `-5%` |
| Volume | `+0%` |
| Pitch | `+0Hz` |
| Sample rate | 24 kHz |
| MP3 | 64 kbps mono |

## Vozes disponíveis no Edge (pt-BR)

| Voz | Gênero | Observação |
|---|---|---|
| `pt-BR-FranciscaNeural` | F | **Padrão**; MOS 4,44; ~3,3x tempo real |
| `pt-BR-AntonioNeural` | M | Mais formal/grave; ~5,8x tempo real |
| `pt-BR-ThalitaMultilingualNeural` | F | Multilíngue; melhor para inglês; ~1,5x |
| `pt-BR-ThalitaNeural` | F | Não listada, mas sintetiza; evitar como padrão |

> A lista do `edge-tts --list-voices` mostra 3 vozes. `pt-BR-ThalitaNeural`
> funciona, mas não é oficialmente listada; trate como “não suportada”.

## Como gerar amostras

```powershell
python -m pdf_tts samples
```

Saída:

- `samples/francisca.mp3`
- `samples/antonio.mp3`
- `samples/thalita.mp3`
- `samples/pronunciation-test.mp3`

O texto é sintético (não é conteúdo do curso) e inclui números, siglas, datas,
`S01`, `MKT 120`, termos em inglês e lacunas.

Amostras geradas em 2026-11-17:

| Arquivo | Voz | Duração |
|---|---|---|
| `samples/francisca.mp3` | `pt-BR-FranciscaNeural` | 28,2 s |
| `samples/antonio.mp3` | `pt-BR-AntonioNeural` | 31,7 s |
| `samples/thalita.mp3` | `pt-BR-ThalitaMultilingualNeural` | 28,6 s |
| `samples/pronunciation-test.mp3` | `pt-BR-FranciscaNeural` | 36,7 s |

## Como trocar de voz

```powershell
python -m pdf_tts build --project mkt120 --lesson S01 `
  --voice pt-BR-AntonioNeural --rate -5%
```

- O cache é separado por voz/rate.
- O manifest registra a mudança.
- Re-renderizar 11 h com Thalita pode levar ~9 h; com Antonio, ~2–3 h.
- **Nunca** misture vozes no mesmo livro sem pedir.

## Léxico de pronúncia

Arquivo: `config/pronunciation.pt-BR.yaml`.

### Como funciona

1. As substituições são aplicadas antes da conversão de números.
2. São regex Python, case-insensitive por padrão.
3. A ordem importa; padrões mais específicos primeiro.
4. Use `\b` para não substituir dentro de palavras.

### Exemplos atuais

| Texto | Fala |
|---|---|
| `S01` | `Semana 1` |
| `MKT 120` | `M K T, cento e vinte` |
| `COM 150` | `C O M, cento e cinquenta` |
| `SWOT` | `S U O T` |
| `CRM` | `C R M` |
| `WhatsApp` | `Uátis Ápi` |
| `Canvas` | `Cânvas` |
| `OpenStax` | `Open Stax` |
| `________` | `lacuna` |
| `R$ 12,50` | `doze reais e cinquenta centavos` |
| `15%` | `quinze por cento` |
| `2026` | `dois mil e vinte e seis` |

### Como adicionar uma correção

1. Identifique a palavra/frase e como ela deve soar.
2. Adicione uma entrada em `replacements`.
3. Regenere o texto falado:
   ```powershell
   python -m pdf_tts segment --project mkt120
   ```
4. Gere uma aula curta para testar:
   ```powershell
   python -m pdf_tts build --project mkt120 --lesson S01 --force
   ```
5. Ouça o trecho e ajuste.
6. Registre a mudança em `09-DECISIONS.md` se for relevante.

### Cuidados

- **Não** substitua palavras comuns por engano (`\b` ajuda).
- **Não** use replacements que criem números (`dez` → `10`) antes da conversão.
- Evite soletrar palavras comuns; o TTS já pronuncia bem.
- Para nomes próprios, teste com uma frase curta.
- Para siglas, soletrar com espaços costuma ser mais claro.
- Termos em inglês: só adicione se a pronúncia padrão estiver ruim.

## Números e datas

A normalização cobre:

- inteiros (`12` → `doze`);
- anos (`2026` → `dois mil e vinte e seis`);
- decimais (`3,5` → `três vírgula cinco`);
- moeda (`R$ 12,50`);
- porcentagem (`15%`);
- ordinais (`1º`, `2ª`);
- datas (`17/11/2026`);
- horas (`9h30`);
- intervalos (`10-20` → `dez a vinte`).

Se algum caso falhar, adicione um teste em `tests/test_normalize.py` e corrija a
regra.

## Listas, exercícios e quizzes

- Marcadores de lista (`1.`, `2.`, `•`) são removidos; a pausa entre chunks
  marca a separação.
- Sublinhados (`________`) viram **“lacuna”**.
- Opções de múltipla escolha começam com **“Opção:”**.
- Listas de respostas bagunçadas são lidas como opções; não tentamos adivinhar
  a correta.

## Checklist de escuta

Ao validar uma amostra/aula, verifique:

- [ ] Nomes próprios (Joseph, Palácio das Bicicletas, OpenStax).
- [ ] Siglas (SWOT, CRM, MKT, COM).
- [ ] Números, anos, dinheiro, porcentagem.
- [ ] Termos em inglês (Task, Purpose, WhatsApp, Canvas).
- [ ] Perguntas têm entonação de pergunta?
- [ ] O ritmo é confortável para estudar?
- [ ] Há cortes/joins estranhos entre parágrafos?
- [ ] O volume está consistente?

Se algo estiver ruim, anote em `08-ERRORS-AND-LESSONS.md` com a página e o
trecho, e ajuste o léxico ou a regra.
