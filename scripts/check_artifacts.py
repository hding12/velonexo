"""Validate build output contains no configured credentials or signed URLs."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from storage_probe import ROOT,dotenv_values

def main():
    values=dotenv_values(ROOT/'.env.local')
    secrets=[v for k,v in values.items() if v and len(v)>6 and any(s in k for s in ('TOKEN','SECRET','ACCESS_KEY'))]
    files=[p for p in (ROOT/'dist').rglob('*') if p.is_file()]
    if not files:raise SystemExit('Build output missing')
    failures=[]
    for p in files:
        data=p.read_bytes()
        if any(v.encode() in data for v in secrets) or b'X-Amz-Signature=' in data or b'x-amz-signature=' in data:
            failures.append(str(p.relative_to(ROOT)))
    if failures:raise SystemExit('Sensitive content detected in: '+', '.join(failures))
    print(f'PASS: {len(files)} build files contain no configured credentials or signed URLs')

if __name__=='__main__':main()
