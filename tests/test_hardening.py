"""Tests for hardened error handling and edge cases in CODEMAP CLI."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codemap.cli import main


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
