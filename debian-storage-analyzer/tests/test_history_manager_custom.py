# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
import sys
import os

# Ajouter src au path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from helpers.history_db import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_history.db")
        self.manager = HistoryManager(db_path=self.db_path)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_record_scan(self):
        self.manager.record_scan("/home", 1024, {"Dossier": 512, "Fichier": 512})
        history = self.manager.get_scan_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['path'], "/home")
        self.assertEqual(history[0]['total_size'], 1024)
        self.assertEqual(history[0]['categorized_data'], {"Dossier": 512, "Fichier": 512})

    def test_record_cleaning(self):
        self.manager.record_cleaning("APT", 500)
        history = self.manager.get_cleaning_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['action_type'], "APT")
        self.assertEqual(history[0]['freed_space'], 500)

        self.assertEqual(self.manager.get_total_freed_space(), 500)

    def test_get_trends(self):
        self.manager.record_scan("/home", 1000, {})
        trends = self.manager.get_trends()
        self.assertEqual(len(trends), 1)
        self.assertIn('day', trends[0])
        self.assertEqual(trends[0]['avg_size'], 1000.0)

if __name__ == '__main__':
    unittest.main()
