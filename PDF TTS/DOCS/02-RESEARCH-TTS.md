# 02 — Pesquisa de TTS (2026)

Pesquisa feita em novembro de 2026. O objetivo era responder:

> Qual é o método gratuito que produz o áudio mais natural em português
> brasileiro, com o menor esforço de setup, para ~600 mil caracteres?

## Resumo da decisão

**Edge TTS** com a voz **`pt-BR-FranciscaNeural`** e ritmo **-5%**.

Motivos:

1. Qualidade natural alta para pt-BR (MOS 4,44 em estudo da Microsoft).
2. Custo zero e **sem cadastro/API key**.
3. Já validado nesta máquina: 24 s de áudio em 4–7 s.
4. Fácil de cachear, retomar e dividir em capítulos.
5. Não exige GPU; usa CPU apenas para orquestração.

Alternativas melhores em qualidade existem, mas exigem conta/billing (Google
Chirp 3 HD, Azure DragonHD) ou são locais e não comerciais (Phonon 40m PT).

## Comparativo

| Motor | Tipo | Qualidade pt-BR | Custo | Setup | Licença | Veredito |
|---|---|---|---|---|---|---|
| **Edge TTS** | Nuvem (não oficial) | **Francisca MOS 4,44**; prosódia natural | Grátis, sem chave | `pip install edge-tts` | Lib LGPL-3.0; serviço não oficial | **Principal** |
| Google Chirp 3 HD | Nuvem | Muito natural, geração HD | **1M chars/mês grátis**; US$ 30/M depois | Conta Google Cloud + billing | Proprietário | Opcional premium |
| Azure DragonHD | Nuvem | Topo de linha (`pt-BR-Thalita:DragonHDLatestNeural`) | Camada gratuita limitada + conta | Conta Azure + key | Proprietário | Opcional premium |
| **Phonon 40m PT** | Local CPU | **Elo 2.144**; WER 2,9% (hard set) | Grátis para uso pessoal | `pip install ptts`; modelo com gate no HF | **CC BY-NC 4.0** | Melhor fallback offline |
| Pocket TTS | Local CPU | Boa; 1 voz pt-BR (Rafael); MOS 4,10 (inglês) | Grátis | `pip install pocket-tts` | **MIT** | Fallback offline simples |
| Kokoro 82M | Local CPU | **Fraco em pt-BR**: Elo 1.633; MOS 5,6 | Grátis | `kokoro` + espeak-ng | Apache 2.0 | Não recomendado p/ pt-BR |
| Piper | Local CPU | Robótico; `pt_BR-faber-medium` | Grátis | `piper-tts` + voz | GPL-3.0 + voz | Emergência |
| ElevenLabs | Nuvem | Excelente | 10 mil chars/mês grátis | Conta | Proprietário | Inviável (600k chars) |
| XTTS v2 | Local GPU | Boa/clonagem | Grátis | Pesado, GPU | CPML (não comercial) | Não usar |

## Evidências

### Edge TTS

- 322 vozes no catálogo (consulta em 25/10/2026); 3 vozes pt-BR listadas:
  `pt-BR-AntonioNeural`, `pt-BR-FranciscaNeural`,
  `pt-BR-ThalitaMultilingualNeural`.
- `pt-BR-ThalitaNeural` (não multilíngue) também sintetizou, apesar de não
  aparecer na listagem. Tratar como voz “não listada”; não usar como padrão.
- Estudo da Microsoft (2020) com 60 falantes nativos: Francisca neutra **4,44**
  e alegre **4,38** em escala Likert de 1–5.
- Ritmo medido: ~134 palavras/min (Azure); com `-5%`, ~149 palavras/min no
  nosso teste (depende do texto).
- Saída: MP3 24 kHz mono 48 kbps; o pipeline reencoda para 64 kbps.
- Latência medida nesta máquina (texto de 374 chars, `-5%`):
  - Francisca: 24,2 s de áudio em 7,3 s (≈3,3x tempo real);
  - Antonio: 25,0 s em 4,3 s (≈5,8x);
  - Thalita: 23,6 s em 15,5 s (≈1,5x).
- Problema conhecido: falhas intermitentes `NoAudioReceived`/WebSocket 1006.
  Mitigação: cache por chunk, retry e concorrência baixa.
- O CLI pode criar um arquivo vazio em caso de erro; **sempre validar** com
  `ffprobe`.

Links:
- https://github.com/rany2/edge-tts
- https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts
- https://news.microsoft.com/pt-br/portugues-do-brasil-e-adicionado-aos-servicos-cognitivos-do-azure-para-texto-e-fala-neural

### Google Chirp 3 HD

- Primeiro 1M de caracteres por mês grátis; depois US$ 30/M.
- Exige conta Google Cloud com billing habilitado.
- 30 vozes em 53 locales, incluindo `pt-BR`.
- Excelente naturalidade, mas o setup não é autônomo.
- Fica no backlog como upgrade opcional.

Links:
- https://cloud.google.com/text-to-speech/pricing
- https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd

### Azure DragonHD

- `pt-BR-Thalita:DragonHDLatestNeural` e `pt-BR-Macerio:DragonHDLatestNeural`
  são as vozes HD mais recentes.
- Requer conta Azure/API key; camada gratuita mensal.
- Não está exposta no catálogo do Edge TTS.
- Fica no backlog como upgrade premium.

### Phonon 40m PT (Gradium)

- 40M parâmetros, 74,6 MB q8, CPU, 24 kHz.
- Elo 2.144 em pt-BR (171 avaliadores, 2.000 votos), à frente de Kokoro (1.633).
- WER 2,9% no hard set; 1,1% no Seed-TTS.
- Licença **CC BY-NC 4.0** (uso pessoal ok; comercial não).
- Modelo com gate no Hugging Face (aceitar termos); `pip install ptts`.
- Excelente fallback offline, mas o gate impede instalação 100% autônoma.

Links:
- https://huggingface.co/gradium/phonon-40m-pt
- https://github.com/gradium-ai/xn-ptts

### Pocket TTS (Kyutai)

- 100M parâmetros, CPU, MIT, 24 kHz.
- 1 voz pt-BR de exemplo: `rafael` (masculina).
- MOS 4,10 (inglês, UTMOS); qualidade boa, mas inferior ao Edge em pt-BR.
- `pip install pocket-tts`; sem gate.
- Bom fallback se o Edge ficar indisponível e o Phonon não puder ser usado.

Links:
- https://github.com/kyutai-labs/pocket-tts
- https://kyutai.org/blog/2026-05-04-pocket-tts-multilingual

### Kokoro 82M

- Apache 2.0, 82M, CPU.
- 3 vozes pt-BR: `pf_dora`, `pm_alex`, `pm_santa`.
- Elo 1.633 e WER 4,1% em pt-BR; as vozes pt-BR têm nota ~5,6 no catálogo,
  contra 8–9 das vozes inglesas. Treino escasso em português.
- **Não recomendado** para este projeto.

Links:
- https://huggingface.co/hexgrad/Kokoro-82M
- https://kokoroweb.app/pt/blog/kokoro-tts-portugues-brasileiro

### Piper

- Rápido, CPU, GPL-3.0; voz `pt_BR-faber-medium`.
- Qualidade claramente inferior (robótica).
- Útil apenas como emergência offline.

## Ferramentas prontas avaliadas

- **ebook2audiobook** (DrewThomasson): suporta PDF e M4B, mas o motor padrão
  (XTTS) é pesado em CPU e a qualidade em pt-BR depende do modelo. Muito
  complexo para o nosso caso.
- **epub2tts / Audiblez**: focados em EPUB e Kokoro; Kokoro é fraco em pt-BR.
- **pdf-to-audiobook** (kitten-lissy): pipeline OCR + Edge TTS + M4B; bom para
  PDFs escaneados, mas o nosso PDF tem texto.
- Conclusão: um pipeline próprio com Edge TTS dá mais controle sobre limpeza,
  divisão por semana, capítulos e retomada. As ferramentas prontas serviram de
  referência para a montagem M4B.

## Por que não usar o Google como principal agora

- Exige criar conta, habilitar billing e configurar credenciais → ação humana.
- O primeiro 1M/mês cobre o projeto, mas re-renders e testes podem estourar e
  gerar cobrança.
- O Edge TTS já entrega qualidade suficiente e começa imediatamente.

Se o usuário quiser o máximo de naturalidade depois, o caminho é:
1. Google Chirp 3 HD (1M grátis/mês) como provider opcional; ou
2. Azure DragonHD (voz HD) com conta/API key.

## Riscos do Edge TTS

- Serviço não oficial, sem SLA; pode mudar/bloquear.
- Falhas intermitentes de WebSocket.
- Texto sai da máquina (vai para a Microsoft). Não usar para conteúdo sensível.
- Pode ter limite de uso não documentado.

Mitigações já planejadas: cache por chunk, retry, concorrência baixa, validação
com `ffprobe`, build retomável e fallback local documentado (Phonon/Pocket).

## Conclusão

Para **qualidade gratuita + esforço zero + pt-BR**, o Edge TTS com Francisca é
a melhor escolha em 2026. Para qualidade máxima paga/opcional, Google Chirp 3 HD
ou Azure DragonHD. Para offline/privacidade, Phonon 40m PT (não comercial) ou
Pocket TTS (MIT).
