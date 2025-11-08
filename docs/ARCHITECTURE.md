# CODEMAP — Architecture

> Translate and validate medical codes across ICD-10, SNOMED CT, LOINC, RxNorm, and CPT from the CLI.

```
input ──▶ collect ──▶ rules/analyzers ──▶ score ──▶ findings ──▶ table · json
                              │                          │
                         (this repo)                 MCP tool (agents)
```

- **collect** normalizes the target (file/dir/API) into records.
- **rules/analyzers** apply the heuristics shipped in `codemap/core.py`.
- **score** ranks by severity.
- **MCP server** (`codemap mcp`) exposes `scan` for Cognis.Studio agents.

Extend by adding a rule + a test + a `demos/NN-*/SCENARIO.md`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
