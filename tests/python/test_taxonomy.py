from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import media_publish as m
class Taxonomy(unittest.TestCase):
 def test_merge_order_and_invalid_order(self):
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'STATE',Path(d)/'state'),patch.object(m,'CATALOG',Path(d)/'catalog.json'):
    c={'schema_version':1,'videos':[{'id':str(i),'title':'T','creator':'C','visibility':'draft','category':category,'tags':['a','b'],'published_at':'2026-01-01T00:00:00Z','source':{'kind':'external','url':'https://example.com'}} for i,category in enumerate(['a','b'])]};m.atomic(m.CATALOG,c)
    m.taxonomy_update('category','a','b');self.assertTrue(all(v['category']=='b' for v in m.read(m.CATALOG)['videos']))
    m.taxonomy_update('tag','a','b');self.assertTrue(all(v['tags']==['b'] for v in m.read(m.CATALOG)['videos']))
    before=m.CATALOG.read_bytes()
    with self.assertRaises(ValueError):m.taxonomy_update('tag',order=['unknown'])
    self.assertEqual(before,m.CATALOG.read_bytes())
    m.taxonomy_update('tag',order=['b']);self.assertEqual(m.read(m.CATALOG)['taxonomy']['tags'],['b'])
