# Contributing

## Golden rule
`gateway/interfaces.py` is the shared contract. **Do not change it without all
three owners agreeing** — everyone builds against it.

## Branches
- Never commit directly to `main`.
- Branch names: `feat/trimmer-...`, `feat/cache-...`, `feat/autopilot-...`, `chore/...`, `fix/...`
- Keep branches small; open a Pull Request early.

## Pull Requests
- Open a PR into `main`. Get **1 review** from a teammate before merging.
- Make sure `pytest` passes locally first.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest            # run all tests
```

## Who owns what
- `trimmer/`  -> Agam
- `cache/`    -> Devansh
- `autopilot/`-> Furmaan
- `gateway/`  -> shared (lead reviews changes)
