# AquaCyber

A 5-minute cyber risk check for small fish and shellfish farms.
It turns cyber and equipment gaps into **fish and dollars at risk**, shows **PASS / FIX** for 9 checks
that insurers, GLOBALG.A.P. and Canada's Cyber Centre look for, and prints a one-page report.

Built for the Brampton SecOps Hackathon 2026 — Challenge 2.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app app run              # open http://127.0.0.1:5000
```

Demo shortcuts: `/demo/netpen` (BC salmon net-pen) and `/demo/ras` (Ontario trout tanks).

## Test

```bash
pytest -q
```

## Deploy

Any Python host (Render, Railway, Fly.io, Heroku-style) works. Start command: `gunicorn app:app`.

## Project layout

```
app.py                 Flask routes (profile -> checks -> report, plus demos)
aquacyber/engine.py    Risk engine: checks, fish-loss model, report data, sources
templates/             Jinja pages (base, profile, checks, report)
static/style.css       Styles (light/dark, print-friendly)
tests/                 Engine and app tests
```

## How the numbers work

- **Fish loss** = stock x (time to notice + time to restore) / survival hours, capped at 100%.
  Survival hours come from the farmer. Notice/restore times are our stated assumptions (see `engine.py`).
- **Fraud exposure** = one month of supplier payments (assumption).
- **Ransomware outage** = 5 days without offline backup vs 1 with (assumption), at daily sales.
- Every assumption and source is shown in the report under "Sources and assumptions".

This is a self-assessment tool, not an audit, certificate or insurance advice.
