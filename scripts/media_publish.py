"""Offline, versioned media publishing for the local VeloNexo demo."""
import argparse
import hashlib
from uuid import uuid4
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from media_storage import ROOT, digest, stores

from workspace_paths import RUNTIME, CATALOG, CONFIG, ENV_FILE

STATE = RUNTIME / 'publisher'
MEDIA = RUNTIME / 'media'
AUDIT_CONTEXT = {'action': 'catalog-update', 'reason': 'Local catalog operation', 'actor': 'local-operator'}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value)
    os.replace(tmp, path)


def valid_id(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('ID must contain only letters, digits, underscore or hyphen')
    return value


def config():
    c = read(CONFIG)
    ids = [p['id'] for p in c['providers']]
    if not ids or len(set(ids)) != len(ids) or not isinstance(c['group_size'], int) or c['group_size'] < 1:
        raise ValueError('Invalid storage configuration')
    for p in c['providers']:
        valid_id(p['id'])
        if p['type'] not in ('s3', 'hf') or p.get('project_limit_bytes', 0) <= 0:
            raise ValueError('Invalid provider or project capacity limit')
    return c


def ledger():
    return read(STATE / 'objects.json') if (STATE / 'objects.json').exists() else {}


def account(objects):
    totals = {}
    for o in objects.values():
        if o.get('deleted'):
            continue
        p = o['provider_id']
        totals[p] = totals.get(p, 0) + o['size_bytes']
    return totals


def object_id(obj):
    return obj['provider_id'] + ':' + obj['object_key']


def check_budget(objects, c, existing):
    merged = dict(existing)
    merged.update({object_id(o): o for o in objects if o['provider_id'] != 'local'})
    totals = account(merged)
    for p in c['providers']:
        if totals.get(p['id'], 0) > p['project_limit_bytes']:
            raise ValueError('Project capacity limit reached for ' + p['id'])
    return totals


def command(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def prepare(source, video_id, c, provider=None):
    valid_id(video_id)
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError('Input file not found')
    ids = [p['id'] for p in c['providers'] if p.get('enabled', True)]
    if not ids and provider != 'local':
        raise ValueError('No enabled storage provider')
    if provider and provider not in ids + ['local']:
        raise ValueError('Unknown provider')
    MEDIA.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source)
    backup = STATE / 'sources' / (source_hash + '.source')
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup.with_suffix('.tmp'))
        os.replace(backup.with_suffix('.tmp'), backup)
    with tempfile.TemporaryDirectory(prefix='.prepare-' + __import__('hashlib').sha256(video_id.encode()).hexdigest()[:16] + '-', dir=MEDIA) as temp:
        work = Path(temp)
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]))
        video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
        if not video:
            raise ValueError('No video stream')
        # Bound the long edge to 720 without stretching or upscaling; force even dimensions.
        scale = "scale=w='min(720,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1"
        command(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0?',
            '-vf', scale, '-r', '24', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '27', '-pix_fmt', 'yuv420p',
            '-g', '48', '-keyint_min', '48', '-sc_threshold', '0', '-c:a', 'aac', '-b:a', '96k',
            '-map_metadata', '-1', '-f', 'hls', '-hls_time', '2', '-hls_playlist_type', 'vod',
            '-hls_segment_type', 'fmp4', '-hls_segment_filename', 'seg_%05d.m4s', 'index.m3u8'], work)
        command(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source), '-vf', scale,
            '-frames:v', '1', '-map_metadata', '-1', 'poster.jpg'], work)
        names = ['init.mp4', 'poster.jpg']
        segments = []
        duration = None
        for line in (work / 'index.m3u8').read_text().splitlines():
            if line.startswith('#EXTINF:'):
                duration = float(line.split(':')[1].split(',')[0])
            elif line and not line.startswith('#'):
                segments.append({'file': line, 'duration': duration, 'sequence': len(segments)})
                names.append(line)
        if not segments or any(not s['duration'] or s['duration'] <= 0 for s in segments):
            raise ValueError('Invalid segment durations')
        import hashlib
        placement = {}
        for name in names:
            index = next((s['sequence'] for s in segments if s['file'] == name), 0)
            placement[name] = provider or ids[(index // c['group_size']) % len(ids)]
        revision = hashlib.sha256((''.join(digest(work / n) for n in names) + json.dumps(placement, sort_keys=True)).encode()).hexdigest()[:16]
        objects = []
        for name in names:
            selected = placement[name]
            objects.append({'file': name, 'provider_id': selected,
                'object_key': f'velonexo/{video_id}/{revision}/{name}',
                'size_bytes': (work / name).stat().st_size, 'sha256': digest(work / name)})
        m = {'schema_version': 1, 'video_id': video_id, 'revision': revision, 'created_at': now(),
            'source_sha256': source_hash, 'encoding': {'video': 'h264', 'audio': 'aac' if any(s['codec_type'] == 'audio' for s in info['streams']) else None, 'fps': 24, 'max_edge': 720},
            'duration': sum(s['duration'] for s in segments), 'init': 'init.mp4', 'poster': 'poster.jpg',
            'segments': segments, 'objects': objects, 'state': 'prepared'}
        validate_map(m)
        dest = MEDIA / video_id / revision
        if dest.exists():
            old = read(dest / 'map.json')
            # Never silently change placement for immutable version keys.
            if old['objects'] != objects:
                raise ValueError('Version already exists with another placement; choose a new ID')
            if old.get('state') == 'purged':
                shutil.rmtree(dest)
            else:
                return dest, old
        atomic(work / 'map.json', m)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(work), dest)
        return dest, m


def validate_map(m):
    valid_id(m['video_id'])
    if m.get('state') == 'purged':
        raise ValueError('Media version was purged; republish from source backup')
    if m.get('schema_version') != 1 or not re.fullmatch(r'[a-f0-9]{16}', m['revision']):
        raise ValueError('Invalid map version')
    objs = {o['file']: o for o in m['objects']}
    if len(objs) != len(m['objects']) or m['init'] not in objs or m['poster'] not in objs:
        raise ValueError('Invalid map objects')
    for name, o in objs.items():
        if Path(name).name != name or not re.fullmatch(r'[a-f0-9]{64}', o['sha256']) or o['size_bytes'] <= 0:
            raise ValueError('Invalid object metadata')
        valid_id(o['provider_id'])
        if o['object_key'] != f"velonexo/{m['video_id']}/{m['revision']}/{name}":
            raise ValueError('Invalid object key')
    if not m['segments']:
        raise ValueError('Empty segments')
    for i, s in enumerate(m['segments']):
        if s['sequence'] != i or s['file'] not in objs or not math.isfinite(s['duration']) or s['duration'] <= 0:
            raise ValueError('Invalid segment order/duration')
    if abs(sum(s['duration'] for s in m['segments']) - m['duration']) > .001:
        raise ValueError('Invalid total duration')


def compile_manifest(m, urls):
    validate_map(m)
    lines = ['#EXTM3U', '#EXT-X-VERSION:7', '#EXT-X-TARGETDURATION:' + str(math.ceil(max(s['duration'] for s in m['segments']))),
        '#EXT-X-MEDIA-SEQUENCE:0', '#EXT-X-PLAYLIST-TYPE:VOD', '#EXT-X-MAP:URI="' + urls[m['init']] + '"']
    for s in m['segments']:
        lines += [f"#EXTINF:{s['duration']:.6f},", urls[s['file']]]
    return '\n'.join(lines + ['#EXT-X-ENDLIST', ''])


def refresh(dest, m, adapters, verify=True):
    validate_map(m)
    bindings = m.get('storage_bindings', {})
    for provider_id, identity in bindings.items():
        if provider_id not in adapters or adapters[provider_id].identity() != identity:
            raise ValueError('Provider target changed; use a new provider ID instead of repointing existing maps')
    urls, report = {}, []
    for o in m['objects']:
        if o['provider_id'] == 'local':
            if digest(dest / o['file']) != o['sha256']:
                raise ValueError('Local integrity mismatch')
            urls[o['file']] = f"/local-media/{m['video_id']}/{m['revision']}/{o['file']}"
        else:
            store = adapters[o['provider_id']]
            if verify:
                report.append({'file': o['file'], 'provider_id': o['provider_id'], **store.verify(o)})
            urls[o['file']] = store.url(o['object_key'])
    atomic(dest / 'play.m3u8', compile_manifest(m, urls))
    atomic(dest / 'verification.json', {'checked_at': now(), 'objects': report})
    m['storage_bindings'] = {pid: adapters[pid].identity() for pid in {o['provider_id'] for o in m['objects']} if pid != 'local'}
    m['refreshed_at'] = now()
    m['expires_in_seconds'] = 3600 if any('X-Amz-Signature=' in url for url in urls.values()) else None
    m['state'] = 'verified'
    atomic(dest / 'map.json', m)


def catalog_hash(c):
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save_catalog(c):
    validate_catalog(c)
    before = read(CATALOG) if CATALOG.exists() else {'schema_version': 1, 'videos': []}
    events_dir = STATE / 'events'
    # Recover interrupted journal finalization before the next catalog mutation.
    for path in events_dir.glob('*.json'):
        event = read(path)
        if event.get('state') == 'prepared' and event.get('after_hash') == catalog_hash(before):
            event['state'] = 'applied'
            atomic(path, event)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    if CATALOG.exists():
        atomic(STATE / 'backups' / (stamp + '.json'), before)
    old = {v['id']: v for v in before['videos']}
    new = {v['id']: v for v in c['videos']}
    event = {**AUDIT_CONTEXT, 'id': stamp + '-' + uuid4().hex, 'at': now(), 'state': 'prepared',
             'before_hash': catalog_hash(before), 'after_hash': catalog_hash(c),
             'metadata_before': {k:v for k,v in before.items() if k!='videos'},
             'metadata_after': {k:v for k,v in c.items() if k!='videos'},
             'changes': [{'id': key, 'before': old.get(key), 'after': new.get(key)}
                         for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key)]}
    event_path = events_dir / (event['id'] + '.json')
    atomic(event_path, event)
    atomic(CATALOG, c)
    event['state'] = 'applied'
    atomic(event_path, event)


def validate_catalog(c):
    if c.get('schema_version') != 1 or not isinstance(c.get('videos'), list):
        raise ValueError('Invalid catalog')
    taxonomy = c.get('taxonomy', {})
    if not isinstance(taxonomy, dict) or any(not isinstance(names,list) or any(not isinstance(n,str) or not n.strip() or len(n)>80 for n in names) or len(set(names))!=len(names) for names in taxonomy.values()):
        raise ValueError('Invalid taxonomy')
    ids = set()
    for v in c['videos']:
        valid_id(v['id'])
        if v['id'] in ids or not isinstance(v.get('title'), str) or not v['title'].strip() or not isinstance(v.get('creator'), str):
            raise ValueError('Invalid/duplicate catalog entry')
        ids.add(v['id'])
        if v.get('visibility') not in ('published', 'draft', 'removed') or not isinstance(v.get('tags'), list) or not all(isinstance(t,str) for t in v['tags']):
            raise ValueError('Invalid entry state/tags')
        datetime.fromisoformat(v['published_at'].replace('Z', '+00:00'))
        s = v['source']
        from urllib.parse import urlparse
        value = s.get('playlist') if s.get('kind') == 'native' and s.get('format') == 'hls' else s.get('url') if s.get('kind') == 'external' else None
        if not isinstance(value,str):
            raise ValueError('Invalid source')
        u = urlparse(value)
        if not ((s['kind']=='native' and value.startswith('/') and not value.startswith('//') and '\\' not in value) or (u.scheme=='https' and u.netloc and not u.username and not u.password)):
            raise ValueError('Invalid source URL')
    editorial = c.get('editorial', {'featured': [], 'topics': []})
    if not isinstance(editorial,dict) or not isinstance(editorial.get('featured'),list) or not isinstance(editorial.get('topics'),list):
        raise ValueError('Invalid editorial config')
    groups = [editorial['featured']]
    topic_ids = set()
    for topic in editorial['topics']:
        if not isinstance(topic,dict) or not isinstance(topic.get('title'),str) or not topic['title'].strip() or len(topic['title'])>100:
            raise ValueError('Invalid topic')
        valid_id(topic.get('id',''))
        if topic['id'] in topic_ids:
            raise ValueError('Duplicate topic')
        topic_ids.add(topic['id'])
        groups.append(topic.get('ids'))
    for group in groups:
        if not isinstance(group,list) or any(not isinstance(i,str) or i not in ids for i in group) or len(group)!=len(set(group)):
            raise ValueError('Invalid editorial references')



def publish(args):
    if not args.title.strip() or len(args.title) > 300:
        raise ValueError('Title must contain 1..300 characters')
    print('STAGE prepare', flush=True)
    c = config()
    dest, m = prepare(args.input, args.id, c, args.provider)
    pending = [o for o in m['objects'] if o['provider_id'] != 'local']
    existing = ledger()
    print(json.dumps({'project_bytes_after': check_budget(pending, c, existing), 'new_bytes': sum(o['size_bytes'] for o in pending if object_id(o) not in existing)}, ensure_ascii=False))
    if args.dry_run:
        return
    adapters = stores(c) if pending else {}
    bindings = {p: adapters[p].identity() for p in {o['provider_id'] for o in pending}}
    if m.get('storage_bindings') and m['storage_bindings'] != bindings:
        raise ValueError('Provider target changed for existing media version')
    m['storage_bindings'] = bindings
    atomic(dest / 'map.json', m)
    print('STAGE upload', flush=True)
    for o in pending:
        # Journal before upload: failed attempts count conservatively until explicitly purged.
        existing[object_id(o)] = {**o, 'recorded_at': now(), 'status': 'pending'}
        atomic(STATE / 'objects.json', existing)
        adapters[o['provider_id']].upload(dest / o['file'], o['object_key'])
        existing[object_id(o)]['status'] = 'uploaded'
        atomic(STATE / 'objects.json', existing)
    print('STAGE verify', flush=True)
    refresh(dest, m, adapters)
    print('STAGE catalog', flush=True)
    catalog = read(CATALOG)
    entry = {'id': args.id, 'title': args.title, 'creator': args.creator, 'visibility': 'draft' if getattr(args,'draft',False) else 'published',
        'source': {'kind': 'native', 'format': 'hls', 'playlist': f'/local-media/{args.id}/{m["revision"]}/play.m3u8',
            'media_map': f'/local-media/{args.id}/{m["revision"]}/map.json'},
        'poster': f'/local-media/{args.id}/{m["revision"]}/poster.jpg',
        'has_audio': m['encoding']['audio'] is not None, 'category': args.category,
        'published_at': now(), 'tags': args.tag or []}
    catalog['videos'] = [v for v in catalog['videos'] if v['id'] != args.id] + [entry]
    save_catalog(catalog)
    print(('Draft prepared ' if getattr(args, 'draft', False) else 'Published ') + args.id)


def find_map(video_id):
    entry = next(v for v in read(CATALOG)['videos'] if v['id'] == video_id)
    value = entry['source'].get('media_map', '')
    if not re.fullmatch(r'/local-media/[A-Za-z0-9_-]+/[a-f0-9]{16}/map.json', value):
        raise ValueError('Entry has no publisher map')
    dest = MEDIA / Path(value).parts[-3] / Path(value).parts[-2]
    m = read(dest / 'map.json')
    validate_map(m)
    if m['video_id'] != video_id:
        raise ValueError('Mismatched map')
    return dest, m


def bulk_state(ids, action):
    if action not in ('publish', 'withdraw') or not ids or len(ids)>50 or len(set(ids)) != len(ids):
        raise ValueError('Invalid batch')
    c = read(CATALOG)
    entries = []
    for video_id in ids:
        valid_id(video_id)
        entry = next((v for v in c['videos'] if v['id']==video_id and v['source']['kind']=='native'), None)
        if not entry:
            raise ValueError('Batch entry not found')
        entries.append(entry)
    if action == 'publish':
        for entry in entries:
            dest, media = find_map(entry['id'])
            refresh(dest, media, stores(config()) if any(o['provider_id']!='local' for o in media['objects']) else {})
    for entry in entries:
        entry['visibility'] = 'published' if action=='publish' else 'removed'
    save_catalog(c)
    print('Batch catalog update complete')


def probe_provider(provider_id):
    import uuid
    c = config()
    selected = next((p for p in c['providers'] if p['id']==provider_id), None)
    if not selected:
        raise ValueError('Unknown provider')
    results_file = STATE/'probes.json'
    results = read(results_file) if results_file.exists() else {}
    result = {'checked_at': now(), 'success': False}
    try:
        adapter = stores({**c, 'providers':[selected]})[provider_id]
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp)/'probe.txt';file.write_bytes(b'VeloNexo connection test data 0123456789')
            key = '_connection-test/studio-' + str(uuid.uuid4()) + '.txt'
            try:
                adapter.upload(file,key)
                report = adapter.verify({'file':file.name,'object_key':key,'sha256':digest(file),'size_bytes':file.stat().st_size})
            finally:
                adapter.delete(key)
            result.update(success=True, checks=report)
    except Exception as error:
        result['error'] = failure_code(error)
        raise
    finally:
        results[provider_id] = result
        atomic(results_file, results)
    print('Provider connection verified and test object deleted')


def cleanup_unpublished(video_id):
    valid_id(video_id)
    if any(v['id'] == video_id for v in read(CATALOG)['videos']):
        raise ValueError('Catalog entry exists; unpublished cleanup refused')
    folder = MEDIA / video_id
    records = ledger()
    adapters = None
    for file in sorted(folder.glob('*/map.json')):
        media = read(file)
        if media.get('state') == 'purged':
            continue
        validate_map(media)
        if media['video_id'] != video_id:
            raise ValueError('Cleanup map ID mismatch')
        for obj in media['objects']:
            if obj['provider_id'] == 'local' or object_id(obj) not in records or records.get(object_id(obj), {}).get('deleted'):
                continue
            if adapters is None:
                adapters = stores(config())
            store = adapters[obj['provider_id']]
            if media.get('storage_bindings', {}).get(obj['provider_id']) != store.identity():
                raise ValueError('Provider target changed; cleanup refused')
            store.delete(obj['object_key'])
            records[object_id(obj)] = {**obj, 'deleted': True}
            atomic(STATE / 'objects.json', records)
        media['state'] = 'purged'
        atomic(file, media)
    # Refuse to silently abandon unaccounted remote objects.
    if any(not o.get('deleted') and o['object_key'].startswith('velonexo/' + video_id + '/') for o in records.values()):
        raise ValueError('Unmapped remote objects remain; cleanup refused')
    if folder.exists():
        shutil.rmtree(folder)
    prefix = '.prepare-' + __import__('hashlib').sha256(video_id.encode()).hexdigest()[:16] + '-'
    for temp in MEDIA.glob(prefix + '*'):
        if temp.is_dir():
            shutil.rmtree(temp)
    print('Unpublished working files cleaned; original backups retained')


def failure_code(error):
    if isinstance(error, BlockingIOError): return 'busy'
    if isinstance(error, subprocess.CalledProcessError): return 'invalid-media'
    if isinstance(error, FileNotFoundError): return 'missing-file-or-tool'
    if isinstance(error, TimeoutError): return 'network-error'
    if isinstance(error, ValueError):
        message = str(error)
        if 'capacity limit' in message: return 'capacity-limit'
        if 'Provider target changed' in message: return 'provider-changed'
        if 'integrity' in message.lower(): return 'integrity-error'
        return 'validation-error'
    response = getattr(error, 'response', None)
    status = response.get('ResponseMetadata', {}).get('HTTPStatusCode') if isinstance(response, dict) else getattr(response, 'status_code', None)
    status = status or getattr(error, 'code', None)
    if status in (401, 403): return 'storage-permission'
    if status == 404: return 'source-missing'
    return 'storage-or-network-error'


def editorial_update(value):
    c = read(CATALOG)
    editorial = c.setdefault('editorial', {'featured': [], 'topics': []})
    known = {v['id'] for v in c['videos']}
    ids = value.get('ids', [])
    if not isinstance(ids,list) or len(ids)>100 or any(not isinstance(i,str) or i not in known for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Invalid editorial members')
    if value.get('action') == 'featured':
        editorial['featured'] = ids
    elif value.get('action') in ('topic','delete-topic'):
        topic_id = valid_id(value.get('id',''))
        topics = [t for t in editorial.get('topics',[]) if t['id']!=topic_id]
        if value['action']=='topic':
            title = value.get('title','').strip()
            if not title or len(title)>100:
                raise ValueError('Invalid topic title')
            topics.append({'id':topic_id,'title':title,'ids':ids})
        editorial['topics'] = topics
    else:
        raise ValueError('Invalid editorial action')
    save_catalog(c)
    print('Editorial selections saved')


def taxonomy_update(kind, source=None, target=None, order=None):
    c = read(CATALOG)
    field = 'category' if kind == 'category' else 'tags'
    values = {v.get('category', 'prueba') for v in c['videos']} if kind == 'category' else {t for v in c['videos'] for t in v['tags']}
    key = 'categories' if kind == 'category' else 'tags'
    current = c.setdefault('taxonomy', {}).get(key, [])
    names = list(dict.fromkeys([*current, *sorted(values)]))
    if order is not None:
        if len(order) != len(set(order)) or set(order) != set(names):
            raise ValueError('Order must include all names exactly once')
        names = order
    else:
        if source not in names or not target or not target.strip() or len(target)>80:
            raise ValueError('Invalid taxonomy rename')
        target = target.strip()
        for v in c['videos']:
            if kind == 'category' and v.get(field, 'prueba') == source:
                v[field] = target
            elif kind == 'tag':
                v[field] = list(dict.fromkeys(target if t == source else t for t in v[field]))
        names = list(dict.fromkeys(target if n == source else n for n in names))
    c['taxonomy'][key] = names
    save_catalog(c)
    print('Taxonomy updated atomically')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reason', default=os.environ.get('VELONEXO_AUDIT_REASON', 'Local CLI operation'))
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('publish')
    for name in ('input', 'id', 'title'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--creator', default='@velonexo')
    p.add_argument('--category', default='prueba')
    p.add_argument('--tag', action='append')
    p.add_argument('--provider', help='Provider ID or local; omit for configured segment groups')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--draft', action='store_true')
    edit = sub.add_parser('edit')
    edit.add_argument('id')
    edit.add_argument('--title', required=True)
    edit.add_argument('--creator', required=True)
    edit.add_argument('--category', required=True)
    edit.add_argument('--tag', action='append', default=[])
    for name in ('refresh', 'withdraw', 'restore-entry', 'purge'):
        sub.add_parser(name).add_argument('id')
    batch = sub.add_parser('bulk-state')
    batch.add_argument('--action', choices=['publish','withdraw'], required=True)
    batch.add_argument('ids', nargs='+')
    sub.add_parser('probe-provider').add_argument('id')
    toggle = sub.add_parser('set-provider')
    toggle.add_argument('id')
    toggle.add_argument('--enabled', choices=['true','false'], required=True)
    sub.add_parser('cleanup-unpublished').add_argument('id')
    sub.add_parser('editorial').add_argument('--value-json',required=True)
    taxonomy = sub.add_parser('taxonomy')
    taxonomy.add_argument('--kind', choices=['category','tag'], required=True)
    taxonomy.add_argument('--source')
    taxonomy.add_argument('--target')
    taxonomy.add_argument('--order', nargs='*')
    taxonomy.add_argument('--order-json')
    migration=sub.add_parser('migrate')
    migration.add_argument('--provider',required=True)
    migration.add_argument('--apply',action='store_true')
    migration.add_argument('ids',nargs='+')
    sub.add_parser('versions')
    sub.add_parser('clean-versions').add_argument('versions',nargs='+')
    sub.add_parser('usage')
    sub.add_parser('validate')
    sub.add_parser('restore-catalog').add_argument('backup')
    args = parser.parse_args()
    if not args.reason.strip() or len(args.reason)>300:
        parser.error('Reason must contain 1..300 characters')
    AUDIT_CONTEXT.update(action=args.command, reason=args.reason.strip())
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / 'lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.command == 'publish':
                publish(args)
            elif args.command == 'probe-provider':
                probe_provider(args.id)
            elif args.command == 'set-provider':
                c = config()
                provider = next((p for p in c['providers'] if p['id']==args.id), None)
                if not provider:
                    raise ValueError('Unknown provider')
                provider['enabled'] = args.enabled == 'true'
                atomic(CONFIG, c)
                print('Upload placement setting saved; existing media mappings unchanged')
            elif args.command == 'bulk-state':
                bulk_state(args.ids, args.action)
            elif args.command == 'cleanup-unpublished':
                cleanup_unpublished(args.id)
            elif args.command == 'edit':
                if not args.title.strip() or len(args.title)>300:
                    raise ValueError('Title must contain 1..300 characters')
                c = read(CATALOG)
                entry = next(v for v in c['videos'] if v['id']==args.id)
                entry.update(title=args.title.strip(), creator=args.creator, category=args.category, tags=args.tag)
                save_catalog(c)
                print('Metadata saved')
            elif args.command == 'editorial':
                editorial_update(json.loads(args.value_json))
            elif args.command == 'taxonomy':
                taxonomy_update(args.kind,args.source,args.target,json.loads(args.order_json) if args.order_json is not None else args.order)
            elif args.command in ('migrate','versions','clean-versions'):
                import media_maintenance as maintenance
                # The executable module is __main__; share its locked state and audit context.
                maintenance.m = sys.modules[__name__]
                result = maintenance.migrate(args.ids,args.provider,args.apply) if args.command=='migrate' else maintenance.versions() if args.command=='versions' else maintenance.clean_versions(args.versions)
                print(json.dumps(result,ensure_ascii=False))
            elif args.command == 'usage':
                print(json.dumps({'scope': 'project journal only; not account billing; excludes old smoke uploads', 'bytes': account(ledger())}, indent=2))
            elif args.command == 'validate':
                validate_catalog(read(CATALOG))
                for v in read(CATALOG)['videos']:
                    if v['visibility'] == 'published' and v['source'].get('media_map'):
                        find_map(v['id'])
                print('Catalog and referenced maps valid')
            elif args.command == 'restore-catalog':
                candidate = read(Path(args.backup))
                validate_catalog(candidate)
                for entry in candidate['videos']:
                    if entry['visibility'] == 'published' and entry['source'].get('media_map'):
                        path = entry['source']['media_map']
                        if not re.fullmatch(r'/local-media/[A-Za-z0-9_-]+/[a-f0-9]{16}/map.json', path):
                            raise ValueError('Invalid restore map path')
                        dest = MEDIA / Path(path).parts[-3] / Path(path).parts[-2]
                        media = read(dest / 'map.json')
                        if media['video_id'] != entry['id']:
                            raise ValueError('Restore map ID mismatch')
                        refresh(dest, media, stores(config()) if any(o['provider_id'] != 'local' for o in media['objects']) else {})
                save_catalog(candidate)
                print('Catalog restored; media URLs may require refresh')
            elif args.command in ('withdraw', 'restore-entry'):
                c = read(CATALOG)
                entry = next(v for v in c['videos'] if v['id'] == args.id)
                if args.command == 'restore-entry':
                    dest, m = find_map(args.id)
                    refresh(dest, m, stores(config()) if any(o['provider_id']!='local' for o in m['objects']) else {})
                entry['visibility'] = 'removed' if args.command == 'withdraw' else 'published'
                save_catalog(c)
                print('Entry hidden; source objects remain accessible until purge' if args.command=='withdraw' else 'Entry restored')
            elif args.command in ('refresh', 'purge'):
                dest, m = find_map(args.id)
                adapters = stores(config()) if any(o['provider_id']!='local' for o in m['objects']) else {}
                if args.command == 'refresh':
                    refresh(dest, m, adapters)
                    print('Manifest refreshed without upload')
                else:
                    entry = next(v for v in read(CATALOG)['videos'] if v['id']==args.id)
                    if entry['visibility']=='published':
                        raise ValueError('Withdraw before purge')
                    records=ledger()
                    for o in m['objects']:
                        if o['provider_id']!='local' and not records.get(object_id(o),{}).get('deleted'):
                            adapters[o['provider_id']].delete(o['object_key'])
                            records[object_id(o)]={**o,'deleted':True}
                            atomic(STATE/'objects.json',records)
                        (dest/o['file']).unlink(missing_ok=True)
                    (dest/'play.m3u8').unlink(missing_ok=True)
                    m['state']='purged';atomic(dest/'map.json',m)
                    print('Current version purged; cached copies and older versions require separate handling')
            return 0
        except Exception as error:
            print('ERROR_CODE ' + failure_code(error), file=sys.stderr, flush=True)
            # Raw SDK/HTTP errors can contain secrets and signed URLs.
            print('FAILED: ' + type(error).__name__ + (': ' + str(error) if isinstance(error, ValueError) else ''), file=sys.stderr)
            return 1


if __name__ == '__main__':
    sys.exit(main())
