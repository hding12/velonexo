import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import media_publish as m
class Editorial(unittest.TestCase):
 def test_references_and_topic_lifecycle(self):
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'STATE',Path(d)/'state'),patch.object(m,'CATALOG',Path(d)/'catalog.json'):
    c={'schema_version':1,'videos':[{'id':'a','title':'T','creator':'C','visibility':'draft','tags':[],'published_at':'2026-01-01T00:00:00Z','source':{'kind':'external','url':'https://example.com'}}]};m.atomic(m.CATALOG,c)
    with self.assertRaises(ValueError):m.editorial_update({'action':'featured','ids':['missing']})
    self.assertEqual(m.read(m.CATALOG),c)
    m.editorial_update({'action':'featured','ids':['a']});m.editorial_update({'action':'topic','id':'one','title':'First','ids':['a']});m.editorial_update({'action':'topic','id':'one','title':'Changed','ids':[]})
    self.assertEqual(m.read(m.CATALOG)['editorial']['topics'],[{'id':'one','title':'Changed','ids':[]}])
    m.editorial_update({'action':'delete-topic','id':'one'});self.assertEqual(m.read(m.CATALOG)['editorial']['topics'],[])
