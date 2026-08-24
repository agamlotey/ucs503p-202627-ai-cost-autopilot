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

Copy `code/.env.example` to `code/.env` and adjust:

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
