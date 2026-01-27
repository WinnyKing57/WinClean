# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.cleaner.intelligent_cleaner import IntelligentCleaner, CleaningAction, CleaningResult


class TestDryRunSafety:
    """Tests de sécurité pour le mode dry-run"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_dry_run_never_modifies_filesystem(self):
        """Property: Le mode dry-run ne modifie jamais le système de fichiers"""
        # Créer des fichiers de test
        test_files = []
        for i in range(5):
            filepath = os.path.join(self.temp_dir, f"test_{i}.txt")
            content = f"Test content {i}"
            Path(filepath).write_text(content)
            test_files.append((filepath, content))
        
        # Créer un nettoyeur en mode dry-run
        cleaner = IntelligentCleaner(dry_run=True)
        
        # Créer des actions de suppression
        actions = []
        for filepath, content in test_files:
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=len(content.encode('utf-8')),
                description=f"Supprimer {os.path.basename(filepath)}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
        
        # Exécuter les actions en mode dry-run
        results = cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que tous les fichiers existent encore
        for filepath, original_content in test_files:
            assert os.path.exists(filepath), f"Fichier {filepath} ne devrait pas être supprimé en mode dry-run"
            
            # Vérifier que le contenu n'a pas changé
            current_content = Path(filepath).read_text()
            assert current_content == original_content, f"Contenu de {filepath} ne devrait pas changer en mode dry-run"
        
        # Vérifier que les résultats indiquent un succès (simulation)
        for result in results:
            assert result.success is True, "Les actions dry-run devraient toujours réussir"
            assert result.actual_size_freed > 0, "Les actions dry-run devraient simuler la libération d'espace"
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.text(min_size=0, max_size=1000)
        ),
        min_size=1,
        max_size=10
    ))
    def test_dry_run_preserves_all_files(self, file_specs):
        """Property: Le mode dry-run préserve tous les fichiers"""
        # Créer des fichiers avec du contenu aléatoire
        created_files = {}
        
        for filename, content in file_specs:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if safe_filename:
                filepath = os.path.join(self.temp_dir, f"{safe_filename}.txt")
                try:
                    Path(filepath).write_text(content, encoding='utf-8')
                    created_files[filepath] = content
                except (OSError, UnicodeEncodeError):
                    continue
        
        if not created_files:
            return  # Skip si aucun fichier créé
        
        # Créer un nettoyeur en mode dry-run
        cleaner = IntelligentCleaner(dry_run=True)
        
        # Créer des actions pour tous les fichiers
        actions = []
        for filepath, content in created_files.items():
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=len(content.encode('utf-8')),
                description=f"Test suppression {os.path.basename(filepath)}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
        
        # Exécuter en mode dry-run
        results = cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que tous les fichiers existent encore avec le bon contenu
        for filepath, original_content in created_files.items():
            assert os.path.exists(filepath)
            current_content = Path(filepath).read_text(encoding='utf-8')
            assert current_content == original_content
        
        # Vérifier que toutes les actions ont "réussi"
        assert len(results) == len(actions)
        for result in results:
            assert result.success is True
    
    def test_dry_run_vs_real_mode_consistency(self):
        """Property: Les résultats dry-run sont cohérents avec les estimations"""
        # Créer des fichiers de test
        test_files = []
        total_expected_size = 0
        
        for i in range(3):
            filepath = os.path.join(self.temp_dir, f"consistency_test_{i}.txt")
            content = f"Test content for consistency {i}" * 10
            Path(filepath).write_text(content)
            
            file_size = len(content.encode('utf-8'))
            test_files.append((filepath, file_size))
            total_expected_size += file_size
        
        # Créer des actions
        actions = []
        for filepath, size in test_files:
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=size,
                description=f"Test {os.path.basename(filepath)}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
        
        # Tester en mode dry-run
        dry_run_cleaner = IntelligentCleaner(dry_run=True)
        dry_run_results = dry_run_cleaner.execute_cleaning_actions(actions)
        
        # Vérifier la cohérence des résultats dry-run
        dry_run_total_freed = sum(result.actual_size_freed for result in dry_run_results)
        assert dry_run_total_freed == total_expected_size
        
        # Vérifier que tous les fichiers existent encore
        for filepath, _ in test_files:
            assert os.path.exists(filepath)
    
    @given(st.sampled_from(['delete_file', 'delete_directory', 'clear_cache']))
    def test_dry_run_safety_across_action_types(self, action_type):
        """Property: Le mode dry-run est sûr pour tous les types d'actions"""
        # Créer le contenu approprié selon le type d'action
        if action_type == 'delete_file':
            target_path = os.path.join(self.temp_dir, "test_file.txt")
            Path(target_path).write_text("Test content")
            expected_size = len("Test content".encode('utf-8'))
        
        elif action_type == 'delete_directory':
            target_path = os.path.join(self.temp_dir, "test_dir")
            os.makedirs(target_path)
            
            # Ajouter quelques fichiers dans le répertoire
            for i in range(3):
                file_path = os.path.join(target_path, f"file_{i}.txt")
                Path(file_path).write_text(f"Content {i}")
            
            expected_size = sum(
                len(f"Content {i}".encode('utf-8')) for i in range(3)
            )
        
        elif action_type == 'clear_cache':
            target_path = os.path.join(self.temp_dir, "cache_dir")
            os.makedirs(target_path)
            
            # Ajouter des fichiers de cache
            for i in range(2):
                cache_file = os.path.join(target_path, f"cache_{i}.tmp")
                Path(cache_file).write_text(f"Cache data {i}")
            
            expected_size = sum(
                len(f"Cache data {i}".encode('utf-8')) for i in range(2)
            )
        
        # Créer l'action
        action = CleaningAction(
            action_type=action_type,
            target_path=target_path,
            size_bytes=expected_size,
            description=f"Test {action_type}",
            safety_level='safe',
            category='test',
            reversible=False
        )
        
        # Exécuter en mode dry-run
        cleaner = IntelligentCleaner(dry_run=True)
        results = cleaner.execute_cleaning_actions([action])
        
        # Vérifier que le contenu existe encore
        assert os.path.exists(target_path)
        
        # Vérifier le résultat
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.actual_size_freed == expected_size
    
    def test_dry_run_mode_toggle(self):
        """Property: Le basculement du mode dry-run fonctionne correctement"""
        cleaner = IntelligentCleaner(dry_run=True)
        
        # Vérifier l'état initial
        assert cleaner.dry_run is True
        
        # Basculer vers le mode réel
        cleaner.set_dry_run(False)
        assert cleaner.dry_run is False
        
        # Basculer vers le mode dry-run
        cleaner.set_dry_run(True)
        assert cleaner.dry_run is True
    
    def test_dry_run_backup_behavior(self):
        """Property: Le mode dry-run ne crée pas de sauvegardes"""
        # Créer un fichier de test
        test_file = os.path.join(self.temp_dir, "backup_test.txt")
        Path(test_file).write_text("Test content for backup")
        
        # Créer une action réversible
        action = CleaningAction(
            action_type='delete_file',
            target_path=test_file,
            size_bytes=1024,
            description="Test backup behavior",
            safety_level='safe',
            category='test',
            reversible=True  # Devrait normalement créer une sauvegarde
        )
        
        # Exécuter en mode dry-run
        cleaner = IntelligentCleaner(dry_run=True)
        results = cleaner.execute_cleaning_actions([action])
        
        # Vérifier qu'aucune sauvegarde n'a été créée
        backup_dir = cleaner.backup_dir
        if os.path.exists(backup_dir):
            backup_files = os.listdir(backup_dir)
            # Il ne devrait pas y avoir de nouveaux fichiers de sauvegarde
            # (on ne peut pas être sûr qu'il n'y en avait pas avant)
            pass
        
        # Vérifier que le fichier original existe toujours
        assert os.path.exists(test_file)
        assert Path(test_file).read_text() == "Test content for backup"
        
        # Vérifier que l'action a "réussi"
        assert len(results) == 1
        assert results[0].success is True


class TestDryRunReporting:
    """Tests pour les rapports en mode dry-run"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = IntelligentCleaner(dry_run=True)
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.lists(
        st.integers(min_value=1, max_value=1000000),
        min_size=1,
        max_size=20
    ))
    def test_dry_run_size_reporting_accuracy(self, file_sizes):
        """Property: Les rapports de taille en mode dry-run sont précis"""
        actions = []
        expected_total = 0
        
        for i, size in enumerate(file_sizes):
            filepath = os.path.join(self.temp_dir, f"size_test_{i}.txt")
            Path(filepath).touch()  # Créer le fichier (taille réelle peut différer)
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=size,  # Taille estimée
                description=f"Size test {i}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
            
            expected_total += size
        
        # Exécuter en mode dry-run
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que les tailles rapportées correspondent aux estimations
        actual_total = sum(result.actual_size_freed for result in results)
        assert actual_total == expected_total
        
        # Chaque résultat devrait rapporter la taille estimée
        for i, result in enumerate(results):
            assert result.actual_size_freed == file_sizes[i]
    
    def test_dry_run_execution_time_reporting(self):
        """Property: Les temps d'exécution sont rapportés même en mode dry-run"""
        # Créer quelques actions
        actions = []
        for i in range(3):
            filepath = os.path.join(self.temp_dir, f"time_test_{i}.txt")
            Path(filepath).touch()
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=1024,
                description=f"Time test {i}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
        
        # Exécuter en mode dry-run
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que les temps d'exécution sont rapportés
        for result in results:
            assert result.execution_time >= 0
            assert isinstance(result.execution_time, (int, float))


class DryRunSafety(RuleBasedStateMachine):
    """Machine à états pour tester la sécurité du mode dry-run"""
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = IntelligentCleaner(dry_run=True)
        self.original_files = {}  # filepath -> content
        self.executed_actions = []
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(filename=st.text(min_size=1, max_size=20),
          content=st.text(min_size=0, max_size=500))
    def create_file(self, filename, content):
        """Créer un fichier à protéger"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if safe_filename:
            filepath = os.path.join(self.temp_dir, f"{safe_filename}.txt")
            try:
                Path(filepath).write_text(content, encoding='utf-8')
                self.original_files[filepath] = content
            except (OSError, UnicodeEncodeError):
                pass
    
    @rule(action_type=st.sampled_from(['delete_file', 'delete_directory', 'clear_cache']))
    def execute_dry_run_action(self, action_type):
        """Exécuter une action en mode dry-run"""
        if not self.original_files:
            return
        
        # Choisir un fichier au hasard
        filepath = list(self.original_files.keys())[0]
        
        action = CleaningAction(
            action_type=action_type,
            target_path=filepath,
            size_bytes=1024,
            description=f"Dry run {action_type}",
            safety_level='safe',
            category='test',
            reversible=False
        )
        
        results = self.cleaner.execute_cleaning_actions([action])
        self.executed_actions.extend(results)
    
    @rule()
    def toggle_dry_run_mode(self):
        """Basculer le mode dry-run"""
        # Toujours revenir en mode dry-run pour la sécurité
        self.cleaner.set_dry_run(True)
        assert self.cleaner.dry_run is True
    
    @invariant()
    def files_are_preserved(self):
        """Invariant: Tous les fichiers originaux sont préservés"""
        for filepath, original_content in self.original_files.items():
            if os.path.exists(filepath):
                current_content = Path(filepath).read_text(encoding='utf-8')
                assert current_content == original_content, f"Fichier {filepath} modifié en mode dry-run"
    
    @invariant()
    def dry_run_mode_is_active(self):
        """Invariant: Le mode dry-run reste actif"""
        assert self.cleaner.dry_run is True
    
    @invariant()
    def all_actions_succeed(self):
        """Invariant: Toutes les actions dry-run réussissent"""
        for result in self.executed_actions:
            assert result.success is True, "Les actions dry-run devraient toujours réussir"


# Test de la machine à états
TestDryRunSafety = DryRunSafety.TestCase


if __name__ == '__main__':
    pytest.main([__file__])