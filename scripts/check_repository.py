"""Check the exact staged snapshot before publishing; print paths, never secret values."""
import re
import subprocess
from pathlib import PurePosixPath
from dotenv import dotenv_values
from workspace_paths import ROOT, ENV_FILE


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    secrets=[v.encode() for k,v in dotenv_values(ENV_FILE).items() if v and len(v)>6 and any(t in k for t in ('TOKEN','SECRET','ACCESS_KEY'))]
    pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}|hf_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    names=[s.decode() for s in git('ls-files','-z').split(b'\0') if s]
    failures=[];total=0
    for name in names:
        path=PurePosixPath(name)
        forbidden=path.parts[0] in {'.local','.local-work','local','.venv','node_modules','dist','data','crawl','.aws','.codex','.agents'} or name in {'.workspace.local.json','public/catalog/videos.json','config/storage.json'} or name.startswith('tests/experimental/') or (path.name.startswith('.env') and path.name!='.env.example') or path.suffix.lower() in {'.pem','.key','.jsonl','.mp4','.m4s','.m3u8','.mov','.webm','.zip','.tar','.gz'}
        data=git('show',':'+name);total+=len(data)
        if forbidden or len(data)>5*1024**2 or pattern.search(data) or any(secret in data for secret in secrets):
            failures.append(name)
    if failures:
        print('FAIL: inspect these staged paths: '+', '.join(failures))
        return 1
    print(f'PASS: {len(names)} staged files, {total} bytes; no forbidden paths or detected credentials')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
