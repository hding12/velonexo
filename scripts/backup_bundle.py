"""Checksummed, secret-free portable backup; restore only into a new directory."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile
import media_publish as m
from storage_probe import dotenv_values


def safe_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts or str(p) != name:
        raise ValueError('Unsafe backup member')
    return p


def create(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Backup output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog = m.read(m.CATALOG)
    m.validate_catalog(catalog)
    with tempfile.TemporaryDirectory(prefix='velonexo-backup-') as temporary:
        stage = Path(temporary)
        def copy(source, name=None):
            if source.is_symlink() or not source.is_file():
                raise ValueError('Backup requires regular files')
            target = stage / (name or source.relative_to(m.ROOT))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for folder in ('src','server','scripts','docs','tests'):
            for source in (m.ROOT / folder).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts:
                    copy(source)
        for name in ('package.json','package-lock.json','tsconfig.json','vite.config.js','index.html','README.md','DESIGN.md','.gitignore'):
            if (m.ROOT/name).exists():
                copy(m.ROOT/name)
        # Provider configs contain env-variable references, never credential values.
        m.atomic(stage/'config/storage.json',m.config())
        m.atomic(stage/'public/catalog/videos.json',catalog)
        for source in (m.STATE/'sources').glob('*.source'):
            if m.digest(source)!=source.stem:
                raise ValueError('Original backup hash mismatch')
            copy(source)
        for source in [m.STATE/'objects.json',*(m.STATE/'events').glob('*.json'),*(m.STATE/'backups').glob('*.json')]:
            if source.exists():
                copy(source)
        versions=0
        for source in m.MEDIA.glob('*/*/map.json'):
            media=m.read(source)
            if media.get('state')=='purged':
                copy(source)
                continue
            m.validate_map(media)
            if source.parent != m.MEDIA/media['video_id']/media['revision']:
                raise ValueError('Media map location mismatch')
            original=m.STATE/'sources'/(media['source_sha256']+'.source')
            if not original.exists():
                raise ValueError('Original backup missing')
            target=stage/source.parent.relative_to(m.ROOT)
            for obj in media['objects']:
                local=source.parent/obj['file']
                if not local.is_file() or m.digest(local)!=obj['sha256']:
                    raise ValueError('Local media copy missing or corrupt; restore/download it before backup')
                copy(local)
            urls={o['file']:f"/local-media/{media['video_id']}/{media['revision']}/{o['file']}" for o in media['objects']}
            # Offline recovery uses bundled bytes; original placement stays recorded.
            media['recovery_playback']='local-copy'
            media['expires_in_seconds']=None
            m.atomic(target/'map.json',media)
            m.atomic(target/'play.m3u8',m.compile_manifest(media,urls))
            versions+=1
        for entry in catalog['videos']:
            if entry['source']['kind']=='native':
                rel=entry['source'].get('media_map','').removeprefix('/local-media/')
                if not (stage/'.local/media'/rel).is_file():
                    raise ValueError('Catalog references an unavailable version')
        values=dotenv_values(m.ROOT/'.env.local')
        secrets=[v.encode() for k,v in values.items() if v and len(v)>6 and any(t in k for t in ('TOKEN','SECRET','ACCESS_KEY'))]
        manifest={}
        for file in sorted(stage.rglob('*')):
            if file.is_file():
                data=file.read_bytes()
                if any(secret in data for secret in secrets):
                    raise ValueError('Credential value found in backup payload')
                manifest[file.relative_to(stage).as_posix()]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        info={'schema_version':1,'created_at':m.now(),'files':manifest,'versions':versions,'credentials_included':False}
        partial=output.with_name(output.name+'.partial')
        try:
            with zipfile.ZipFile(partial,'x',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('backup-manifest.json',json.dumps(info))
                for name in manifest:
                    archive.write(stage/name,name)
            os.replace(partial,output)
        finally:
            partial.unlink(missing_ok=True)
        return info


def restore(archive_path,destination):
    destination=Path(destination).resolve()
    if destination.exists():
        raise ValueError('Restore destination must not exist; live overwrite is refused')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='restore-',dir=destination.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries=archive.infolist();names=[i.filename for i in entries]
            if len(names)!=len(set(names)) or sum(i.file_size for i in entries)>10*1024**3:
                raise ValueError('Duplicate members or backup too large')
            for name in names:
                safe_name(name)
            info=json.loads(archive.read('backup-manifest.json'))
            if info.get('schema_version')!=1 or set(names)!=set(info['files'])|{'backup-manifest.json'}:
                raise ValueError('Backup inventory mismatch')
            for name,expected in info['files'].items():
                target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();size=0
                with archive.open(name) as src,open(target,'xb') as dst:
                    while True:
                        chunk=src.read(1024*1024)
                        if not chunk:break
                        h.update(chunk);size+=len(chunk);dst.write(chunk)
                if h.hexdigest()!=expected['sha256'] or size!=expected['bytes']:
                    raise ValueError('Backup integrity mismatch')
        m.validate_catalog(m.read(stage/'public/catalog/videos.json'))
        for file in (stage/'.local/media').glob('*/*/map.json'):
            media=m.read(file)
            if media.get('state')=='purged':continue
            m.validate_map(media)
            for obj in media['objects']:
                if m.digest(file.parent/obj['file'])!=obj['sha256']:
                    raise ValueError('Restored media hash mismatch')
        os.replace(stage,destination)
        return info
    finally:
        if stage.exists():shutil.rmtree(stage)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('create');p.add_argument('--output',required=True)
    p=sub.add_parser('restore');p.add_argument('--archive',required=True);p.add_argument('--destination',required=True)
    args=parser.parse_args()
    if args.command=='create':
        with open(m.STATE/'lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            info=create(args.output)
    else:
        info=restore(args.archive,args.destination)
    print(json.dumps({'command':args.command,'files':len(info['files']),'versions':info['versions'],'credentials_included':False}))

if __name__=='__main__':main()
