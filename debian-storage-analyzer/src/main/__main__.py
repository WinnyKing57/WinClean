# -*- coding: utf-8 -*-

import sys
import os
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser("~/.cache/debian-storage-analyzer.log"))
    ]
)
logger = logging.getLogger("debian-storage-analyzer")

# Ajout du chemin src pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main.modern_main import ModernApplication

if __name__ == "__main__":
    app = ModernApplication()
    sys.exit(app.run(sys.argv))
