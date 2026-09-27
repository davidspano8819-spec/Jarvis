# J.A.R.V.I.S.

*Just A Rather Very Intelligent System* — assistente personale in italiano, con
personalità da maggiordomo britannico. Il "cervello" è Claude (API Anthropic);
il server gira su una macchina sempre accesa e l'iPad lo usa tramite Siri
(Comandi Rapidi), un'app web (HUD) e Telegram.

> Stato: **Fase 1 — Fondamenta**. Per ora si conversa da terminale.
> README completo (installazione su iPad, integrazioni, troubleshooting) in Fase 8.

## Requisiti

- Python 3.11+ e [`uv`](https://docs.astral.sh/uv/)
- Una chiave Claude API: <https://console.anthropic.com> → *API Keys*.
  È a consumo e separata dall'abbonamento a Claude.

## Avvio rapido

```bash
uv sync
cp .env.example .env        # poi inserisca ANTHROPIC_API_KEY in .env
uv run jarvis
```

Esempi da provare:

- «Buongiorno Jarvis, che giorno è oggi?» → modello rapido (Haiku)
- «Spiegami come funziona un mutuo a tasso variabile» → modello di ragionamento (Sonnet)
- «Pensaci bene: conviene l'auto elettrica per 8000 km l'anno?» → modello approfondito (Opus)

Comandi nel terminale: `/reset` dimentica la conversazione, `/modello` mostra i
modelli configurati, `/esci` chiude.

## Configurazione

Tutto in `config.yaml`: come Jarvis si rivolge a Lei (`user.title`), posizione,
fuso orario, modelli per livello, parole che attivano il ragionamento
approfondito. La personalità è in `server/jarvis/brain/persona.md`.

## Verifica

```bash
uv run pytest -q
uv run ruff check .
uv run mypy
```
