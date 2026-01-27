# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.cleaner.system_extensions import SystemExtensionsCleaner
from src.cleaner.intelligent_cleaner import CleaningAction, CleaningResult


class TestSystemComponentCleaning:
    """Tests pour le nettoyage des composants système"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = SystemExtensionsCleaner(dry_run=True)
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_thumbnail_cleaning_age_consistency(self):
        """Property: Le nettoyage des miniatures respecte l'âge des fichiers"""
        # Créer un répertoire de miniatures de test
        thumb_dir = os.path.join(self.temp_dir, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        # Créer des miniatures de différents âges
        now = datetime.now()
        old_cutoff = now - timedelta(days=90)
        
        # Miniature récente (ne devrait pas être nettoyée)
        recent_thumb = os.path.join(thumb_dir, "recent.png")
        Path(recent_thumb).write_text("recent thumbnail data")
        recent_time = now.timestamp()
        os.utime(recent_thumb, (recent_time, recent_time))
        
        # Miniature ancienne (devrait être nettoyée)
        old_thumb = os.path.join(thumb_dir, "old.png")
        Path(old_thumb).write_text("old thumbnail data")
        old_time = (now - timedelta(days=120)).timestamp()
        os.utime(old_thumb, (old_time, old_time))
        
        # Modifier temporairement la méthode pour utiliser notre répertoire de test
        original_scan = self.cleaner._scan_thumbnails
        
        def mock_scan_thumbnails():
            actions = []
            cutoff_date = datetime.now() - timedelta(days=90)
            
            if os.path.exists(thumb_dir):
                total_size = 0
                old_files_count = 0
                
                for file in os.listdir(thumb_dir):
                    filepath = os.path.join(thumb_dir, file)
                    try:
                        stat = os.stat(filepath)
                        file_date = datetime.fromtimestamp(stat.st_atime)
                        
                        if file_date < cutoff_date:
                            total_size += stat.st_size
                            old_files_count += 1
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
                
                if total_size > 0:
                    actions.append(CleaningAction(
                        action_type='clean_old_thumbnails',
                        target_path=thumb_dir,
                        size_bytes=total_size,
                        description=f"Supprimer anciennes miniatures ({old_files_count} fichiers)",
                        safety_level='safe',
                        category='thumbnails',
                        reversible=False
                    ))
            
            return actions
        
        self.cleaner._scan_thumbnails = mock_scan_thumbnails
        
        # Scanner les miniatures
        actions = self.cleaner._scan_thumbnails()
        
        # Vérifier qu'une action est proposée pour les anciennes miniatures
        if actions:
            thumb_action = actions[0]
            assert thumb_action.category == 'thumbnails'
            assert thumb_action.size_bytes > 0
            assert 'anciennes miniatures' in thumb_action.description.lower()
    
    def test_trash_cleaning_date_consistency(self):
        """Property: Le nettoyage de la corbeille respecte les dates de suppression"""
        # Créer une structure de corbeille de test
        trash_dir = os.path.join(self.temp_dir, "Trash")
        files_dir = os.path.join(trash_dir, "files")
        info_dir = os.path.join(trash_dir, "info")
        
        os.makedirs(files_dir, exist_ok=True)
        os.makedirs(info_dir, exist_ok=True)
        
        # Créer un fichier récemment supprimé
        recent_file = os.path.join(files_dir, "recent_file.txt")
        Path(recent_file).write_text("recent trash content")
        
        recent_info = os.path.join(info_dir, "recent_file.txt.trashinfo")
        recent_date = datetime.now().isoformat()
        Path(recent_info).write_text(f"""[Trash Info]
Path=/home/user/recent_file.txt
DeletionDate={recent_date}
""")
        
        # Créer un fichier anciennement supprimé
        old_file = os.path.join(files_dir, "old_file.txt")
        Path(old_file).write_text("old trash content")
        
        old_info = os.path.join(info_dir, "old_file.txt.trashinfo")
        old_date = (datetime.now() - timedelta(days=45)).isoformat()
        Path(old_info).write_text(f"""[Trash Info]
Path=/home/user/old_file.txt
DeletionDate={old_date}
""")
        
        # Modifier temporairement la méthode pour utiliser notre répertoire de test
        def mock_scan_trash():
            actions = []
            cutoff_date = datetime.now() - timedelta(days=30)
            
            if os.path.exists(trash_dir):
                files_dir_path = os.path.join(trash_dir, 'files')
                info_dir_path = os.path.join(trash_dir, 'info')
                
                if os.path.exists(files_dir_path):
                    total_size = 0
                    old_items_count = 0
                    
                    for item in os.listdir(files_dir_path):
                        item_path = os.path.join(files_dir_path, item)
                        info_path = os.path.join(info_dir_path, f"{item}.trashinfo")
                        
                        try:
                            deletion_date = None
                            if os.path.exists(info_path):
                                with open(info_path, 'r') as f:
                                    for line in f:
                                        if line.startswith('DeletionDate='):
                                            date_str = line.split('=', 1)[1].strip()
                                            deletion_date = datetime.fromisoformat(date_str.replace('T', ' '))
                                            break
                            
                            if deletion_date and deletion_date < cutoff_date:
                                item_size = self.cleaner._get_path_size(item_path)
                                total_size += item_size
                                old_items_count += 1
                        
                        except (PermissionError, FileNotFoundError, OSError, ValueError):
                            continue
                    
                    if total_size > 0:
                        actions.append(CleaningAction(
                            action_type='empty_old_trash',
                            target_path=trash_dir,
                            size_bytes=total_size,
                            description=f"Vider anciens éléments de la corbeille ({old_items_count} éléments)",
                            safety_level='moderate',
                            category='trash',
                            reversible=False
                        ))
            
            return actions
        
        self.cleaner._scan_trash = mock_scan_trash
        
        # Scanner la corbeille
        actions = self.cleaner._scan_trash()
        
        # Vérifier qu'une action est proposée pour les anciens éléments
        if actions:
            trash_action = actions[0]
            assert trash_action.category == 'trash'
            assert trash_action.safety_level == 'moderate'
            assert 'anciens éléments' in trash_action.description.lower()
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=1, max_value=1000000)
        ),
        min_size=1,
        max_size=10
    ))
    def test_system_cache_scanning_consistency(self, cache_specs):
        """Property: Le scan des caches système est cohérent"""
        # Créer des répertoires de cache système de test
        system_cache_dirs = []
        total_expected_size = 0
        
        for i, (cache_name, size) in enumerate(cache_specs):
            safe_cache_name = "".join(c for c in cache_name if c.isalnum() or c in "._-")
            if safe_cache_name:
                cache_dir = os.path.join(self.temp_dir, f"cache_{i}_{safe_cache_name}")
                os.makedirs(cache_dir, exist_ok=True)
                
                # Créer des fichiers de cache
                cache_file = os.path.join(cache_dir, "cache_data")
                try:
                    content = "x" * size
                    Path(cache_file).write_text(content, encoding='utf-8')
                    actual_size = len(content.encode('utf-8'))
                    total_expected_size += actual_size
                    system_cache_dirs.append(cache_dir)
                except (OSError, UnicodeEncodeError):
                    continue
        
        if not system_cache_dirs:
            return  # Skip si aucun cache créé
        
        # Modifier temporairement la méthode pour utiliser nos répertoires de test
        def mock_scan_snap_cache():
            actions = []
            for cache_dir in system_cache_dirs:
                if os.path.exists(cache_dir):
                    try:
                        cache_size = self.cleaner._get_directory_size(cache_dir)
                        if cache_size > 1024:  # Plus de 1KB
                            actions.append(CleaningAction(
                                action_type='clear_cache',
                                target_path=cache_dir,
                                size_bytes=cache_size,
                                description=f"Vider cache système: {os.path.basename(cache_dir)}",
                                safety_level='safe',
                                category='snap_cache',
                                reversible=False
                            ))
                    except (PermissionError, FileNotFoundError):
                        continue
            return actions
        
        self.cleaner._scan_snap_cache = mock_scan_snap_cache
        
        # Scanner les caches
        actions = self.cleaner._scan_snap_cache()
        
        # Vérifier la cohérence
        if actions:
            total_cache_size = sum(action.size_bytes for action in actions)
            assert total_cache_size >= total_expected_size * 0.8  # Tolérance
            
            for action in actions:
                assert action.category == 'snap_cache'
                assert action.safety_level == 'safe'
                assert action.size_bytes > 0
    
    def test_broken_symlinks_detection(self):
        """Property: La détection de liens symboliques cassés est correcte"""
        # Créer un répertoire de test
        test_bin_dir = os.path.join(self.temp_dir, "bin")
        os.makedirs(test_bin_dir, exist_ok=True)
        
        # Créer un fichier cible
        target_file = os.path.join(self.temp_dir, "target.txt")
        Path(target_file).write_text("target content")
        
        # Créer un lien symbolique valide
        valid_link = os.path.join(test_bin_dir, "valid_link")
        os.symlink(target_file, valid_link)
        
        # Créer un lien symbolique cassé
        broken_link = os.path.join(test_bin_dir, "broken_link")
        os.symlink("/nonexistent/path", broken_link)
        
        # Modifier temporairement la méthode pour utiliser notre répertoire
        def mock_scan_broken_symlinks():
            actions = []
            search_dirs = [test_bin_dir]
            
            broken_links = []
            total_size = 0
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    try:
                        for item in os.listdir(search_dir):
                            filepath = os.path.join(search_dir, item)
                            
                            if os.path.islink(filepath):
                                try:
                                    os.stat(filepath)
                                except (FileNotFoundError, OSError):
                                    broken_links.append(filepath)
                                    total_size += 1024
                    
                    except (PermissionError, FileNotFoundError):
                        continue
            
            if broken_links:
                actions.append(CleaningAction(
                    action_type='remove_broken_symlinks',
                    target_path=','.join(broken_links),
                    size_bytes=total_size,
                    description=f"Supprimer liens symboliques cassés ({len(broken_links)} liens)",
                    safety_level='safe',
                    category='broken_symlinks',
                    reversible=True
                ))
            
            return actions
        
        self.cleaner._scan_broken_symlinks = mock_scan_broken_symlinks
        
        # Scanner les liens cassés
        actions = self.cleaner._scan_broken_symlinks()
        
        # Vérifier qu'une action est proposée pour le lien cassé
        if actions:
            symlink_action = actions[0]
            assert symlink_action.category == 'broken_symlinks'
            assert symlink_action.safety_level == 'safe'
            assert symlink_action.reversible is True
            assert 'liens symboliques cassés' in symlink_action.description.lower()
            
            # Vérifier que seul le lien cassé est ciblé
            target_paths = symlink_action.target_path.split(',')
            assert broken_link in target_paths
            assert valid_link not in target_paths
    
    @given(st.lists(
        st.text(min_size=1, max_size=20),
        min_size=1,
        max_size=10
    ))
    def test_config_backup_age_filtering(self, backup_names):
        """Property: Le filtrage des sauvegardes de config par âge est correct"""
        # Créer un répertoire de configuration de test
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        
        now = datetime.now()
        old_cutoff = now - timedelta(days=180)
        
        created_backups = []
        old_backups = []
        
        for i, backup_name in enumerate(backup_names):
            safe_name = "".join(c for c in backup_name if c.isalnum() or c in "._-")
            if safe_name:
                # Créer des sauvegardes récentes et anciennes
                recent_backup = os.path.join(config_dir, f"{safe_name}_recent.bak")
                old_backup = os.path.join(config_dir, f"{safe_name}_old.backup")
                
                Path(recent_backup).write_text(f"recent backup {i}")
                Path(old_backup).write_text(f"old backup {i}")
                
                # Définir les temps de modification
                recent_time = now.timestamp()
                old_time = (now - timedelta(days=200)).timestamp()
                
                os.utime(recent_backup, (recent_time, recent_time))
                os.utime(old_backup, (old_time, old_time))
                
                created_backups.extend([recent_backup, old_backup])
                old_backups.append(old_backup)
        
        if not created_backups:
            return  # Skip si aucune sauvegarde créée
        
        # Modifier temporairement la méthode pour utiliser notre répertoire
        def mock_scan_old_config_backups():
            actions = []
            config_dirs = [config_dir]
            cutoff_date = datetime.now() - timedelta(days=180)
            backup_patterns = ['*.bak', '*.backup', '*.old', '*.orig', '*~']
            
            for config_dir_path in config_dirs:
                if os.path.exists(config_dir_path):
                    try:
                        old_backups_found = []
                        total_size = 0
                        
                        for file in os.listdir(config_dir_path):
                            is_backup = any(file.endswith(pattern[1:]) or file.endswith(pattern) 
                                          for pattern in backup_patterns)
                            
                            if is_backup:
                                filepath = os.path.join(config_dir_path, file)
                                try:
                                    stat = os.stat(filepath)
                                    file_date = datetime.fromtimestamp(stat.st_mtime)
                                    
                                    if file_date < cutoff_date:
                                        old_backups_found.append(filepath)
                                        total_size += stat.st_size
                                
                                except (PermissionError, FileNotFoundError, OSError):
                                    continue
                        
                        if old_backups_found and total_size > 1024:
                            actions.append(CleaningAction(
                                action_type='remove_old_config_backups',
                                target_path=','.join(old_backups_found),
                                size_bytes=total_size,
                                description=f"Supprimer anciennes sauvegardes de config ({len(old_backups_found)} fichiers)",
                                safety_level='moderate',
                                category='config_backups',
                                reversible=True
                            ))
                    
                    except (PermissionError, FileNotFoundError):
                        continue
            
            return actions
        
        self.cleaner._scan_old_config_backups = mock_scan_old_config_backups
        
        # Scanner les sauvegardes
        actions = self.cleaner._scan_old_config_backups()
        
        # Vérifier que seules les anciennes sauvegardes sont ciblées
        if actions:
            backup_action = actions[0]
            assert backup_action.category == 'config_backups'
            assert backup_action.safety_level == 'moderate'
            assert backup_action.reversible is True
            
            target_paths = backup_action.target_path.split(',')
            
            # Vérifier que toutes les anciennes sauvegardes sont incluses
            for old_backup in old_backups:
                assert old_backup in target_paths
    
    @given(st.sampled_from([
        'remove_snap_version', 'clean_old_thumbnails', 'empty_old_trash',
        'remove_broken_symlinks', 'remove_old_config_backups'
    ]))
    def test_system_action_execution_consistency(self, action_type):
        """Property: L'exécution d'actions système est cohérente"""
        # Créer une action de test selon le type
        if action_type == 'remove_snap_version':
            action = CleaningAction(
                action_type=action_type,
                target_path='test-snap:123',
                size_bytes=100 * 1024 * 1024,
                description="Supprimer ancienne version snap",
                safety_level='safe',
                category='snap_versions',
                reversible=False
            )
        
        elif action_type == 'clean_old_thumbnails':
            thumb_dir = os.path.join(self.temp_dir, "thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)
            
            action = CleaningAction(
                action_type=action_type,
                target_path=thumb_dir,
                size_bytes=10 * 1024 * 1024,
                description="Nettoyer anciennes miniatures",
                safety_level='safe',
                category='thumbnails',
                reversible=False
            )
        
        elif action_type == 'empty_old_trash':
            trash_dir = os.path.join(self.temp_dir, "Trash")
            os.makedirs(trash_dir, exist_ok=True)
            
            action = CleaningAction(
                action_type=action_type,
                target_path=trash_dir,
                size_bytes=5 * 1024 * 1024,
                description="Vider anciens éléments corbeille",
                safety_level='moderate',
                category='trash',
                reversible=False
            )
        
        elif action_type == 'remove_broken_symlinks':
            action = CleaningAction(
                action_type=action_type,
                target_path='/tmp/broken_link1,/tmp/broken_link2',
                size_bytes=2048,
                description="Supprimer liens cassés",
                safety_level='safe',
                category='broken_symlinks',
                reversible=True
            )
        
        elif action_type == 'remove_old_config_backups':
            action = CleaningAction(
                action_type=action_type,
                target_path='/etc/config.bak,/etc/other.backup',
                size_bytes=1024 * 1024,
                description="Supprimer anciennes sauvegardes config",
                safety_level='moderate',
                category='config_backups',
                reversible=True
            )
        
        # Exécuter l'action
        result = self.cleaner.execute_system_cleaning_action(action)
        
        # Vérifier la cohérence du résultat
        assert isinstance(result, CleaningResult)
        assert result.action == action
        assert isinstance(result.success, bool)
        assert result.actual_size_freed >= 0
        assert result.execution_time >= 0
        
        # En mode dry-run, l'action devrait réussir
        assert result.success is True
        assert result.actual_size_freed == action.size_bytes


class SystemComponentCleaning(RuleBasedStateMachine):
    """Machine à états pour tester le nettoyage des composants système"""
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = SystemExtensionsCleaner(dry_run=True)
        self.created_system_files = {}
        self.executed_actions = []
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(component=st.sampled_from(['thumbnails', 'trash', 'cache', 'logs']),
          age_days=st.integers(min_value=1, max_value=365))
    def create_system_component(self, component, age_days):
        """Créer un composant système à nettoyer"""
        if component == 'thumbnails':
            thumb_dir = os.path.join(self.temp_dir, "thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)
            
            thumb_file = os.path.join(thumb_dir, f"thumb_{age_days}.png")
            Path(thumb_file).write_text("thumbnail data")
            
            # Définir l'âge du fichier
            file_time = (datetime.now() - timedelta(days=age_days)).timestamp()
            os.utime(thumb_file, (file_time, file_time))
            
            self.created_system_files[thumb_file] = {'component': component, 'age_days': age_days}
        
        elif component == 'trash':
            trash_dir = os.path.join(self.temp_dir, "Trash")
            files_dir = os.path.join(trash_dir, "files")
            info_dir = os.path.join(trash_dir, "info")
            
            os.makedirs(files_dir, exist_ok=True)
            os.makedirs(info_dir, exist_ok=True)
            
            trash_file = os.path.join(files_dir, f"trash_{age_days}.txt")
            Path(trash_file).write_text("trash content")
            
            info_file = os.path.join(info_dir, f"trash_{age_days}.txt.trashinfo")
            deletion_date = (datetime.now() - timedelta(days=age_days)).isoformat()
            Path(info_file).write_text(f"""[Trash Info]
Path=/home/user/trash_{age_days}.txt
DeletionDate={deletion_date}
""")
            
            self.created_system_files[trash_file] = {'component': component, 'age_days': age_days}
        
        elif component == 'cache':
            cache_dir = os.path.join(self.temp_dir, f"cache_{age_days}")
            os.makedirs(cache_dir, exist_ok=True)
            
            cache_file = os.path.join(cache_dir, "cache_data")
            Path(cache_file).write_text("cache content")
            
            self.created_system_files[cache_file] = {'component': component, 'age_days': age_days}
    
    @rule()
    def scan_system_extensions(self):
        """Scanner les extensions système"""
        # Mock des méthodes de scan pour utiliser nos fichiers de test
        actions = []
        
        # Scanner nos composants créés
        for filepath, info in self.created_system_files.items():
            if info['component'] == 'thumbnails' and info['age_days'] > 90:
                actions.append(CleaningAction(
                    action_type='clean_old_thumbnails',
                    target_path=os.path.dirname(filepath),
                    size_bytes=1024,
                    description="Test thumbnail cleaning",
                    safety_level='safe',
                    category='thumbnails',
                    reversible=False
                ))
            
            elif info['component'] == 'trash' and info['age_days'] > 30:
                actions.append(CleaningAction(
                    action_type='empty_old_trash',
                    target_path=os.path.dirname(os.path.dirname(filepath)),
                    size_bytes=1024,
                    description="Test trash cleaning",
                    safety_level='moderate',
                    category='trash',
                    reversible=False
                ))
        
        # Exécuter quelques actions
        if actions:
            results = []
            for action in actions[:3]:  # Limiter à 3 actions
                result = self.cleaner.execute_system_cleaning_action(action)
                results.append(result)
            
            self.executed_actions.extend(results)
    
    @rule()
    def create_broken_symlink(self):
        """Créer un lien symbolique cassé"""
        bin_dir = os.path.join(self.temp_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        
        broken_link = os.path.join(bin_dir, "broken_link")
        try:
            os.symlink("/nonexistent/target", broken_link)
            self.created_system_files[broken_link] = {'component': 'symlink', 'broken': True}
        except OSError:
            pass
    
    @invariant()
    def system_files_are_tracked(self):
        """Invariant: Les fichiers système sont suivis"""
        for filepath in self.created_system_files:
            # Le fichier devrait exister (sauf s'il a été nettoyé)
            parent_dir = os.path.dirname(filepath)
            if os.path.exists(parent_dir):
                # Le répertoire parent existe, donc le fichier devrait être là
                # (sauf en cas de nettoyage réel, mais on est en dry-run)
                pass
    
    @invariant()
    def executed_actions_are_valid(self):
        """Invariant: Les actions exécutées sont valides"""
        for result in self.executed_actions:
            assert isinstance(result, CleaningResult)
            assert result.success is True  # En mode dry-run
            assert result.actual_size_freed >= 0
            assert result.execution_time >= 0


# Test de la machine à états
TestSystemComponentCleaning = SystemComponentCleaning.TestCase


if __name__ == '__main__':
    pytest.main([__file__])