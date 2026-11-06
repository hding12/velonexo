import argparse,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import media_publish as m
import media_maintenance as maintenance
class Maintenance(unittest.TestCase):
 def test_batch_failure_and_resumable_cleanup(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);config={'schema_version':1,'group_size':3,'providers':[{'id':'target','project_limit_bytes':10000000}]}
   with patch.object(m,'STATE',root/'state'),patch.object(m,'MEDIA',root/'media'),patch.object(m,'CATALOG',root/'catalog.json'),patch.object(m,'config',return_value=config):
    m.atomic(m.CATALOG,{'schema_version':1,'videos':[]});source=root/'input.mp4'
    m.command(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=80x120:rate=24','-t','1','-c:v','libx264',str(source)])
    for id in ['a','b']:m.publish(argparse.Namespace(input=str(source),id=id,title=id,creator='@test',category='test',tag=[],provider='local',draft=True,dry_run=False))
    before=m.CATALOG.read_bytes()
    class Store:
     fail=True;deletes=0
     def identity(self):return {'bucket':'test'}
     def upload(self,*args):pass
     def url(self,key):return 'https://example.com/'+key
     def verify(self,obj):
      if self.fail and '/b/' in obj['object_key']:raise ValueError('Injected verify failure')
      return {}
     def delete(self,key):
      self.deletes+=1
      if self.deletes==5:raise OSError('Injected delete failure')
    store=Store()
    with patch.object(m,'stores',return_value={'target':store}):
     maintenance.migrate(['a','b'],'target',False);self.assertEqual(m.CATALOG.read_bytes(),before)
     with self.assertRaises(ValueError):maintenance.migrate(['a','b'],'target',True)
     self.assertEqual(m.CATALOG.read_bytes(),before)
     candidates=[v['version'] for v in maintenance.versions() if not v['protected']]
     self.assertEqual(len(candidates),2)
     protected=next(v['version'] for v in maintenance.versions() if v['protected'])
     with self.assertRaises(ValueError):maintenance.clean_versions([protected])
     with self.assertRaises(OSError):maintenance.clean_versions(candidates)
     maintenance.clean_versions(candidates)
     self.assertTrue(all(m.read(m.MEDIA/key/'map.json')['state']=='purged' for key in candidates))
     store.fail=False;maintenance.migrate(['a','b'],'target',True)
     result=m.read(m.CATALOG);self.assertTrue(all(v['visibility']=='draft' and v['title']==v['id'] for v in result['videos']))
     self.assertNotEqual(m.CATALOG.read_bytes(),before)
     self.assertTrue(all(v['protected'] for v in maintenance.versions()))
