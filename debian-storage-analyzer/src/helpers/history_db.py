# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime
import json
from typing import List, Dict, Any, Optional

class HistoryManager:
    """Gère l'historique des analyses et des nettoyages dans une base SQLite."""

    def __init__(self, db_path=None):
        if db_path is None:
            config_dir = os.path.expanduser("~/.config/debian-storage-analyzer")
            os.makedirs(config_dir, exist_ok=True)
            db_path = os.path.join(config_dir, "history.db")

        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialise le schéma de la base de données."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Table pour les analyses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    path TEXT NOT NULL,
                    total_size INTEGER NOT NULL,
                    categorized_data TEXT -- JSON string of category sizes
                )
            ''')

            # Table pour les nettoyages
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cleanings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT NOT NULL,
                    freed_space INTEGER NOT NULL
                )
            ''')

            conn.commit()

    def record_scan(self, path: str, total_size: int, categorized_data: Dict[str, int]):
        """Enregistre une nouvelle analyse."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scans (path, total_size, categorized_data) VALUES (?, ?, ?)",
                (path, total_size, json.dumps(categorized_data))
            )
            conn.commit()

    def record_cleaning(self, action_type: str, freed_space: int):
        """Enregistre une action de nettoyage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cleanings (action_type, freed_space) VALUES (?, ?)",
                (action_type, freed_space)
            )
            conn.commit()

    def get_scan_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère l'historique des analyses."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()

            history = []
            for row in rows:
                item = dict(row)
                item['categorized_data'] = json.loads(item['categorized_data']) if item['categorized_data'] else {}
                history.append(item)
            return history

    def get_cleaning_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère l'historique des nettoyages."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cleanings ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_all_history(self):
        """Supprime tout l'historique de la base de données."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scans")
            cursor.execute("DELETE FROM cleanings")
            conn.commit()

    def get_total_freed_space(self) -> int:
        """Calcule l'espace total libéré par tous les nettoyages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(freed_space) FROM cleanings")
            result = cursor.fetchone()[0]
            return result if result else 0

    def get_trends(self) -> List[Dict[str, Any]]:
        """Récupère les tendances de stockage au fil du temps (taille totale par scan)."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # On groupe par jour pour avoir une tendance simplifiée
            cursor.execute('''
                SELECT date(timestamp) as day, AVG(total_size) as avg_size
                FROM scans
                GROUP BY day
                ORDER BY day ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
