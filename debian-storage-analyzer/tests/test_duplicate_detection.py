# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import hashlib
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.analyzer.duplicate_detector import DuplicateDetector, DuplicateGroup


class TestDuplicateDetector:
    """Tests unitaires pour DuplicateDetector"""
    
    def setup_method(self):
        self.detector = DuplicateDetector(max_workers=2)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.detector.clear_cache()
    
    def test_empty_directory_no_duplicates(self):
        """Property: Un répertoire vide n'a pas de doublons"""
        duplicates = self.detector.find_duplicates(self.temp_dir)
        assert len(duplicates) == 0
    
    def test_single_file_no_duplicates(self):
        """Property: Un seul fichier n'a pas de doublons"""
        test_file = os.path.join(self.temp_dir, "single.txt")
        Path(test_file).write_text("unique content")
        
        duplicates = self.detector.find_duplicates(self.temp_dir)
        assert len(duplicates) == 0
    
    @given(st.text(min_size=1, max_size=1000))
    def test_identical_content_creates_duplicates(self, content):
        """Property: Des fichiers avec contenu identique sont détectés comme doublons"""
        # Nettoyer le répertoire pour chaque exemple Hypothesis
        shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        # Créer deux fichiers avec le même contenu
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        Path(file1).write_text(content, encoding='utf-8')
        Path(file2).write_text(content, encoding='utf-8')
        
        duplicates = self.detector.find_duplicates(self.temp_dir)
        
        if len(content.encode('utf-8')) > 0:  # Ignorer les fichiers vides
            assert len(duplicates) == 1
            duplicate_group = next(iter(duplicates.values()))
            assert len(duplicate_group.file_paths) == 2
            assert file1 in duplicate_group.file_paths
            assert file2 in duplicate_group.file_paths
    
    @given(st.text(min_size=1, max_size=500), st.text(min_size=1, max_size=500))
    def test_different_content_no_duplicates(self, content1, content2):
        """Property: Des fichiers avec contenu différent ne sont pas des doublons"""
        assume(content1 != content2)
        
        # Nettoyer le répertoire pour chaque exemple Hypothesis
        shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        Path(file1).write_text(content1, encoding='utf-8')
        Path(file2).write_text(content2, encoding='utf-8')
        
        duplicates = self.detector.find_duplicates(self.temp_dir)
        
        # Ne devrait pas y avoir de doublons
        assert len(duplicates) == 0
    
    @given(st.integers(min_value=3, max_value=10))
    def test_multiple_identical_files(self, num_files):
        """Property: Plusieurs fichiers identiques forment un groupe de doublons"""
        # Nettoyer le répertoire pour chaque exemple Hypothesis
        shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        content = "identical content for all files"
        file_paths = []
        
        for i in range(num_files):
            filepath = os.path.join(self.temp_dir, f"file_{i}.txt")
            Path(filepath).write_text(content)
            file_paths.append(filepath)
        
        duplicates = self.detector.find_duplicates(self.temp_dir)
        
        assert len(duplicates) == 1
        duplicate_group = next(iter(duplicates.values()))
        assert len(duplicate_group.file_paths) == num_files
        
        # Vérifier que tous les fichiers sont dans le groupe
        for filepath in file_paths:
            assert filepath in duplicate_group.file_paths
        
        # Vérifier l'espace gaspillé
        file_size = len(content.encode('utf-8'))
        expected_wasted = file_size * (num_files - 1)
        assert duplicate_group.total_wasted_space == expected_wasted
    
    @given(st.integers(min_value=1, max_value=1000))
    def test_min_size_filter(self, min_size):
        """Property: Le filtre de taille minimale fonctionne correctement"""
        # Nettoyer le répertoire pour chaque exemple Hypothesis
        shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        # Créer un petit fichier
        small_content = "x" * (min_size - 1) if min_size > 1 else ""
        small_file1 = os.path.join(self.temp_dir, "small1.txt")
        small_file2 = os.path.join(self.temp_dir, "small2.txt")
        Path(small_file1).write_text(small_content)
        Path(small_file2).write_text(small_content)
        
        # Créer un gros fichier
        large_content = "x" * (min_size + 10)
        large_file1 = os.path.join(self.temp_dir, "large1.txt")
        large_file2 = os.path.join(self.temp_dir, "large2.txt")
        Path(large_file1).write_text(large_content)
        Path(large_file2).write_text(large_content)
        
        duplicates = self.detector.find_duplicates(self.temp_dir, min_size=min_size)
        
        if min_size > len(small_content.encode('utf-8')):
            # Seuls les gros fichiers devraient être détectés
            assert len(duplicates) <= 1
            if len(duplicates) == 1:
                group = next(iter(duplicates.values()))
                assert large_file1 in group.file_paths
                assert large_file2 in group.file_paths
                assert small_file1 not in group.file_paths
                assert small_file2 not in group.file_paths
        else:
            # Tous les doublons devraient être détectés
            assert len(duplicates) >= 1


class TestDuplicateGroupOperations:
    """Tests pour les opérations sur les groupes de doublons"""
    
    def setup_method(self):
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.sampled_from(['first', 'shortest_path', 'newest', 'oldest']))
    def test_file_selection_strategies(self, strategy):
        """Property: Les stratégies de sélection de fichiers fonctionnent"""
        content = "duplicate content"
        
        # Créer des fichiers avec des chemins de longueurs différentes
        files = [
            os.path.join(self.temp_dir, "a.txt"),
            os.path.join(self.temp_dir, "very_long_filename.txt"),
            os.path.join(self.temp_dir, "subdir", "file.txt")
        ]
        
        # Créer le sous-répertoire
        os.makedirs(os.path.join(self.temp_dir, "subdir"), exist_ok=True)
        
        # Créer les fichiers avec des temps différents
        for i, filepath in enumerate(files):
            Path(filepath).write_text(content)
            # Modifier le temps de modification pour tester newest/oldest
            mtime = 1000000 + i * 1000  # Temps croissants
            os.utime(filepath, (mtime, mtime))
        
        # Créer le groupe de doublons
        file_size = len(content.encode('utf-8'))
        duplicate_group = DuplicateGroup(
            hash_value="test_hash",
            file_size=file_size,
            file_paths=files,
            total_wasted_space=file_size * (len(files) - 1)
        )
        
        # Tester la sélection
        files_to_delete = self.detector.select_files_for_deletion(duplicate_group, strategy)
        
        # Vérifications
        assert len(files_to_delete) == len(files) - 1  # Tous sauf un
        
        # Vérifier qu'aucun fichier n'est à la fois gardé et supprimé
        kept_files = set(files) - set(files_to_delete)
        assert len(kept_files) == 1
        
        # Vérifier la stratégie spécifique
        kept_file = next(iter(kept_files))
        
        if strategy == 'first':
            assert kept_file == files[0]
        elif strategy == 'shortest_path':
            assert kept_file == min(files, key=len)
    
    def test_verify_duplicates_identical_files(self):
        """Property: La vérification confirme les fichiers identiques"""
        content = "identical content"
        
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        Path(file1).write_text(content)
        Path(file2).write_text(content)
        
        result = self.detector.verify_duplicates([file1, file2])
        assert result is True
    
    def test_verify_duplicates_different_files(self):
        """Property: La vérification rejette les fichiers différents"""
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        Path(file1).write_text("content 1")
        Path(file2).write_text("content 2")
        
        result = self.detector.verify_duplicates([file1, file2])
        assert result is False
    
    def test_verify_duplicates_single_file(self):
        """Property: La vérification d'un seul fichier retourne True"""
        file1 = os.path.join(self.temp_dir, "file1.txt")
        Path(file1).write_text("content")
        
        result = self.detector.verify_duplicates([file1])
        assert result is True
    
    def test_verify_duplicates_empty_list(self):
        """Property: La vérification d'une liste vide retourne True"""
        result = self.detector.verify_duplicates([])
        assert result is True


class TestDuplicateSummary:
    """Tests pour le résumé des doublons"""
    
    def setup_method(self):
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_empty_summary(self):
        """Property: Le résumé d'une analyse vide est correct"""
        summary = self.detector.get_duplicate_summary({})
        
        assert summary['total_duplicate_groups'] == 0
        assert summary['total_duplicate_files'] == 0
        assert summary['total_wasted_space'] == 0
        assert summary['largest_duplicate_group'] is None
        assert summary['most_wasted_space_group'] is None
    
    @given(st.integers(min_value=2, max_value=10))
    def test_summary_calculations(self, num_duplicates):
        """Property: Les calculs du résumé sont corrects"""
        content = "duplicate content"
        file_size = len(content.encode('utf-8'))
        
        # Créer des groupes de doublons
        duplicate_groups = {}
        total_files = 0
        total_wasted = 0
        
        for group_id in range(2):  # 2 groupes
            group_files = []
            for file_id in range(num_duplicates):
                filepath = os.path.join(self.temp_dir, f"group_{group_id}_file_{file_id}.txt")
                Path(filepath).write_text(content)
                group_files.append(filepath)
            
            hash_value = f"hash_{group_id}"
            wasted_space = file_size * (num_duplicates - 1)
            
            duplicate_groups[hash_value] = DuplicateGroup(
                hash_value=hash_value,
                file_size=file_size,
                file_paths=group_files,
                total_wasted_space=wasted_space
            )
            
            total_files += num_duplicates
            total_wasted += wasted_space
        
        # Générer le résumé
        summary = self.detector.get_duplicate_summary(duplicate_groups)
        
        # Vérifications
        assert summary['total_duplicate_groups'] == 2
        assert summary['total_duplicate_files'] == total_files
        assert summary['total_wasted_space'] == total_wasted
        
        # Vérifier les groupes les plus importants
        assert summary['largest_duplicate_group'] is not None
        assert summary['largest_duplicate_group']['file_count'] == num_duplicates
        
        assert summary['most_wasted_space_group'] is not None
        assert summary['most_wasted_space_group']['wasted_space'] == file_size * (num_duplicates - 1)


class TestCacheOperations:
    """Tests pour les opérations de cache"""
    
    def setup_method(self):
        self.detector = DuplicateDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.detector.clear_cache()
    
    def test_cache_consistency(self):
        """Property: Le cache maintient la cohérence"""
        content = "test content for caching"
        filepath = os.path.join(self.temp_dir, "test.txt")
        Path(filepath).write_text(content)
        
        # Premier calcul (mise en cache)
        hash1 = self.detector._calculate_file_hash(filepath)
        
        # Deuxième calcul (depuis le cache)
        hash2 = self.detector._calculate_file_hash(filepath)
        
        assert hash1 == hash2
        assert hash1 is not None
        
        # Vérifier les stats du cache
        stats = self.detector.get_cache_stats()
        assert stats['cached_files'] >= 1
        assert stats['cache_size_bytes'] > 0
    
    def test_cache_clear(self):
        """Property: Le nettoyage du cache fonctionne"""
        content = "test content"
        filepath = os.path.join(self.temp_dir, "test.txt")
        Path(filepath).write_text(content)
        
        # Mettre en cache
        self.detector._calculate_file_hash(filepath)
        
        # Vérifier que le cache n'est pas vide
        stats_before = self.detector.get_cache_stats()
        assert stats_before['cached_files'] > 0
        
        # Nettoyer le cache
        self.detector.clear_cache()
        
        # Vérifier que le cache est vide
        stats_after = self.detector.get_cache_stats()
        assert stats_after['cached_files'] == 0
        assert stats_after['cache_size_bytes'] == 0


class DuplicateDetection(RuleBasedStateMachine):
    """Machine à états pour tester la détection de doublons"""
    
    def __init__(self):
        super().__init__()
        self.detector = DuplicateDetector(max_workers=2)
        self.temp_dir = tempfile.mkdtemp()
        self.created_files = {}  # content -> list of filepaths
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.detector.clear_cache()
    
    @rule(content=st.text(min_size=1, max_size=100), 
          filename=st.text(min_size=1, max_size=20))
    def create_file(self, content, filename):
        """Créer un fichier avec un contenu donné"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if safe_filename:
            filepath = os.path.join(self.temp_dir, f"{safe_filename}.txt")
            try:
                Path(filepath).write_text(content, encoding='utf-8')
                
                if content not in self.created_files:
                    self.created_files[content] = []
                self.created_files[content].append(filepath)
                
            except OSError:
                pass
    
    @rule()
    def find_duplicates(self):
        """Rechercher les doublons"""
        duplicates = self.detector.find_duplicates(self.temp_dir)
        
        # Vérifier la cohérence avec nos données
        expected_groups = sum(1 for files in self.created_files.values() if len(files) > 1)
        
        # Le nombre de groupes détectés ne devrait pas dépasser le nombre attendu
        assert len(duplicates) <= expected_groups
        
        # Chaque groupe doit avoir au moins 2 fichiers
        for group in duplicates.values():
            assert len(group.file_paths) >= 2
            assert group.total_wasted_space >= 0
    
    @invariant()
    def hash_consistency(self):
        """Invariant: Les hashes sont cohérents"""
        # Vérifier que les fichiers avec le même contenu ont le même hash
        for content, filepaths in self.created_files.items():
            if len(filepaths) > 1:
                hashes = []
                for filepath in filepaths:
                    if os.path.exists(filepath):
                        file_hash = self.detector._calculate_file_hash(filepath)
                        if file_hash:
                            hashes.append(file_hash)
                
                # Tous les hashes devraient être identiques
                if len(hashes) > 1:
                    assert all(h == hashes[0] for h in hashes)


# Test de la machine à états
TestDuplicateDetection = DuplicateDetection.TestCase


if __name__ == '__main__':
    pytest.main([__file__])