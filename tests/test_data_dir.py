import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

import core


BUNDLED_ENTRIES = core.BUNDLED_DATA_DIR / "entries.json"
BUNDLED_BYTES = BUNDLED_ENTRIES.read_bytes()


def load_with(data_dir):
    environment = {} if data_dir is None else {"DATA_DIR": str(data_dir)}
    with patch.dict(os.environ, environment, clear=True):
        return core._load_json("entries.json")


def test_data_dir_is_optional():
    assert load_with(None) == json.loads(BUNDLED_BYTES)


def test_missing_file_is_initialized():
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "entries.json"
        assert load_with(directory) == json.loads(BUNDLED_BYTES)
        assert target.read_bytes() == BUNDLED_BYTES


def test_empty_file_is_restored():
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "entries.json"
        target.touch()
        assert load_with(directory) == json.loads(BUNDLED_BYTES)
        assert target.read_bytes() == BUNDLED_BYTES


def test_invalid_json_is_restored():
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "entries.json"
        target.write_text("not json", encoding="utf-8")
        assert load_with(directory) == json.loads(BUNDLED_BYTES)
        assert target.read_bytes() == BUNDLED_BYTES


def test_valid_json_is_preserved():
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "entries.json"
        custom_data = [{"lemma": "test-entry"}]
        original = json.dumps(custom_data).encode("utf-8")
        target.write_bytes(original)
        assert load_with(directory) == custom_data
        assert target.read_bytes() == original


if __name__ == "__main__":
    test_data_dir_is_optional()
    test_missing_file_is_initialized()
    test_empty_file_is_restored()
    test_invalid_json_is_restored()
    test_valid_json_is_preserved()
    print("OK: DATA_DIR fallback and initialization scenarios")
