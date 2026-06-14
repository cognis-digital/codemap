"""Command-line interface for CODEMAP.

Examples:
  # Validate a code (system auto-detected) using the built-in table
  codemap validate E11.9

  # Crosswalk an ICD-10 code to all mapped systems, as JSON
  codemap crosswalk E11.9 --format json

  # Crosswalk and keep only RxNorm targets, using your own table
  codemap crosswalk I10 --to RXNORM --table mytable.csv

  # Validate several codes from a file (one per line); CI-friendly exit code
  codemap validate --input codes.txt --format json

Exit codes: 0 = all good, 1 = at least one invalid/unknown finding, 2 = usage error.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import List, Optional

from codemap import TOOL_NAME, TOOL_VERSION
from codemap.core import (
    CodeSystem,
    Terminology,
    detect_system,
    load_default,
    load_table,
)


def _die(msg: str) -> int:
    """Print *msg* to stderr and return exit code 2 (usage/input error)."""
    print(f"error: {msg}", file=sys.stderr)
    return 2


def _load(table_path: Optional[str]) -> Terminology:
    """Load terminology from *table_path* or fall back to the built-in table.

    Raises SystemExit(2) with a clear message on any I/O or parse failure.
    """
    if not table_path:
        return load_default()
    try:
        return load_table(table_path)
    except FileNotFoundError:
        print(f"error: table file not found: {table_path!r}", file=sys.stderr)
        raise SystemExit(2)
    except (UnicodeDecodeError, csv.Error) as exc:
        print(f"error: could not read table file {table_path!r}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"error: I/O error reading table file {table_path!r}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def _read_codes(args) -> List[str]:
    """Collect codes from positional args and/or --input file.

    Raises SystemExit(2) with a clear message if the input file cannot be read.
    """
    codes: List[str] = list(args.codes or [])
    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        codes.append(line)
        except FileNotFoundError:
            print(f"error: input file not found: {args.input!r}", file=sys.stderr)
            raise SystemExit(2)
        except UnicodeDecodeError as exc:
            print(
                f"error: input file {args.input!r} is not valid UTF-8: {exc}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        except OSError as exc:
            print(f"error: could not read input file {args.input!r}: {exc}", file=sys.stderr)
            raise SystemExit(2)
    return codes


def _print_table(rows: List[List[str]], headers: List[str]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))


def _cmd_validate(args) -> int:
    term = _load(args.table)
    codes = _read_codes(args)
    if not codes:
        print("error: no codes provided", file=sys.stderr)
        return 2
    results = [term.validate(c) for c in codes]
    findings = sum(1 for r in results if not (r.valid and r.known))
    if args.format == "json":
        print(json.dumps({
            "results": [r.as_dict() for r in results],
            "total": len(results),
            "findings": findings,
        }, indent=2))
    else:
        rows = [[r.raw, r.system.value, r.code,
                 "valid" if r.valid else "INVALID",
                 "yes" if r.known else "no",
                 r.display or r.reason] for r in results]
        _print_table(rows, ["raw", "system", "code", "format", "known", "display/reason"])
        print(f"\n{len(results)} code(s), {findings} finding(s).")
    return 1 if findings else 0


def _cmd_crosswalk(args) -> int:
    term = _load(args.table)
    target = None
    if args.to:
        try:
            target = CodeSystem(args.to.strip().upper().replace("-", ""))
        except ValueError:
            print(f"error: unknown target system {args.to!r}", file=sys.stderr)
            return 2
    matches = term.crosswalk(args.code, target)
    src_system = detect_system(args.code)
    if args.format == "json":
        print(json.dumps({
            "source": {"raw": args.code, "system": src_system.value},
            "matches": [m.as_dict() for m in matches],
            "count": len(matches),
        }, indent=2))
    else:
        if not matches:
            print(f"No crosswalk targets found for {args.code} ({src_system.value}).")
        else:
            rows = [[m.system.value, m.code, m.display] for m in matches]
            _print_table(rows, ["system", "code", "display"])
            print(f"\n{len(matches)} mapped concept(s) from {args.code}.")
    # A crosswalk with zero results is a CI finding.
    return 0 if matches else 1


def _cmd_detect(args) -> int:
    codes = _read_codes(args)
    if not codes:
        print("error: no codes provided", file=sys.stderr)
        return 2
    items = [{"raw": c, "system": detect_system(c).value} for c in codes]
    unknown = sum(1 for it in items if it["system"] == "UNKNOWN")
    if args.format == "json":
        print(json.dumps({"results": items, "unknown": unknown}, indent=2))
    else:
        _print_table([[it["raw"], it["system"]] for it in items], ["raw", "system"])
    return 1 if unknown else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="CODEMAP - offline medical code crosswalk and validator "
                    "(ICD-10 / LOINC / RxNorm / CPT).",
        epilog="Examples:\n"
               "  codemap validate E11.9\n"
               "  codemap crosswalk E11.9 --to RXNORM --format json\n"
               "  codemap detect 4548-4\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    v = sub.add_parser("validate", help="validate and identify codes")
    v.add_argument("codes", nargs="*", help="one or more codes")
    v.add_argument("--input", help="file with one code per line")
    v.add_argument("--table", help="custom terminology CSV (defaults to built-in)")
    v.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")
    v.set_defaults(func=_cmd_validate)

    c = sub.add_parser("crosswalk", help="map a code to equivalent concepts")
    c.add_argument("code", help="the source code")
    c.add_argument("--to", help="limit to a target system (ICD10/LOINC/RXNORM/CPT)")
    c.add_argument("--table", help="custom terminology CSV (defaults to built-in)")
    c.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")
    c.set_defaults(func=_cmd_crosswalk)

    d = sub.add_parser("detect", help="detect the coding system of raw codes")
    d.add_argument("codes", nargs="*", help="one or more codes")
    d.add_argument("--input", help="file with one code per line")
    d.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")
    d.set_defaults(func=_cmd_detect)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except SystemExit:
        # Re-raise SystemExit so _load/_read_codes can propagate exit-code-2
        # errors cleanly without being swallowed by the generic handler below.
        raise
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"error: unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
