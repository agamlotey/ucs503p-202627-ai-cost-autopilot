# AI Cost Autopilot — dashboard (frontend)

The project's web frontend: a live savings dashboard built on the
[Dabang](https://github.com/themewagon/dabang) React + Material-UI template.
It does everything the gateway's built-in page does — **send prompts, show
cache hits / trims, live KPIs, a per-request chart and an activity feed** — in
the template's look.

## Run it

You need the gateway running first (from `code/`):

```bash
MOCK_PROVIDER=1 TOKEN_BUDGET=1000 uvicorn gateway.app:app --port 8000
```
(`MOCK_PROVIDER=1` = no API key, no cost. Drop it and set `PROVIDER_API_KEY`
for a real model. `TOKEN_BUDGET=1000` makes the trimmer fire on normal-sized
code pastes.)

Then, from `code/frontend/`:

```bash
npm install      # first time only
npm run dev      # http://localhost:3000
```

The dev server **proxies** `/stats` and `/v1/...` to the gateway (see
`vite.config.ts`), so the browser sees everything as one origin — no CORS setup.
If your gateway is on another port: `GATEWAY_URL=http://localhost:8001 npm run dev`.

## What's on the page

| Section | What it does | Talks to |
|---|---|---|
| **Try it** | type a prompt → answer + what happened (cache hit / trimmed / forwarded), tokens in / sent / saved, ms | `POST /v1/chat/completions`, then `/stats` |
| **Live savings** | requests, cache hit-rate, tokens saved, reduction, est. $; Reset button | `GET /stats` (polled every 1.5 s), `POST /stats/reset` |
| **Tokens per request** | stacked bar per request: sent to model vs. saved | `/stats.recent` |
| **Recent activity** | the feed, colour-coded by outcome | `/stats.recent` |

Source: `src/api/gateway.ts` (calls), `src/hooks/useStats.ts` (polling),
`src/components/sections/dashboard/*` (the four sections),
`src/pages/dashboard/Dashboard.tsx` (layout).

## Notes

- The **first prose request after the gateway starts takes ~7–15 s** (it loads
  the embedding model). Send one warm-up prompt before a demo.
- Metrics are in-memory in the gateway and reset when it restarts.
- `npm run build` produces a static `dist/`; serving that from a different
  origin than the gateway would need CORS on the gateway.
