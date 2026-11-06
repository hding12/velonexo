"""Initialize missing local files without replacing existing data or credentials."""
import argparse
import json
import os
from pathlib import Path
from workspace_paths import ROOT, local_root


def initialize(code_root=ROOT, destination=None):
    code_root = Path(code_root).resolve()
    target = (code_root / destination).resolve() if destination else local_root(code_root)
    if target == code_root:
        raise ValueError('Local data must have its own directory')
    for name in ('runtime/publisher', 'runtime/studio', 'catalog', 'config', 'secrets'):
        (target / name).mkdir(parents=True, exist_ok=True)
    for template, name in [('config/catalog.example.json','catalog/videos.json'),('config/storage.example.json','config/storage.json'),('.env.example','secrets/.env.local')]:
        try:
            fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'wb') as out:
            out.write((code_root / template).read_bytes())
    if destination:
        marker = code_root / '.workspace.local.json'
        value = {'localRoot': os.path.relpath(target, code_root)}
        if marker.exists() and json.loads(marker.read_text()) != value:
            raise ValueError('Workspace already configured; edit the local marker explicitly to switch')
        if not marker.exists():
            with marker.open('x') as out:
                out.write(json.dumps(value) + '\n')
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-root')
    args = parser.parse_args()
    print('Local workspace initialized:', initialize(destination=args.local_root))
