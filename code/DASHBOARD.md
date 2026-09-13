# Live savings dashboard

A web page, served by the gateway itself, that shows what it is doing and how
much it is saving — in real time.

## Run it

```bash
cd code
.venv/bin/uvicorn gateway.app:app --port 8000
```

Then open **http://localhost:8000** in a browser. With no `PROVIDER_API_KEY`
set, the gateway answers from a mock provider, so this runs with no key and no
cost. Send it traffic (e.g. `python demo.py` in another terminal, or any
OpenAI-compatible client pointed at `http://localhost:8000/v1`) and watch the
dashboard update.

## What it shows

- **Try it:** a prompt box at the top. Type a question and press Send (or
  ⌘/Ctrl+Enter); it goes through the gateway to the model and the answer appears
  below, tagged with what happened — `cache hit` / `trimmed` / `forwarded` — plus
  tokens in, tokens sent, tokens saved and the round-trip time. Ask the same
  thing twice to watch it flip to a cache hit. No second terminal needed.

- **KPIs:** requests, cache hit-rate, tokens saved, % reduction, and an
  estimated dollar figure (at ~$0.15 / 1M input tokens, for illustration).
- **Sent vs. saved bar:** the share of tokens that reached the provider versus
  the share the gateway avoided.
- **Recent activity:** each request with its outcome — `cache hit` (served free),
  `trimmed` (bulky code collapsed), or `forwarded` — and original / sent / saved
  token counts.

## How it works

- `gateway/metrics.py` — lightweight in-memory metering; every request records
  its outcome and token counts.
- `GET /stats` — JSON snapshot of the running totals + recent feed.
- `POST /stats/reset` — clears the counters (the "reset" button).
- `GET /` — serves `gateway/static/dashboard.html`, which polls `/stats` every
  1.5 s. Same origin, so no CORS setup is needed.

Metrics are in-memory and reset when the gateway restarts — fine for a live demo
and local use; a persistent store would be a later addition.
