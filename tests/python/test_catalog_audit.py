import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import media_publish as m

class Audit(unittest.TestCase):
    def test_before_after_reason_and_failed_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(m,'STATE',root/'state'),patch.object(m,'CATALOG',root/'catalog.json'),patch.object(m,'AUDIT_CONTEXT',{'action':'edit','reason':'Correct title','actor':'local-operator'}):
                original={'schema_version':1,'videos':[]};m.atomic(m.CATALOG,original)
                updated={'schema_version':1,'videos':[{'id':'a','title':'Title','creator':'@a','visibility':'draft','tags':[],'published_at':'2026-01-01T00:00:00Z','source':{'kind':'external','url':'https://example.com/v'}}]}
                m.save_catalog(updated)
                event=m.read(next((m.STATE/'events').glob('*.json')))
                self.assertEqual(event['reason'],'Correct title');self.assertEqual(event['state'],'applied');self.assertIsNone(event['changes'][0]['before']);self.assertEqual(event['changes'][0]['after']['title'],'Title')
                real=m.atomic
                def fail_catalog(path,value):
                    if path==m.CATALOG:raise OSError('injected catalog failure')
                    real(path,value)
                with patch.object(m,'atomic',side_effect=fail_catalog):
                    with self.assertRaises(OSError):m.save_catalog(original)
                self.assertEqual(m.read(m.CATALOG),updated)
                self.assertEqual(sum(m.read(p)['state']=='prepared' for p in (m.STATE/'events').glob('*.json')),1)
