# -*- coding: utf-8 -*-
import unittest
import os
import tempfile
import shutil
import sys

# Ajout du chemin src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from analyzer.storage_analyzer import analyze_directory

class TestStorageAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Créer des fichiers et dossiers de test
        self.sub_dir = os.path.join(self.test_dir, "sub")
        os.mkdir(self.sub_dir)

        with open(os.path.join(self.test_dir, "file1.txt"), "w") as f:
            f.write("a" * 100) # 100 bytes

        with open(os.path.join(self.sub_dir, "file2.txt"), "w") as f:
            f.write("b" * 500) # 500 bytes

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_analyze_directory(self):
        results = analyze_directory(self.test_dir)

        # On attend 2 éléments : sub (500b) et file1.txt (100b)
        self.assertEqual(len(results), 2)

        # Trié par taille décroissante
        self.assertEqual(os.path.basename(results[0].path), "sub")
        self.assertEqual(results[0].size, 500)
        self.assertTrue(results[0].is_dir)

        self.assertEqual(os.path.basename(results[1].path), "file1.txt")
        self.assertEqual(results[1].size, 100)
        self.assertFalse(results[1].is_dir)

if __name__ == '__main__':
    unittest.main()
