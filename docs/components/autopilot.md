# Autopilot

**Owner:** Furmaan (1024240029) · **Code:** `code/autopilot/policy.py`

The gateway asks the policy two questions before forwarding a completion:
may this request use the response cache, and is its code large enough to trim?

## Routing

The gateway estimates input size from string message content and looks for code
markers. When the caller supplies no secret flag, the policy checks message
text, including text parts in multipart messages, for known credential and PII
patterns. A match disables both cache lookup and storage. Large code requests
can still be trimmed.

Trimming rewrites the prompt. Looking up that rewritten prompt against entries
keyed on the original can turn an exact repeat into a miss. The gateway checks
the original request first and uses that same key when it stores a response. A hit returns the
stored response. On a miss, the gateway calls the trimmer if the policy selected
it, then forwards the request to the provider. The cache owns similarity matching.
The policy keeps decision counts in memory. The gateway records token estimates
and the observed outcome in `/stats`.

## Choosing the trim threshold

I ran each threshold in a fresh local gateway with a mock provider and held
the trimmer's separate token budget at 1,000. I sent the fixture files as
individual messages using `trimmer.fixtures.loader.as_messages`. The table shows
the gateway's forwarded input-token counts on the first request.

| Fixture and task | Original | Threshold 500 | Threshold 1,000 | Threshold 4,000 |
|---|---:|---:|---:|---:|
| notes_api, fix create_note | 3,348 | 2,237 | 2,237 | 3,348 |
| ledger_cli, fix parse_row | 2,536 | 1,650 | 1,650 | 2,536 |

I kept the default at 1,000. Lowering it produced the same counts on these
fixtures. Raising it to 4,000 skipped trimming on both. Requests near the
lower cutoff would be needed to distinguish 500 from 1,000 more precisely.

At the default threshold, repeating the notes request returned the same
completion ID and forwarded zero tokens. I then appended a synthetic project
key in a user message and sent that request twice. The gateway trimmed both requests
and returned different mock completion IDs, confirming that the repeat also
reached the mock provider.

## Status and next steps

- [x] Route code-heavy requests using the gateway’s size estimate and code markers.
- [x] Bypass cache lookup and storage for detected secrets, including secrets in multipart text.
- [x] Check eligible requests for a cache hit before trimming and record the outcome in `/stats`.
- [x] Compare three policy thresholds on the notes_api and ledger_cli fixtures.
- [ ] Measure requests near the 1,000-token cutoff to determine when trimming saves enough input to justify its latency. Threshold selection is currently manual.
