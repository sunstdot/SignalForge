"""Local, atomic daily coverage state independent of stored content items."""
import json
import os
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from .storage import DATA_DIR


SOURCE_RUN_DIR = DATA_DIR / 'source_runs'


def _path(day: str) -> Path:
    date.fromisoformat(day)
    return SOURCE_RUN_DIR / f'{day}.json'


def load_source_run(day: str) -> dict:
    path = _path(day)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def save_source_run(day: str, payload: dict) -> None:
    path = _path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                prefix=f'{day}-', suffix='.tmp', delete=False) as handle:
            tmp = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
