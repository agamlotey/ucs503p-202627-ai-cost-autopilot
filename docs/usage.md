# Usage

All application code lives in the `code/` folder of the repository.

## Install

``` shell
cd code
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the gateway

``` shell
uvicorn gateway.app:app --reload --port 8000
```

Check it is alive:

``` shell
curl http://localhost:8000/health
# {"status":"ok"}
```

## Configuration

The gateway reads environment variables when it starts. From the `code/`
directory, export your settings in the same terminal before launching it.
For example:

```shell
export DEFAULT_MODEL=gpt-4o-mini
uvicorn gateway.app:app --port 8000
```

See `.env.example` for the available settings. Copying that file alone does
not load its values into the gateway process.

| Variable | Meaning |
|---|---|
| `PROVIDER_BASE_URL` | Upstream API base URL (default: OpenAI) |
| `PROVIDER_API_KEY` | Your provider key |
| `DEFAULT_MODEL` | Model used when the client does not name one |
| `TOKEN_BUDGET` | Trim only when a request exceeds this many tokens |
| `MOCK_PROVIDER` | `1` to return a canned reply instead of calling a provider |

### Offline mock mode

With `MOCK_PROVIDER=1` (or no API key set) the gateway returns a canned response
instead of calling a real provider. The full pipeline — signals, autopilot,
cache, trimmer — still runs, so the whole system can be developed and tested
**with no API key and no cost**.

``` shell
MOCK_PROVIDER=1 uvicorn gateway.app:app --port 8000
```

## Connect a coding agent

The gateway speaks the OpenAI/Anthropic chat-completions format, so a tool
connects by pointing its base URL at the gateway:

| Tool | Setting |
|---|---|
| Cursor | Override the OpenAI base URL |
| Claude Code | `ANTHROPIC_BASE_URL` |
| Aider | `OPENAI_API_BASE` |
| Cline / Continue | Custom provider → API base |

Set it to `http://localhost:8000/v1`.

## Run the tests

``` shell
cd code
pytest
```

Tests also run automatically on every push and pull request via GitHub Actions.

## Host the mock dashboard

In Render, choose **New → Blueprint**, connect this repository, and select
`master`. The root `render.yaml` configures one free Python service. The
dashboard and gateway share the service URL. It starts in mock mode and needs
no provider key.

Once Render reports the service healthy, open its URL and send a sample prompt
twice. An exact repeat should show a cache hit and zero tokens forwarded. Use
sample text for this shared demo because ordinary prompt previews appear in
the activity feed. A service restart clears the in-memory cache and counters.
