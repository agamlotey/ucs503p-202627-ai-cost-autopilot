# Team

**UCS503: Software Engineering (Project), 2026–27 Odd**
Computer Science and Engineering Department, Thapar Institute of Engineering and
Technology, Patiala.

| Member | Roll No | Component |
|---|---|---|
| Agam | 1024240033 | [Compiler-Aware Trimmer](components/trimmer.md) |
| Devansh | 1024240012 | [Semantic Cache](components/cache.md) |
| Furmaan | 1024240029 | [Autopilot](components/autopilot.md) |

The gateway (`code/gateway/`) and the evaluation harness are shared, with
pull-request review across the team.

## How we work

- **One folder per owner**, so the three components can be built in parallel
  without merge conflicts.
- **Frozen interfaces** in `code/gateway/interfaces.py` — the contract each
  component implements. It is only changed when all three agree.
- **Branch per feature**, then a pull request into `master`, which is protected
  and requires review before merging.
- **Continuous integration** runs the test suite on every pull request.

## Journals

Each member keeps a weekly technical journal in the `journals/` folder of the
repository, documenting problems solved during development.
