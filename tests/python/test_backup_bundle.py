import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import backup_bundle as b
class Backup(unittest.TestCase):
 def test_corruption_traversal_and_existing_destination(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);archive=root/'bad.zip';dest=root/'result'
   with zipfile.ZipFile(archive,'w') as z:
    z.writestr('backup-manifest.json',json.dumps({'schema_version':1,'files':{'file':{'sha256':'0'*64,'bytes':4}}}));z.writestr('file','data')
   with self.assertRaises(ValueError):b.restore(archive,dest)
   self.assertFalse(dest.exists())
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','data')
   with self.assertRaises(ValueError):b.restore(archive,dest)
   self.assertFalse((root/'escape').exists())
   dest.mkdir()
   with self.assertRaises(ValueError):b.restore(archive,dest)
