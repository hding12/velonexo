import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from workspace_paths import ROOT, local_root
from setup_local import initialize


class Workspace(unittest.TestCase):
    def test_paths_match_node_and_initialize_preserves_existing_data(self):
        node_binary = shutil.which('node')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory).resolve() / 'code'
            (root/'config').mkdir(parents=True)
            for name in ['.env.example', 'config/catalog.example.json', 'config/storage.example.json']:
                (root/name).write_bytes((ROOT/name).read_bytes())
            first = initialize(root)
            self.assertEqual(first, root/'.local-work')
            # Existing data and credential bytes must never be replaced.
            for name in ['catalog/videos.json', 'config/storage.json', 'secrets/.env.local']:
                (first/name).write_text('preserve me')
            initialize(root)
            for name in ['catalog/videos.json', 'config/storage.json', 'secrets/.env.local']:
                self.assertEqual((first/name).read_text(), 'preserve me')
            self.assertEqual((first/'secrets/.env.local').stat().st_mode & 0o777, 0o600)
            second = initialize(root, '../separate')
            self.assertNotEqual(first, second)
            self.assertEqual(local_root(root), second)
            node = subprocess.check_output([node_binary, '-e', 'console.log(require(process.argv[1]).workspacePaths(process.argv[2]).LOCAL_ROOT)', str(ROOT/'server/workspace-paths.cjs'), str(root)], text=True)
            self.assertEqual(node.strip(), str(second))
            with patch.dict(os.environ, {'VELONEXO_LOCAL_ROOT':'../override'}):
                self.assertEqual(local_root(root), root.parent/'override')
            other=root.parent/'other-code'
            self.assertEqual(local_root(other), other/'.local-work')
