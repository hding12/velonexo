"""Build a standalone public package from already-published, verified media."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import tempfile
import media_publish as m
from storage_probe import dotenv_values

OUTPUT = m.RUNTIME / 'static-site'


def export(output=OUTPUT):
    if any((m.ROOT / 'dist/assets').glob('Studio-*')):
        raise ValueError('Run npm run build:static before exporting')
    catalog = m.read(m.CATALOG)
    m.validate_catalog(catalog)
    catalog['videos'] = [v for v in catalog['videos'] if v['visibility'] == 'published']
    if 'editorial' in catalog:
        published = {v['id'] for v in catalog['videos']}
        catalog['editorial']['featured'] = [i for i in catalog['editorial']['featured'] if i in published]
        for topic in catalog['editorial']['topics']:
            topic['ids'] = [i for i in topic['ids'] if i in published]
    stage = Path(tempfile.mkdtemp(prefix='static-export-', dir=m.RUNTIME))
    try:
        shutil.copy2(m.ROOT / 'dist/index.html', stage / 'index.html')
        shutil.copytree(m.ROOT / 'dist/assets', stage / 'assets')
        for entry in catalog['videos']:
            if entry['source']['kind'] != 'native':
                continue
            dest, media = m.find_map(entry['id'])
            m.validate_map(media)
            if media.get('state') == 'purged':
                raise ValueError('Cannot export purged media')
            playlist = (dest / 'play.m3u8').read_text()
            if 'x-amz-' in playlist.lower() or media.get('expires_in_seconds'):
                raise ValueError('Static export requires non-expiring public media URLs')
            # Current publisher emits only plain fMP4 VOD playlists.
            if not playlist.startswith('#EXTM3U') or '#EXT-X-ENDLIST' not in playlist:
                raise ValueError('Invalid playback manifest')
            target = stage / 'local-media' / media['video_id'] / media['revision']
            target.mkdir(parents=True)
            for obj in media['objects']:
                if obj['provider_id'] == 'local' or obj['file'] == media['poster']:
                    source = dest / obj['file']
                    if m.digest(source) != obj['sha256']:
                        raise ValueError('Export integrity mismatch')
                    shutil.copy2(source, target / obj['file'])
            (target / 'play.m3u8').write_text(playlist)
            public_map = {k: media[k] for k in ('schema_version', 'video_id', 'revision', 'init', 'poster', 'segments', 'objects', 'duration')}
            m.atomic(target / 'map.json', public_map)
            # Directory indexes allow detail URLs on a plain static HTTP server.
            page = stage / 'video' / entry['id']
            page.mkdir(parents=True)
            shutil.copy2(stage / 'index.html', page / 'index.html')
        m.atomic(stage / 'catalog/videos.json', catalog)
        (stage / 'explore').mkdir()
        shutil.copy2(stage / 'index.html', stage / 'explore/index.html')
        (stage / '_redirects').write_text('/* /index.html 200\n')
        (stage / '_headers').write_text('/local-media/*\n  Access-Control-Allow-Origin: *\n  X-Content-Type-Options: nosniff\n')
        secrets = [v.encode() for k, v in dotenv_values(m.ENV_FILE).items() if v and len(v)>6 and any(t in k for t in ('TOKEN','SECRET','ACCESS_KEY'))]
        for file in stage.rglob('*'):
            if file.is_file():
                data = file.read_bytes()
                if any(secret in data for secret in secrets) or b'x-amz-signature=' in data.lower():
                    raise ValueError('Sensitive content in static package')
        old = output.with_name(output.name + '.previous')
        if old.exists():
            shutil.rmtree(old)
        if output.exists():
            os.replace(output, old)
        try:
            os.replace(stage, output)
        except Exception:
            if old.exists():
                os.replace(old, output)
            raise
        print(json.dumps({'output': str(output), 'published': len(catalog['videos']), 'files': sum(p.is_file() for p in output.rglob('*'))}))
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    with open(m.STATE / 'lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        export()


if __name__ == '__main__':
    main()
