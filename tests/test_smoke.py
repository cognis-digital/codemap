"""Smoke tests for CODEMAP. No network. Runs against the built-in table
and the demo input file.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codemap.core import CodeSystem, detect_system, load_default
from codemap.cli import main

DEMO = os.path.join(os.path.dirname(__file__), "..", "demos", "01-basic", "sample_codes.txt")


def test_detect_system():
    assert detect_system("E11.9") == CodeSystem.ICD10
    assert detect_system("4548-4") == CodeSystem.LOINC
    assert detect_system("99213") == CodeSystem.CPT
    assert detect_system("6809") == CodeSystem.RXNORM
    assert detect_system("ZZZ999") == CodeSystem.UNKNOWN
    # Explicit prefix overrides shape.
    assert detect_system("RXNORM:435") == CodeSystem.RXNORM


def test_loinc_check_digit():
    # 4548-4 is a real, well-formed LOINC code with a valid check digit.
    res = load_default().validate("4548-4")
    assert res.valid and res.known
    assert "A1c" in res.display
    # Wrong check digit must fail validation.
    bad = load_default().validate("4548-9")
    assert not bad.valid


def test_validate_known_and_unknown():
    term = load_default()
    ok = term.validate("E11.9")
    assert ok.valid and ok.known and ok.system == CodeSystem.ICD10
    unknown_shape = term.validate("ZZZ999")
    assert not unknown_shape.valid
    wellformed_not_in_table = term.validate("A00.0")
    assert wellformed_not_in_table.valid and not wellformed_not_in_table.known


def test_crosswalk_diabetes():
    matches = load_default().crosswalk("E11.9")
    pairs = {(m.system, m.code) for m in matches}
    assert (CodeSystem.LOINC, "4548-4") in pairs
    assert (CodeSystem.RXNORM, "6809") in pairs
    # source itself is never returned
    assert (CodeSystem.ICD10, "E11.9") not in pairs


def test_crosswalk_reverse_and_target_filter():
    # Metformin (RxNorm) should map back to the diabetes ICD-10 code.
    matches = load_default().crosswalk("6809", CodeSystem.ICD10)
    assert any(m.code == "E11.9" for m in matches)
    assert all(m.system == CodeSystem.ICD10 for m in matches)


def test_cli_validate_demo_file_exit_code(capsys):
    # Demo file contains ZZZ999 which is a finding -> exit 1.
    rc = main(["validate", "--input", DEMO, "--format", "json"])
    out = capsys.readouterr().out
    assert '"findings"' in out
    assert rc == 1


def test_cli_crosswalk_json_exit_zero(capsys):
    rc = main(["crosswalk", "E11.9", "--format", "json"])
    out = capsys.readouterr().out
    assert '"matches"' in out
    assert "4548-4" in out
    assert rc == 0


def test_cli_crosswalk_no_match_exit_one():
    # Well-formed but unmapped code yields no targets -> finding -> exit 1.
    rc = main(["crosswalk", "A00.0"])
    assert rc == 1


def test_version_exits_zero(capsys):
    try:
        main(["--version"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "codemap" in out
