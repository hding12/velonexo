"""Shared local-data layout. Relative overrides are relative to the code root."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def local_root(code_root=ROOT):
    code_root = Path(code_root).resolve()
    value = os.environ.get('VELONEXO_LOCAL_ROOT')
    marker = code_root / '.workspace.local.json'
    if not value and marker.exists():
        value = json.loads(marker.read_text())['localRoot']
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError('Invalid local workspace path')
    return (code_root / (value or '.local-work')).resolve()

LOCAL_ROOT = local_root()
RUNTIME = LOCAL_ROOT / 'runtime'
CATALOG = LOCAL_ROOT / 'catalog/videos.json'
CONFIG = LOCAL_ROOT / 'config/storage.json'
ENV_FILE = LOCAL_ROOT / 'secrets/.env.local'
