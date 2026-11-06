"""Inject a partial upload failure on synthetic media and clean only its unlisted objects."""
import argparse
import fcntl
import sys
import uuid
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import media_publish as m
from media_storage import Store


def main():
    before_catalog=m.CATALOG.read_bytes();before_usage=m.account(m.ledger());evidence=[]
    with open(m.STATE/'lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for provider in ['tigris','hf']:
            video_id='cleanup-test-'+uuid.uuid4().hex[:12];calls=[];original=Store.upload
            args=argparse.Namespace(input=str(m.RUNTIME/'fixtures/portrait-audio.mp4'),id=video_id,title='Prueba de limpieza',creator='@test',category='prueba',tag=[],provider=provider,dry_run=False,draft=True)
            def interrupted(self,file,key):
                calls.append(key)
                if len(calls)==2:raise OSError('Injected interruption before second object')
                return original(self,file,key)
            try:
                with patch.object(Store,'upload',interrupted):
                    try:m.publish(args)
                    except OSError:pass
                    else:raise AssertionError('Expected interruption')
                assert len(calls)==2
                assert m.CATALOG.read_bytes()==before_catalog
                m.cleanup_unpublished(video_id)
                adapter=m.stores(m.config())[provider]
                try:
                    with urlopen(Request(adapter.url(calls[0],'HEAD'),method='HEAD'),timeout=20):raise AssertionError('Object still accessible')
                except HTTPError as e:assert e.code==404
                assert m.account(m.ledger())==before_usage
                evidence.append({'provider':provider,'partial_upload':True,'catalog_unchanged':True,'uploaded_object_404':True,'usage_restored':True})
            finally:
                if (m.MEDIA/video_id).exists():m.cleanup_unpublished(video_id)
        m.atomic(m.STATE/'studio-cleanup-evidence.json',{'checked_at':m.now(),'checks':evidence})
    print('PASS: real partial-upload cleanup on Tigris and HF; catalog and project usage unchanged')


if __name__=='__main__':main()
