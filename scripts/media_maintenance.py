"""Batch migration and conservative unused-version cleanup, under publisher lock."""
import re
import media_publish as m


def migrate(ids, provider, apply=False):
    if not ids or len(ids)>50 or len(ids)!=len(set(ids)):
        raise ValueError('Select 1..50 unique videos')
    catalog=m.read(m.CATALOG);config=m.config();prepared=[]
    for video_id in ids:
        entry=next((v for v in catalog['videos'] if v['id']==video_id and v['source']['kind']=='native'),None)
        if not entry:raise ValueError('Unknown native video')
        _,old=m.find_map(video_id)
        source=m.STATE/'sources'/(old['source_sha256']+'.source')
        if not source.exists() or m.digest(source)!=old['source_sha256']:
            raise ValueError('Verified source backup required for migration')
        dest,media=m.prepare(source,video_id,config,provider)
        prepared.append((entry,dest,media))
    objects=[o for _,_,media in prepared for o in media['objects'] if o['provider_id']!='local']
    records=m.ledger();usage=m.check_budget(objects,config,records)
    plan={'videos':[{'id':e['id'],'revision':v['revision']} for e,_,v in prepared],'target':provider,'project_bytes_after':usage,'apply':apply}
    if not apply:return plan
    adapters=m.stores(config) if objects else {}
    for entry,dest,media in prepared:
        bindings={pid:adapters[pid].identity() for pid in {o['provider_id'] for o in media['objects']} if pid!='local'}
        if media.get('storage_bindings') and media['storage_bindings']!=bindings:
            raise ValueError('Provider target changed')
        media['storage_bindings']=bindings;m.atomic(dest/'map.json',media)
        for obj in media['objects']:
            if obj['provider_id']=='local':continue
            key=m.object_id(obj)
            if records.get(key,{}).get('status')!='uploaded' or records.get(key,{}).get('deleted'):
                records[key]={**obj,'status':'pending','recorded_at':m.now()};m.atomic(m.STATE/'objects.json',records)
                adapters[obj['provider_id']].upload(dest/obj['file'],obj['object_key'])
                records[key]['status']='uploaded';m.atomic(m.STATE/'objects.json',records)
        m.refresh(dest,media,adapters)
    # No catalog mutation until every selected video has passed verification.
    for entry,_,media in prepared:
        base=f"/local-media/{entry['id']}/{media['revision']}"
        entry['source']={**entry['source'],'playlist':base+'/play.m3u8','media_map':base+'/map.json'}
        entry['poster']=base+'/'+media['poster']
    m.save_catalog(catalog)
    return plan


def protected_versions():
    protected=set()
    for file in [m.CATALOG,*(m.STATE/'backups').glob('*.json')]:
        catalog=m.read(file);m.validate_catalog(catalog)
        for entry in catalog['videos']:
            if entry['source']['kind']!='native':continue
            ref=entry['source'].get('media_map','')
            if not ref:
                playlist=entry['source'].get('playlist','')
                if not playlist.startswith('/local-media/'):continue
                ref=playlist.removesuffix('play.m3u8')+'map.json'
            match=re.fullmatch(r'/local-media/([A-Za-z0-9_-]+)/([a-f0-9]{16})/map.json',ref)
            if not match:raise ValueError('Unrecognized reference; cleanup refused')
            protected.add('/'.join(match.groups()))
    return protected


def versions():
    protected=protected_versions();result=[]
    for path in sorted(m.MEDIA.glob('*/*/map.json')):
        media=m.read(path)
        if media.get('state')=='purged':continue
        m.validate_map(media)
        key=media['video_id']+'/'+media['revision']
        if path.parent!=m.MEDIA/key:raise ValueError('Map path mismatch')
        result.append({'version':key,'protected':key in protected,'bytes':sum(o['size_bytes'] for o in media['objects'])})
    return result


def clean_versions(selected):
    candidates={v['version']:v for v in versions()}
    if not selected or len(selected)!=len(set(selected)):
        raise ValueError('Select unique versions')
    for key in selected:
        if key in candidates:
            if candidates[key]['protected']:raise ValueError('Referenced version; cleanup refused')
        else:
            if not re.fullmatch(r'[A-Za-z0-9_-]+/[a-f0-9]{16}',key):raise ValueError('Invalid version')
            file=m.MEDIA/key/'map.json'
            if not file.is_file():raise ValueError('Unknown version')
            tombstone=m.read(file)
            if tombstone.get('state')!='purged' or key!=tombstone.get('video_id','')+'/'+tombstone.get('revision',''):
                raise ValueError('Unknown version')
    records=m.ledger();adapters=None
    for key in selected:
        dest=m.MEDIA/key;media=m.read(dest/'map.json')
        if media.get('state')=='purged':continue
        for obj in media['objects']:
            if obj['provider_id']!='local':
                oid=m.object_id(obj)
                if oid in records and not records[oid].get('deleted'):
                    if adapters is None:adapters=m.stores(m.config())
                    store=adapters[obj['provider_id']]
                    if store.identity()!=media.get('storage_bindings',{}).get(obj['provider_id']):
                        raise ValueError('Provider target changed; cleanup refused')
                    store.delete(obj['object_key'])
                    records[oid]={**obj,'deleted':True};m.atomic(m.STATE/'objects.json',records)
            (dest/obj['file']).unlink(missing_ok=True)
        (dest/'play.m3u8').unlink(missing_ok=True)
        media['state']='purged';media['purged_at']=m.now();m.atomic(dest/'map.json',media)
    return {'cleaned':selected,'originals_retained':True}
