"""Tests for hardened error handling and edge cases in CODEMAP CLI and core."""
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codemap.cli import main
from codemap.core import (
    CodeSystem,
    detect_system,
    load_table,
    normalize_code,
    _loinc_check_ok,
)


def test_validate_missing_input_file_exits_2(capsys):
    """--input pointing to a nonexistent file must exit 2 with an error message."""
    with pytest.raises(SystemExit) as exc_info:
        main(["validate", "--input", "/nonexistent/does_not_exist.txt"])
    assert exc_info.value.code == 2
    assert "error" in capsys.readouterr().err


def test_validate_missing_table_file_exits_2(capsys):
    """--table pointing to a nonexistent file must exit 2 with an error message."""
    with pytest.raises(SystemExit) as exc_info:
        main(["validate", "E11.9", "--table", "/nonexistent/table.csv"])
    assert exc_info.value.code == 2
    assert "error" in capsys.readouterr().err


def test_crosswalk_missing_table_file_exits_2(capsys):
    """crosswalk --table pointing to a nonexistent file must exit 2."""
    with pytest.raises(SystemExit) as exc_info:
        main(["crosswalk", "E11.9", "--table", "/no/such/file.csv"])
    assert exc_info.value.code == 2
    assert "error" in capsys.readouterr().err


def test_validate_binary_input_file_exits_2(capsys):
    """An input file with non-UTF-8 bytes must exit 2 with an error message."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
        # Write bytes that are invalid UTF-8 (0xFF 0xFE BOM + garbage).
        f.write(bytes.fromhex("fffe") + b"binary garbage")
        path = f.name
    try:
        with pytest.raises(SystemExit) as exc_info:
            main(["validate", "--input", path])
        assert exc_info.value.code == 2
        assert "error" in capsys.readouterr().err
    finally:
        os.unlink(path)


def test_validate_binary_table_exits_2(capsys):
    """A --table file with non-UTF-8 bytes must exit 2 with an error message."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        f.write(bytes.fromhex("fffe") + b"binary garbage")
        path = f.name
    try:
        with pytest.raises(SystemExit) as exc_info:
            main(["validate", "E11.9", "--table", path])
        assert exc_info.value.code == 2
        assert "error" in capsys.readouterr().err
    finally:
        os.unlink(path)


def test_crosswalk_invalid_to_target_exits_2(capsys):
    """crosswalk with an unknown --to system name must return 2."""
    rc = main(["crosswalk", "E11.9", "--to", "NOTASYSTEM"])
    assert rc == 2
    assert "unknown target system" in capsys.readouterr().err


def test_validate_comments_only_input_file_exits_2(capsys):
    """An input file that yields no codes (all comment lines) must exit 2."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("# only a comment line" + chr(10))
        path = f.name
    try:
        rc = main(["validate", "--input", path])
        assert rc == 2
        assert "no codes" in capsys.readouterr().err
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Core edge-case hardening tests
# ---------------------------------------------------------------------------


def test_normalize_code_none_returns_empty():
    """normalize_code(None) must return '' rather than raising AttributeError."""
    assert normalize_code(None) == ""


def test_normalize_code_whitespace_only():
    """All-whitespace input normalizes to empty string."""
    assert normalize_code("   ") == ""


def test_detect_system_empty_string():
    """detect_system('') must return UNKNOWN, not raise."""
    assert detect_system("") == CodeSystem.UNKNOWN


def test_detect_system_whitespace_only():
    """detect_system on whitespace must return UNKNOWN, not raise."""
    assert detect_system("   ") == CodeSystem.UNKNOWN


def test_loinc_check_non_numeric_body():
    """_loinc_check_ok must return False (not crash) on a non-numeric body."""
    assert _loinc_check_ok("ABCD-4") is False


def test_loinc_check_no_dash():
    """_loinc_check_ok must return False when the separator is absent."""
    assert _loinc_check_ok("45484") is False


def test_load_table_empty_csv():
    """A CSV with only a header and no data rows loads without error."""
    src = io.StringIO("system,code,display,maps_to\n")
    term = load_table(src)
    assert len(term) == 0


def test_load_table_missing_required_columns():
    """A CSV with missing required columns is silently skipped (no crash)."""
    src = io.StringIO("unrelated_col\nfoo\n")
    term = load_table(src)
    assert len(term) == 0


def test_load_table_skips_unknown_system_rows():
    """Rows with an unrecognised system value are skipped gracefully."""
    csv_text = "system,code,display,maps_to\nSNOMED,12345,Something,\n"
    term = load_table(io.StringIO(csv_text))
    assert len(term) == 0


def test_load_table_malformed_maps_to_is_silently_skipped():
    """A maps_to entry with an unknown system tag is skipped, rest loads fine."""
    csv_text = (
        "system,code,display,maps_to\n"
        "ICD10,E11.9,Diabetes,BADTAG:99999;LOINC:4548-4\n"
    )
    term = load_table(io.StringIO(csv_text))
    assert len(term) == 1
    rec = term.get(CodeSystem.ICD10, "E11.9")
    assert rec is not None
    # Only the valid LOINC mapping survives; the bad tag is silently dropped.
    assert any(s == CodeSystem.LOINC and c == "4548-4" for s, c in rec.maps_to)
    assert all(s != CodeSystem.UNKNOWN for s, _ in rec.maps_to)


def test_cli_validate_no_args_returns_2(capsys):
    """validate with no codes and no --input must return 2."""
    rc = main(["validate"])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_cli_detect_no_codes_returns_2(capsys):
    """detect with no codes and no --input must return 2."""
    rc = main(["detect"])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_mcp_server_module_imports_cleanly():
    """mcp_server must be importable without raising ImportError."""
    import importlib
    mod = importlib.import_module("codemap.mcp_server")
    assert callable(mod.serve)
