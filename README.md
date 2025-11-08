# CODEMAP — Translate and validate medical codes across ICD-10, SNOMED CT, LOINC, RxNorm, and CPT from the CLI.

> Part of the **[Cognis Neural Suite](https://github.com/cognis-digital)** by [Cognis Digital](https://cognis.digital)
> Cognis Open Collaboration License (COCL) v1.0 · domain: `healthcare`

[![PyPI](https://img.shields.io/pypi/v/cognis-codemap.svg)](https://pypi.org/project/cognis-codemap/)
[![CI](https://github.com/cognis-digital/codemap/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/codemap/actions)
[![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE)
[![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

**Translate and validate medical codes across ICD-10, SNOMED CT, LOINC, RxNorm, and CPT from the CLI..**

*Healthcare & Life-Sciences — HIPAA, PHI, FHIR/HL7, and clinical data.*

## Why

CODEMAP exists for one job — translate and validate medical codes across icd-10, snomed ct, loinc, rxnorm, and cpt from the cli. — and does it without a SaaS bill or heavyweight setup.
Single-purpose, scriptable, CI-friendly, self-hostable, and callable by AI agents over MCP.

## Install

```bash
pip install cognis-codemap
# or from this repo:
pip install -e ".[dev]"
```

## Quick start

```bash
codemap --version
codemap scan .                      # scan the current project
codemap scan . --format json
codemap scan . --fail-on high       # non-zero exit for CI gates
codemap mcp                         # expose as an MCP server (Cognis.Studio / Claude Desktop / Cursor)
```

## Built-in demo scenarios

- [`demos/01-basic/`](demos/01-basic/SCENARIO.md)
- [`demos/02-clean/`](demos/02-clean/SCENARIO.md)
- [`demos/03-mixed/`](demos/03-mixed/SCENARIO.md)

## Inspiration / prior art

Built in the spirit of **OHDSI Athena + UMLS**, re-framed for the Cognis approach: single-purpose, self-hostable,
MCP-native, and unified with the rest of the Suite. Missing a credit? Open a PR.

## How it fits the Cognis Neural Suite

`codemap` is one of the **100+ tools** in the [Cognis Neural Suite](https://github.com/cognis-digital).
Every tool ships an MCP server, so [Cognis.Studio](https://cognis.studio) agents can call them as scoped capabilities.

- Design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Roadmap: [`ROADMAP.md`](ROADMAP.md)

## Contributing

PRs, new rules, and demo scenarios welcome under the collaboration-pull model — see
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal,
internal-evaluation, research, and educational use; **commercial / production use requires a license**
(licensing@cognis.digital). See [LICENSE](LICENSE).

## About

**[Cognis Digital](https://cognis.digital)** — Wyoming, USA · *Making Tomorrow Better Today.*
