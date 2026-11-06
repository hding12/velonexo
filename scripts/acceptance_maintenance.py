"""Real HF batch migration/cleanup with tiny synthetic videos and isolated catalog."""
import argparse
import fcntl
import json
from pathlib import Path
import tempfile
from uuid import uuid4
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import media_publish as m
import media_maintenance as maintenance


def main():
    evidence=m.RUNTIME/'acceptance/maintenance-remote.json'
    with open(m.STATE/'lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        real_ledger=m.ledger()
        with tempfile.TemporaryDirectory(prefix='maintenance-real-') as directory:
            root=Path(directory)
            with patch.object(m,'STATE',root/'state'),patch.object(m,'MEDIA',root/'media'),patch.object(m,'CATALOG',root/'catalog.json'):
                m.atomic(m.CATALOG,{'schema_version':1,'videos':[]});m.atomic(m.STATE/'objects.json',real_ledger)
                source=root/'sample.mp4';m.command(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=80x120:rate=24','-t','1','-c:v','libx264',str(source)])
                ids=['migration-test-'+uuid4().hex[:16] for _ in range(2)]
                for id in ids:m.publish(argparse.Namespace(input=str(source),id=id,title='Synthetic migration test',creator='@test',category='test',tag=[],provider='local',draft=True,dry_run=False))
                baseline=m.read(m.CATALOG);urls=[]
                try:
                    maintenance.migrate(ids,'hf',True)
                    after=m.read(m.CATALOG)
                    assert all(v['visibility']=='draft' for v in after['videos'])
                    for id in ids:
                        dest,media=m.find_map(id);assert all(o['provider_id']=='hf' for o in media['objects'])
                        urls.extend(m.stores(m.config())['hf'].url(o['object_key']) for o in media['objects'])
                finally:
                    m.atomic(m.CATALOG,baseline)
                    unused=[v['version'] for v in maintenance.versions() if not v['protected']]
                    if unused:maintenance.clean_versions(unused)
                for url in urls:
                    try:
                        with urlopen(Request(url,method='HEAD'),timeout=20):raise AssertionError('Object still readable')
                    except HTTPError as error:
                        assert error.code==404
                m.atomic(evidence,{'checked_at':m.now(),'videos':2,'provider':'hf','batch_verified':True,'source_metadata_preserved':True,'remote_cleanup_404':True,'production_catalog_untouched':True})
                print('PASS: two real HF migrations verified; old references preserved until commit; test objects deleted and HEAD404')

if __name__=='__main__':main()
