import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import media_publish as m

class Publishing(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patches=[patch.object(m,'STATE',self.root/'state'),patch.object(m,'MEDIA',self.root/'media'),patch.object(m,'CATALOG',self.root/'catalog.json')]
        for p in self.patches:p.start()
        m.atomic(m.CATALOG,{'schema_version':1,'videos':[]})
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def fixture(self):
        dest=self.root/'package';dest.mkdir();(dest/'init.mp4').write_bytes(b'init');(dest/'seg_00000.m4s').write_bytes(b'segment');(dest/'poster.jpg').write_bytes(b'poster')
        objs=[{'file':p.name,'provider_id':'local','object_key':'velonexo/test/0123456789abcdef/'+p.name,'sha256':m.digest(p),'size_bytes':p.stat().st_size} for p in dest.iterdir()]
        manifest={'schema_version':1,'video_id':'test','revision':'0123456789abcdef','init':'init.mp4','poster':'poster.jpg','objects':objs,'duration':2.0,'encoding':{'audio':None},'segments':[{'file':'seg_00000.m4s','sequence':0,'duration':2.0}]}
        return dest,manifest
    def test_map_rejects_order_hash_path(self):
        _,original=self.fixture()
        for field,value in [('sequence',2),('duration',float('nan'))]:
            bad=copy.deepcopy(original);bad['segments'][0][field]=value
            with self.assertRaises(ValueError):m.validate_map(bad)
        bad=copy.deepcopy(original);bad['objects'][0]['object_key']='../escape'
        with self.assertRaises(ValueError):m.validate_map(bad)
    def test_refresh_compiles_map_and_detects_corruption(self):
        dest,manifest=self.fixture();m.refresh(dest,manifest,{})
        self.assertIn('#EXT-X-ENDLIST',(dest/'play.m3u8').read_text())
        (dest/'init.mp4').write_bytes(b'corrupted')
        before=(dest/'play.m3u8').read_bytes()
        with self.assertRaises(ValueError):m.refresh(dest,manifest,{})
        self.assertEqual(before,(dest/'play.m3u8').read_bytes())
    def test_refresh_never_uploads(self):
        dest,manifest=self.fixture()
        class Adapter:
            def identity(self):return {'bucket':'test'}
            def upload(self,*a):raise AssertionError('must not upload')
            def verify(self,o):return {'verified':True}
            def url(self,k):return 'https://example.com/'+k+'?new-signature'
        for o in manifest['objects']:o['provider_id']='test'
        m.refresh(dest,manifest,{'test':Adapter()})
        self.assertIn('new-signature',(dest/'play.m3u8').read_text())
    def test_failed_verification_does_not_publish(self):
        dest,manifest=self.fixture();args=argparse.Namespace(input='unused',id='test',provider='local',dry_run=False,title='Prueba',creator='@test',category='prueba',tag=[])
        before=m.CATALOG.read_bytes()
        with patch.object(m,'prepare',return_value=(dest,manifest)),patch.object(m,'refresh',side_effect=ValueError('failure')):
            with self.assertRaises(ValueError):m.publish(args)
        self.assertEqual(before,m.CATALOG.read_bytes())
    def test_prepare_outputs_and_placement_revision(self):
        source=self.root/'input.mp4'
        m.command(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=80x120:rate=24','-f','lavfi','-i','sine=frequency=440','-t','7','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)])
        c={'providers':[{'id':'a'},{'id':'b'}],'group_size':3}
        dest,media=m.prepare(source,'encode-test',c,'local')
        self.assertEqual(media['encoding']['audio'],'aac')
        self.assertTrue((dest/'poster.jpg').exists())
        self.assertTrue((m.STATE/'sources'/(media['source_sha256']+'.source')).exists())
        self.assertEqual(dest,m.prepare(source,'encode-test',c,'local')[0])
        other,split=m.prepare(source,'encode-test',c)
        self.assertNotEqual(dest,other)
        self.assertEqual({o['provider_id'] for o in split['objects']},{'a','b'})
        m.refresh(dest,media,{})
        self.assertEqual(len(media['segments']),4)

    def test_upload_failure_does_not_publish(self):
        dest,media=self.fixture()
        for o in media['objects']:o['provider_id']='test'
        class Adapter:
            def identity(self):return {'bucket':'test'}
            def upload(self,*args):raise RuntimeError('interrupted upload')
        c={'providers':[{'id':'test','project_limit_bytes':1000}]}
        args=argparse.Namespace(input='unused',id='test',provider='test',dry_run=False,title='Prueba',creator='@test',category='prueba',tag=[])
        before=m.CATALOG.read_bytes()
        with patch.object(m,'config',return_value=c),patch.object(m,'prepare',return_value=(dest,media)),patch.object(m,'stores',return_value={'test':Adapter()}):
            with self.assertRaises(RuntimeError):m.publish(args)
        self.assertEqual(before,m.CATALOG.read_bytes())
        self.assertEqual(len(m.ledger()),1)

    def test_batch_publish_failure_is_atomic(self):
        entries=[{'id':name,'title':'Prueba','creator':'@test','visibility':'draft','source':{'kind':'native','format':'hls','playlist':'/play.m3u8'},'published_at':'2026-11-06T00:00:00Z','tags':[]} for name in ['first','second']]
        m.atomic(m.CATALOG,{'schema_version':1,'videos':entries});before=m.CATALOG.read_bytes()
        with patch.object(m,'find_map',return_value=(self.root,{'objects':[]})),patch.object(m,'refresh',side_effect=[None,ValueError('missing')]):
            with self.assertRaises(ValueError):m.bulk_state(['first','second'],'publish')
        self.assertEqual(before,m.CATALOG.read_bytes())
        m.bulk_state(['first','second'],'withdraw')
        self.assertTrue(all(e['visibility']=='removed' for e in m.read(m.CATALOG)['videos']))

    def cleanup_fixture(self, remote=False):
        import shutil
        dest,media=self.fixture();target=m.MEDIA/'test'/media['revision'];target.parent.mkdir(parents=True)
        shutil.move(dest,target)
        if remote:
            for o in media['objects']:o['provider_id']='remote'
            media['storage_bindings']={'remote':{'bucket':'test'}}
            m.atomic(m.STATE/'objects.json',{m.object_id(o):o for o in media['objects']})
        m.atomic(target/'map.json',media)
        return target,media

    def test_cleanup_refuses_even_draft_entries(self):
        dest,media=self.cleanup_fixture()
        m.atomic(m.CATALOG,{'schema_version':1,'videos':[{'id':'test','visibility':'draft'}]})
        with self.assertRaises(ValueError):m.cleanup_unpublished('test')
        self.assertTrue(dest.exists())

    def test_cleanup_is_resumable_and_preserves_backups(self):
        dest,media=self.cleanup_fixture(True);calls=[]
        backup=m.STATE/'sources'/'original.source';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(b'original')
        class Adapter:
            failed=False
            def identity(self):return {'bucket':'test'}
            def delete(self,key):
                calls.append(key)
                if len(calls)==2 and not self.failed:
                    self.failed=True;raise OSError('network interruption')
        adapter=Adapter()
        with patch.object(m,'stores',return_value={'remote':adapter}):
            with self.assertRaises(OSError):m.cleanup_unpublished('test')
            self.assertTrue(dest.exists())
            m.cleanup_unpublished('test')
        self.assertFalse(dest.parent.exists())
        self.assertTrue(backup.exists())
        self.assertEqual(calls.count(media['objects'][0]['object_key']),1)
        self.assertTrue(all(o.get('deleted') for o in m.ledger().values()))

    def test_provider_repointing_rejected(self):
        dest,manifest=self.fixture();manifest['storage_bindings']={'remote':{'bucket':'original'}}
        class Adapter:
            def identity(self):return {'bucket':'changed'}
        with self.assertRaises(ValueError):m.refresh(dest,manifest,{'remote':Adapter()})

    def test_capacity_deduplicates_and_rejects_limit(self):
        o={'provider_id':'p','object_key':'key','size_bytes':10}
        c={'providers':[{'id':'p','project_limit_bytes':10}]}
        self.assertEqual(m.check_budget([o],c,{'p:key':o}),{'p':10})
        with self.assertRaises(ValueError):m.check_budget([{**o,'object_key':'another'}],c,{'p:key':o})
    def test_catalog_backup_and_invalid_restore(self):
        old=m.read(m.CATALOG);m.save_catalog(old)
        self.assertEqual(len(list((m.STATE/'backups').glob('*.json'))),1)
        with self.assertRaises(ValueError):m.save_catalog({'schema_version':2,'videos':[]})
        self.assertEqual(old,m.read(m.CATALOG))

if __name__=='__main__':unittest.main()
