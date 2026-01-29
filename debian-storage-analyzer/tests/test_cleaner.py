# -*- coding: utf-8 -*-
import unittest
import os
import sys

# Ajout du chemin src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from cleaner.intelligent_cleaner import IntelligentCleaner

class TestIntelligentCleaner(unittest.TestCase):
    def test_dry_run_mode(self):
        cleaner = IntelligentCleaner(dry_run=True)
        self.assertTrue(cleaner.dry_run)

    def test_safe_path_detection(self):
        cleaner = IntelligentCleaner(dry_run=True)
        self.assertTrue(cleaner.is_path_safe_to_clean("/tmp/test"))
        self.assertFalse(cleaner.is_path_safe_to_clean("/etc/passwd"))
        self.assertFalse(cleaner.is_path_safe_to_clean(os.path.expanduser("~/.ssh/id_rsa")))

if __name__ == '__main__':
    unittest.main()
