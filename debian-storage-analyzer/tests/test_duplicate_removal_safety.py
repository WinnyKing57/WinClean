# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import stat
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.analyzer.duplicate_detector import DuplicateDetector, DuplicateGroup


class TestDuplicateRemovalSafety:
    """Tests de sécurité pour la suppression de doublons"""
    
    def setup_method(self):
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_never_delete_all_duplicates(self):
        """Property: Ne jamais supprimer tous les fichiers d'un groupe de doublons"""
        content = "duplicate content"
        
        # Créer plusieurs fichiers identiques
        files = []
        for i in range(5):
            filepath = os.path.join(self.temp_dir, f"file_{i}.txt")
            Path(filepath).write_text(content)
            files.append(filepath)
        
        # Créer un groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # Tester toutes les stratégies
        strategies = ['first', 'shortest_path', 'newest', 'oldest']
        
        for strategy in strategies:
            files_to_delete = self.detector.select_files_for_deletion(duplicate_group, strategy)
            
            # Vérifier qu'au moins un fichier est conservé
            assert len(files_to_delete) == len(files) - 1
            assert len(files_to_delete) < len(files)
            
            # Vérifier qu'aucun fichier n'est à la fois dans la liste de suppression et conservé
            kept_files = set(files) - set(files_to_delete)
            assert len(kept_files) == 1
            assert len(set(files_to_delete) & kept_files) == 0
    
    def test_preserve_file_with_special_permissions(self):
        """Property: Préserver les fichiers avec des permissions spéciales"""
        content = "duplicate content"
        
        # Créer des fichiers avec différentes permissions
        normal_file = os.path.join(self.temp_dir, "normal.txt")
        readonly_file = os.path.join(self.temp_dir, "readonly.txt")
        executable_file = os.path.join(self.temp_dir, "executable.txt")
        
        Path(normal_file).write_text(content)
        Path(readonly_file).write_text(content)
        Path(executable_file).write_text(content)
        
        # Modifier les permissions
        os.chmod(readonly_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # Lecture seule
        os.chmod(executable_file, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)  # Exécutable
        
        files = [normal_file, readonly_file, executable_file]
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # La sélection devrait fonctionner même avec des permissions spéciales
        files_to_delete = self.detector.select_files_for_deletion(duplicate_group, 'first')
        
        assert len(files_to_delete) == 2
        assert len(set(files) - set(files_to_delete)) == 1
    
    @given(st.integers(min_value=2, max_value=20))
    def test_deletion_list_completeness(self, num_files):
        """Property: La liste de suppression est complète et cohérente"""
        content = "duplicate content"
        
        # Créer plusieurs fichiers identiques
        files = []
        for i in range(num_files):
            filepath = os.path.join(self.temp_dir, f"file_{i:03d}.txt")
            Path(filepath).write_text(content)
            files.append(filepath)
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (num_files - 1)
        )
        
        # Tester la sélection
        files_to_delete = self.detector.select_files_for_deletion(duplicate_group, 'first')
        
        # Vérifications de sécurité
        assert len(files_to_delete) == num_files - 1  # Exactement n-1 fichiers à supprimer
        assert len(set(files_to_delete)) == len(files_to_delete)  # Pas de doublons dans la liste
        
        # Tous les fichiers à supprimer doivent être dans le groupe original
        for filepath in files_to_delete:
            assert filepath in files
        
        # Le fichier conservé ne doit pas être dans la liste de suppression
        kept_files = set(files) - set(files_to_delete)
        assert len(kept_files) == 1
    
    def test_verify_before_deletion(self):
        """Property: Vérifier que les fichiers sont vraiment identiques avant suppression"""
        # Créer des fichiers avec le même contenu initial
        content = "initial content"
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        Path(file1).write_text(content)
        Path(file2).write_text(content)
        
        # Vérifier qu'ils sont identiques
        assert self.detector.verify_duplicates([file1, file2]) is True
        
        # Modifier un fichier
        Path(file2).write_text("modified content")
        
        # Vérifier qu'ils ne sont plus identiques
        assert self.detector.verify_duplicates([file1, file2]) is False
    
    def test_handle_missing_files_gracefully(self):
        """Property: Gérer gracieusement les fichiers manquants"""
        content = "duplicate content"
        
        # Créer des fichiers
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        file3 = os.path.join(self.temp_dir, "file3.txt")  # Sera supprimé
        
        Path(file1).write_text(content)
        Path(file2).write_text(content)
        Path(file3).write_text(content)
        
        files = [file1, file2, file3]
        
        # Supprimer un fichier pour simuler une suppression externe
        os.remove(file3)
        
        # La vérification devrait gérer le fichier manquant
        result = self.detector.verify_duplicates(files)
        # Le résultat peut être False car un fichier est manquant
        assert isinstance(result, bool)
        
        # La vérification des fichiers existants devrait fonctionner
        existing_files = [f for f in files if os.path.exists(f)]
        if len(existing_files) >= 2:
            assert self.detector.verify_duplicates(existing_files) is True
    
    def test_empty_group_safety(self):
        """Property: Gérer les groupes vides en toute sécurité"""
        # Créer un groupe vide
        empty_group = DuplicateGroup(
            hash_value="empty_hash",
            file_size=0,
            file_paths=[],
            total_wasted_space=0
        )
        
        # La sélection ne devrait rien retourner
        files_to_delete = self.detector.select_files_for_deletion(empty_group, 'first')
        assert len(files_to_delete) == 0
        
        # La vérification devrait retourner True pour une liste vide
        assert self.detector.verify_duplicates([]) is True
    
    def test_single_file_group_safety(self):
        """Property: Gérer les groupes à un seul fichier en toute sécurité"""
        content = "single file content"
        filepath = os.path.join(self.temp_dir, "single.txt")
        Path(filepath).write_text(content)
        
        # Créer un groupe avec un seul fichier
        single_group = DuplicateGroup(
            hash_value="single_hash",
            file_size=len(content.encode('utf-8')),
            file_paths=[filepath],
            total_wasted_space=0
        )
        
        # Aucun fichier ne devrait être sélectionné pour suppression
        files_to_delete = self.detector.select_files_for_deletion(single_group, 'first')
        assert len(files_to_delete) == 0
        
        # La vérification d'un seul fichier devrait retourner True
        assert self.detector.verify_duplicates([filepath]) is True


class TestDeletionStrategySafety:
    """Tests de sécurité pour les stratégies de suppression"""
    
    def setup_method(self):
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.sampled_from(['first', 'shortest_path', 'newest', 'oldest', 'invalid_strategy']))
    def test_strategy_robustness(self, strategy):
        """Property: Les stratégies sont robustes aux entrées invalides"""
        content = "test content"
        
        # Créer des fichiers de test
        files = []
        for i in range(3):
            filepath = os.path.join(self.temp_dir, f"file_{i}.txt")
            Path(filepath).write_text(content)
            files.append(filepath)
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # Tester la stratégie (même invalide)
        files_to_delete = self.detector.select_files_for_deletion(duplicate_group, strategy)
        
        # Vérifications de sécurité de base
        assert isinstance(files_to_delete, list)
        assert len(files_to_delete) <= len(files) - 1  # Au maximum n-1 fichiers
        
        # Tous les fichiers à supprimer doivent être dans le groupe original
        for filepath in files_to_delete:
            assert filepath in files
    
    def test_shortest_path_strategy_safety(self):
        """Property: La stratégie 'shortest_path' est sûre"""
        content = "duplicate content"
        
        # Créer des fichiers avec des chemins de longueurs différentes
        short_file = os.path.join(self.temp_dir, "a.txt")
        medium_file = os.path.join(self.temp_dir, "medium_name.txt")
        
        # Créer un sous-répertoire pour un chemin plus long
        subdir = os.path.join(self.temp_dir, "subdirectory")
        os.makedirs(subdir)
        long_file = os.path.join(subdir, "very_long_filename.txt")
        
        files = [short_file, medium_file, long_file]
        
        for filepath in files:
            Path(filepath).write_text(content)
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # Tester la stratégie shortest_path
        files_to_delete = self.detector.select_files_for_deletion(duplicate_group, 'shortest_path')
        
        # Le fichier avec le chemin le plus court devrait être conservé
        kept_files = set(files) - set(files_to_delete)
        kept_file = next(iter(kept_files))
        
        # Vérifier que c'est bien le plus court
        assert len(kept_file) == min(len(f) for f in files)
        assert kept_file == short_file
    
    def test_newest_oldest_strategy_safety(self):
        """Property: Les stratégies 'newest' et 'oldest' sont sûres"""
        content = "duplicate content"
        
        # Créer des fichiers avec des temps de modification différents
        files = []
        for i in range(3):
            filepath = os.path.join(self.temp_dir, f"file_{i}.txt")
            Path(filepath).write_text(content)
            files.append(filepath)
            
            # Définir des temps de modification différents
            mtime = 1000000 + i * 1000
            os.utime(filepath, (mtime, mtime))
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # Tester la stratégie 'newest'
        files_to_delete_newest = self.detector.select_files_for_deletion(duplicate_group, 'newest')
        kept_newest = set(files) - set(files_to_delete_newest)
        
        # Tester la stratégie 'oldest'
        files_to_delete_oldest = self.detector.select_files_for_deletion(duplicate_group, 'oldest')
        kept_oldest = set(files) - set(files_to_delete_oldest)
        
        # Vérifications
        assert len(kept_newest) == 1
        assert len(kept_oldest) == 1
        assert len(files_to_delete_newest) == len(files) - 1
        assert len(files_to_delete_oldest) == len(files) - 1
        
        # Les fichiers conservés devraient être différents (sauf cas particulier)
        if len(set(os.path.getmtime(f) for f in files)) > 1:  # Si les temps sont différents
            assert kept_newest != kept_oldest


class DuplicateRemovalSafety(RuleBasedStateMachine):
    """Machine à états pour tester la sécurité de suppression des doublons"""
    
    def __init__(self):
        super().__init__()
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
        self.duplicate_groups = {}
        self.all_files = set()
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(content=st.text(min_size=1, max_size=50),
          num_files=st.integers(min_value=2, max_value=5))
    def create_duplicate_group(self, content, num_files):
        """Créer un groupe de fichiers dupliqués"""
        group_id = len(self.duplicate_groups)
        files = []
        
        for i in range(num_files):
            filename = f"group_{group_id}_file_{i}.txt"
            filepath = os.path.join(self.temp_dir, filename)
            
            try:
                Path(filepath).write_text(content, encoding='utf-8')
                files.append(filepath)
                self.all_files.add(filepath)
            except OSError:
                continue
        
        if len(files) >= 2:
            file_size = len(content.encode('utf-8'))
            self.duplicate_groups[group_id] = DuplicateGroup(
                hash_value=f"hash_{group_id}",
                file_size=file_size,
                file_paths=files,
                total_wasted_space=file_size * (len(files) - 1)
            )
    
    @rule(strategy=st.sampled_from(['first', 'shortest_path', 'newest', 'oldest']))
    def test_deletion_selection(self, strategy):
        """Tester la sélection de fichiers pour suppression"""
        for group_id, group in self.duplicate_groups.items():
            files_to_delete = self.detector.select_files_for_deletion(group, strategy)
            
            # Vérifications de sécurité
            assert len(files_to_delete) < len(group.file_paths)  # Ne pas tout supprimer
            assert len(files_to_delete) == len(group.file_paths) - 1  # Exactement n-1
            
            # Tous les fichiers à supprimer doivent exister dans le groupe
            for filepath in files_to_delete:
                assert filepath in group.file_paths
    
    @invariant()
    def files_exist_on_disk(self):
        """Invariant: Les fichiers référencés existent sur le disque"""
        for group in self.duplicate_groups.values():
            existing_files = [f for f in group.file_paths if os.path.exists(f)]
            # Au moins un fichier du groupe doit exister
            assert len(existing_files) >= 1
    
    @invariant()
    def duplicate_groups_valid(self):
        """Invariant: Les groupes de doublons sont valides"""
        for group in self.duplicate_groups.values():
            assert len(group.file_paths) >= 2
            assert group.file_size >= 0
            assert group.total_wasted_space >= 0
            assert group.total_wasted_space == group.file_size * (len(group.file_paths) - 1)


# Test de la machine à états
TestDuplicateRemovalSafety = DuplicateRemovalSafety.TestCase


if __name__ == '__main__':
    pytest.main([__file__])