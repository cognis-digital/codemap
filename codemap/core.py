"""Core engine for CODEMAP.

A terminology crosswalk over a local table of medical codes. Supports four
coding systems: ICD-10(-CM), LOINC, RxNorm, and CPT. The engine does real
work: it detects which system a raw code belongs to from its lexical shape,
normalizes/validates the code against per-system rules, and crosswalks a code
to equivalent concepts in other systems using the loaded mapping table.

The table format is a simple CSV with header:

    system,code,display,maps_to

where `maps_to` is a ';'-separated list of `SYSTEM:CODE` cross-references.
A small built-in table ships with the tool so it is useful out of the box.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple


class CodeSystem(str, Enum):
    ICD10 = "ICD10"
    LOINC = "LOINC"
    RXNORM = "RXNORM"
    CPT = "CPT"
    UNKNOWN = "UNKNOWN"


# --- Per-system lexical rules ------------------------------------------------
# ICD-10-CM: letter, 2 digits, optional '.' then up to 4 alphanumerics.
_ICD10_RE = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](?:\.?[0-9A-Z]{0,4})$")
# LOINC: 1-7 digits, a dash, then a single check digit.
_LOINC_RE = re.compile(r"^\d{1,7}-\d$")
# CPT: 5 chars - either 5 digits (Cat I) or 4 digits + trailing letter (Cat II/III).
_CPT_RE = re.compile(r"^(?:\d{5}|\d{4}[A-Z])$")
# RxNorm: a bare numeric concept id (RXCUI), 1-8 digits.
_RXNORM_RE = re.compile(r"^\d{1,8}$")


def normalize_code(raw: str) -> str:
    """Trim, uppercase, and strip an explicit `SYSTEM:` prefix if present."""
    if raw is None:
        return ""
    s = raw.strip().upper()
    # Strip a leading explicit system tag like "ICD10:E11.9".
    m = re.match(r"^(ICD10|ICD-10|LOINC|RXNORM|RXCUI|CPT)\s*:\s*(.+)$", s)
    if m:
        s = m.group(2).strip()
    return s


def _system_hint(raw: str) -> Optional[CodeSystem]:
    """Return a system if the raw value carried an explicit prefix."""
    if raw is None:
        return None
    m = re.match(r"^\s*(ICD10|ICD-10|LOINC|RXNORM|RXCUI|CPT)\s*:", raw.strip().upper())
    if not m:
        return None
    tag = m.group(1)
    return {
        "ICD10": CodeSystem.ICD10,
        "ICD-10": CodeSystem.ICD10,
        "LOINC": CodeSystem.LOINC,
        "RXNORM": CodeSystem.RXNORM,
        "RXCUI": CodeSystem.RXNORM,
        "CPT": CodeSystem.CPT,
    }[tag]


def detect_system(raw: str) -> CodeSystem:
    """Infer the coding system of a raw code from its lexical shape.

    An explicit prefix (e.g. ``ICD10:E11.9``) always wins. Otherwise the code
    shape is matched against per-system patterns. LOINC and CPT have distinctive
    shapes; ICD-10 requires a leading letter; a bare integer is treated as an
    RxNorm RXCUI.
    """
    hinted = _system_hint(raw)
    if hinted is not None:
        return hinted
    s = normalize_code(raw)
    if not s:
        return CodeSystem.UNKNOWN
    if _LOINC_RE.match(s):
        return CodeSystem.LOINC
    if _ICD10_RE.match(s) and not s.isdigit():
        return CodeSystem.ICD10
    if _CPT_RE.match(s) and not s.isdigit():
        # 4 digits + letter is unambiguously CPT Cat II/III.
        return CodeSystem.CPT
    if s.isdigit():
        # Pure 5-digit codes are ambiguous between CPT and RxNorm; CPT wins.
        if len(s) == 5 and _CPT_RE.match(s):
            return CodeSystem.CPT
        if _RXNORM_RE.match(s):
            return CodeSystem.RXNORM
    return CodeSystem.UNKNOWN


def _valid_for(system: CodeSystem, code: str) -> bool:
    if system == CodeSystem.ICD10:
        return bool(_ICD10_RE.match(code)) and not code.isdigit()
    if system == CodeSystem.LOINC:
        return bool(_LOINC_RE.match(code)) and _loinc_check_ok(code)
    if system == CodeSystem.CPT:
        return bool(_CPT_RE.match(code))
    if system == CodeSystem.RXNORM:
        return bool(_RXNORM_RE.match(code))
    return False


def _loinc_check_ok(code: str) -> bool:
    """Verify a LOINC mod-10 check digit (Luhn-style on the numeric body)."""
    try:
        body, check = code.split("-")
    except ValueError:
        return False
    digits = [int(c) for c in body]
    total = 0
    # Apply weights 2,1,2,1... from the rightmost body digit.
    for i, d in enumerate(reversed(digits)):
        w = 2 if i % 2 == 0 else 1
        p = d * w
        if p > 9:
            p -= 9
        total += p
    expected = (10 - (total % 10)) % 10
    return expected == int(check)


@dataclass(frozen=True)
class CodeRecord:
    system: CodeSystem
    code: str
    display: str
    maps_to: Tuple[Tuple[CodeSystem, str], ...] = ()

    def as_dict(self) -> dict:
        return {
            "system": self.system.value,
            "code": self.code,
            "display": self.display,
            "maps_to": [{"system": s.value, "code": c} for s, c in self.maps_to],
        }


@dataclass
class ValidationResult:
    raw: str
    code: str
    system: CodeSystem
    valid: bool
    known: bool
    display: Optional[str] = None
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "raw": self.raw,
            "code": self.code,
            "system": self.system.value,
            "valid": self.valid,
            "known": self.known,
            "display": self.display,
            "reason": self.reason,
        }


class Terminology:
    """An in-memory terminology table supporting lookup and crosswalk."""

    def __init__(self) -> None:
        # (system, code) -> CodeRecord
        self._records: Dict[Tuple[CodeSystem, str], CodeRecord] = {}

    def add(self, record: CodeRecord) -> None:
        self._records[(record.system, record.code)] = record

    def get(self, system: CodeSystem, code: str) -> Optional[CodeRecord]:
        return self._records.get((system, code))

    def __len__(self) -> int:
        return len(self._records)

    def records(self) -> Iterable[CodeRecord]:
        return self._records.values()

    def validate(self, raw: str) -> ValidationResult:
        system = detect_system(raw)
        code = normalize_code(raw)
        if system == CodeSystem.UNKNOWN:
            return ValidationResult(raw, code, system, False, False,
                                    reason="could not detect coding system")
        valid = _valid_for(system, code)
        rec = self.get(system, code)
        if not valid:
            return ValidationResult(raw, code, system, False, rec is not None,
                                    display=rec.display if rec else None,
                                    reason=f"malformed {system.value} code")
        if rec is None:
            return ValidationResult(raw, code, system, True, False,
                                    reason="well-formed but not in table")
        return ValidationResult(raw, code, system, True, True,
                                display=rec.display, reason="ok")

    def crosswalk(self, raw: str,
                  target: Optional[CodeSystem] = None) -> List[CodeRecord]:
        """Return target-system records mapped from the given source code.

        Mappings are followed bidirectionally: an entry that declares
        ``maps_to`` is honored, and any record that maps *to* the source is
        also returned. Results are de-duplicated and exclude the source.
        """
        system = detect_system(raw)
        code = normalize_code(raw)
        src = self.get(system, code)
        out: Dict[Tuple[CodeSystem, str], CodeRecord] = {}
        if src is not None:
            for s, c in src.maps_to:
                rec = self.get(s, c)
                if rec is not None:
                    out[(s, c)] = rec
        # Reverse direction.
        for rec in self._records.values():
            for s, c in rec.maps_to:
                if s == system and c == code:
                    out[(rec.system, rec.code)] = rec
        results = [r for (s, _), r in out.items()
                   if not (r.system == system and r.code == code)]
        if target is not None:
            results = [r for r in results if r.system == target]
        return sorted(results, key=lambda r: (r.system.value, r.code))


def _parse_maps_to(field_val: str) -> Tuple[Tuple[CodeSystem, str], ...]:
    out: List[Tuple[CodeSystem, str]] = []
    if not field_val:
        return tuple(out)
    for part in field_val.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        sys_tag, code = part.split(":", 1)
        sys_tag = sys_tag.strip().upper().replace("-", "")
        if sys_tag == "RXCUI":
            sys_tag = "RXNORM"
        try:
            cs = CodeSystem(sys_tag)
        except ValueError:
            continue
        out.append((cs, code.strip().upper()))
    return tuple(out)


def load_table(source) -> Terminology:
    """Load a terminology table from a file path or an open text stream.

    Expected CSV header: ``system,code,display,maps_to``.
    """
    term = Terminology()
    if hasattr(source, "read"):
        reader = csv.DictReader(source)
        _ingest(reader, term)
    else:
        with open(source, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            _ingest(reader, term)
    return term


def _ingest(reader: csv.DictReader, term: Terminology) -> None:
    for row in reader:
        if not row.get("system") or not row.get("code"):
            continue
        sys_tag = row["system"].strip().upper().replace("-", "")
        if sys_tag == "RXCUI":
            sys_tag = "RXNORM"
        try:
            cs = CodeSystem(sys_tag)
        except ValueError:
            continue
        term.add(CodeRecord(
            system=cs,
            code=row["code"].strip().upper(),
            display=(row.get("display") or "").strip(),
            maps_to=_parse_maps_to((row.get("maps_to") or "").strip()),
        ))


# --- Convenience functions over a default/loaded table -----------------------
def validate_code(raw: str, term: Optional[Terminology] = None) -> ValidationResult:
    term = term if term is not None else load_default()
    return term.validate(raw)


def lookup(raw: str, term: Optional[Terminology] = None) -> Optional[CodeRecord]:
    term = term if term is not None else load_default()
    return term.get(detect_system(raw), normalize_code(raw))


def crosswalk(raw: str, target: Optional[CodeSystem] = None,
              term: Optional[Terminology] = None) -> List[CodeRecord]:
    term = term if term is not None else load_default()
    return term.crosswalk(raw, target)


# A small, real built-in crosswalk table so the tool works with zero config.
DEFAULT_TABLE = """system,code,display,maps_to
ICD10,E11.9,Type 2 diabetes mellitus without complications,LOINC:4548-4;RXNORM:6809
ICD10,I10,Essential (primary) hypertension,RXNORM:29046;CPT:99213
ICD10,J45.909,Unspecified asthma uncomplicated,RXNORM:435;CPT:94010
ICD10,E78.5,Hyperlipidemia unspecified,LOINC:2093-3;RXNORM:36567
LOINC,4548-4,Hemoglobin A1c/Hemoglobin.total in Blood,ICD10:E11.9
LOINC,2093-3,Cholesterol [Mass/volume] in Serum or Plasma,ICD10:E78.5
LOINC,2160-0,Creatinine [Mass/volume] in Serum or Plasma,
RXNORM,6809,Metformin,ICD10:E11.9
RXNORM,29046,Lisinopril,ICD10:I10
RXNORM,435,Albuterol,ICD10:J45.909
RXNORM,36567,Simvastatin,ICD10:E78.5
CPT,99213,Office/outpatient visit established patient,ICD10:I10
CPT,94010,Spirometry,ICD10:J45.909
CPT,80061,Lipid panel,LOINC:2093-3
"""


_DEFAULT_CACHE: Optional[Terminology] = None


def load_default() -> Terminology:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = load_table(io.StringIO(DEFAULT_TABLE))
    return _DEFAULT_CACHE
