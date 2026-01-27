# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.analyzer.file_categorizer import FileCategorizer, CategoryStats


class TestFileCategorizer:
    """Tests unitaires pour FileCategorizer"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.text(min_size=1, max_size=50))
    def test_categorize_nonexistent_file_returns_unknown(self, filename):
        """Property: Les fichiers inexistants retournent 'unknown'"""
        assume(not os.path.exists(filename))
        result = self.categorizer.categorize_file(filename)
        assert result == 'unknown'
    
    @given(st.sampled_from([
        '.jpg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff'
    ]))
    def test_image_extensions_categorized_correctly(self, extension):
        """Property: Les extensions d'images sont correctement catégorisées"""
        # Créer un fichier temporaire avec l'extension
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'images'
    
    @given(st.sampled_from([
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'
    ]))
    def test_video_extensions_categorized_correctly(self, extension):
        """Property: Les extensions vidéo sont correctement catégorisées"""
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'videos'
    
    @given(st.sampled_from([
        '.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a'
    ]))
    def test_audio_extensions_categorized_correctly(self, extension):
        """Property: Les extensions audio sont correctement catégorisées"""
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'audio'
    
    @given(st.sampled_from([
        '.pdf', '.doc', '.docx', '.txt', '.odt', '.rtf', '.md'
    ]))
    def test_document_extensions_categorized_correctly(self, extension):
        """Property: Les extensions de documents sont correctement catégorisées"""
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'documents'
    
    def test_directory_categorized_as_directories(self):
        """Property: Les répertoires sont catégorisés comme 'directories'"""
        test_dir = os.path.join(self.temp_dir, "test_directory")
        os.makedirs(test_dir)
        
        result = self.categorizer.categorize_file(test_dir)
        assert result == 'directories'
    
    @given(st.text(min_size=1, max_size=20).filter(lambda x: '.' not in x))
    def test_files_without_extension_categorized_as_other(self, filename):
        """Property: Les fichiers sans extension sont catégorisés comme 'other'"""
        assume(not filename.startswith('.'))
        test_file = os.path.join(self.temp_dir, filename)
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'other'
    
    @given(st.text(min_size=2, max_size=10).filter(lambda x: x.startswith('.')))
    def test_unknown_extensions_categorized_as_other(self, extension):
        """Property: Les extensions inconnues sont catégorisées comme 'other'"""
        # S'assurer que l'extension n'est pas dans nos catégories connues
        known_extensions = set()
        for category_config in self.categorizer.categories.values():
            known_extensions.update(category_config['extensions'])
        
        assume(extension.lower() not in known_extensions)
        
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        result = self.categorizer.categorize_file(test_file)
        assert result == 'other'


class TestCategoryAnalysis:
    """Tests pour l'analyse de catégories"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.sampled_from(['.jpg', '.mp4', '.mp3', '.pdf', '.txt'])
        ),
        min_size=1,
        max_size=20
    ))
    def test_category_stats_consistency(self, file_specs):
        """Property: Les statistiques de catégories sont cohérentes"""
        # Créer les fichiers de test
        created_files = []
        for filename, extension in file_specs:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if safe_filename:
                test_file = os.path.join(self.temp_dir, f"{safe_filename}{extension}")
                try:
                    Path(test_file).touch()
                    created_files.append(test_file)
                except OSError:
                    continue
        
        if not created_files:
            return  # Skip si aucun fichier créé
        
        # Analyser le répertoire
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Vérifications de cohérence
        total_files = sum(stat.file_count for stat in stats.values())
        total_percentage = sum(stat.percentage for stat in stats.values())
        
        # Le nombre total de fichiers doit correspondre aux fichiers créés
        assert total_files >= len(created_files)  # >= car peut inclure des dossiers
        
        # Les pourcentages doivent totaliser ~100% (avec tolérance pour les arrondis)
        assert abs(total_percentage - 100.0) < 1.0
        
        # Chaque catégorie doit avoir des statistiques valides
        for category, stat in stats.items():
            assert stat.file_count >= 0
            assert stat.total_size >= 0
            assert 0 <= stat.percentage <= 100
            assert isinstance(stat.extensions, set)
    
    def test_empty_directory_analysis(self):
        """Property: L'analyse d'un répertoire vide retourne des stats vides"""
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Un répertoire vide ne devrait pas avoir de statistiques
        assert len(stats) == 0 or all(stat.file_count == 0 for stat in stats.values())
    
    @given(st.integers(min_value=1, max_value=10))
    def test_nested_directory_analysis(self, depth):
        """Property: L'analyse fonctionne avec des répertoires imbriqués"""
        # Créer une structure imbriquée
        current_dir = self.temp_dir
        for i in range(depth):
            current_dir = os.path.join(current_dir, f"level_{i}")
            os.makedirs(current_dir, exist_ok=True)
            
            # Ajouter un fichier à chaque niveau
            test_file = os.path.join(current_dir, f"file_{i}.txt")
            Path(test_file).touch()
        
        # Analyser depuis la racine
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Doit trouver les fichiers et dossiers
        assert len(stats) > 0
        
        # Doit avoir des documents (fichiers .txt)
        if 'documents' in stats:
            assert stats['documents'].file_count >= depth
        
        # Doit avoir des répertoires
        if 'directories' in stats:
            assert stats['directories'].file_count >= depth


class TestCustomCategories:
    """Tests pour les catégories personnalisées"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        st.text(min_size=1, max_size=20),
        st.sets(st.text(min_size=2, max_size=10).filter(lambda x: x.startswith('.'))),
        st.sets(st.text(min_size=1, max_size=30))
    )
    def test_custom_category_addition(self, category_name, extensions, mimetypes):
        """Property: Les catégories personnalisées fonctionnent correctement"""
        assume(category_name not in self.categorizer.categories)
        assume(len(extensions) > 0)
        
        # Ajouter la catégorie personnalisée
        self.categorizer.add_custom_category(category_name, extensions, mimetypes)
        
        # Vérifier qu'elle a été ajoutée
        assert category_name in self.categorizer.categories
        assert self.categorizer.categories[category_name]['extensions'] == extensions
        assert self.categorizer.categories[category_name]['mimetypes'] == mimetypes
        
        # Tester avec un fichier ayant une des extensions
        if extensions:
            test_extension = next(iter(extensions))
            test_file = os.path.join(self.temp_dir, f"test{test_extension}")
            Path(test_file).touch()
            
            result = self.categorizer.categorize_file(test_file)
            assert result == category_name


class TestFileTypeSummary:
    """Tests pour le résumé des types de fichiers"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.sampled_from(['.jpg', '.mp4', '.mp3', '.pdf', '.py', '.zip']))
    def test_file_type_summary_completeness(self, extension):
        """Property: Le résumé de type de fichier est complet"""
        test_file = os.path.join(self.temp_dir, f"test{extension}")
        Path(test_file).touch()
        
        summary = self.categorizer.get_file_type_summary(test_file)
        
        # Vérifier que tous les champs requis sont présents
        required_fields = ['category', 'mime_type', 'encoding', 'extension', 'icon', 'color']
        for field in required_fields:
            assert field in summary
            assert summary[field] is not None
        
        # Vérifier la cohérence
        assert summary['extension'] == extension.lower()
        assert summary['category'] != 'unknown'  # Fichier existant avec extension connue
        assert summary['icon'].startswith(('image-', 'video-', 'audio-', 'text-', 'x-', 'application-', 'folder', 'package-', 'font-'))
        assert summary['color'].startswith('#')
        assert len(summary['color']) == 7  # Format hexadécimal


class FileCategorization(RuleBasedStateMachine):
    """Machine à états pour tester les propriétés de catégorisation"""
    
    def __init__(self):
        super().__init__()
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
        self.created_files = []
        self.created_dirs = []
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(filename=st.text(min_size=1, max_size=20), 
          extension=st.sampled_from(['.jpg', '.mp4', '.mp3', '.pdf', '.txt', '.py', '.zip']))
    def create_file(self, filename, extension):
        """Créer un fichier avec une extension donnée"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if safe_filename:
            filepath = os.path.join(self.temp_dir, f"{safe_filename}{extension}")
            try:
                Path(filepath).touch()
                self.created_files.append(filepath)
            except OSError:
                pass
    
    @rule(dirname=st.text(min_size=1, max_size=20))
    def create_directory(self, dirname):
        """Créer un répertoire"""
        safe_dirname = "".join(c for c in dirname if c.isalnum() or c in "._-")
        if safe_dirname:
            dirpath = os.path.join(self.temp_dir, safe_dirname)
            try:
                os.makedirs(dirpath, exist_ok=True)
                self.created_dirs.append(dirpath)
            except OSError:
                pass
    
    @rule()
    def analyze_categories(self):
        """Analyser les catégories du répertoire"""
        if self.created_files or self.created_dirs:
            stats = self.categorizer.analyze_directory_categories(self.temp_dir)
            
            # Vérifier la cohérence des statistiques
            if stats:
                total_percentage = sum(stat.percentage for stat in stats.values())
                assert abs(total_percentage - 100.0) < 1.0
    
    @invariant()
    def categorization_is_consistent(self):
        """Invariant: La catégorisation est cohérente"""
        for filepath in self.created_files:
            if os.path.exists(filepath):
                category1 = self.categorizer.categorize_file(filepath)
                category2 = self.categorizer.categorize_file(filepath)
                assert category1 == category2  # Même fichier, même catégorie
    
    @invariant()
    def directories_categorized_correctly(self):
        """Invariant: Les répertoires sont toujours catégorisés comme 'directories'"""
        for dirpath in self.created_dirs:
            if os.path.exists(dirpath):
                category = self.categorizer.categorize_file(dirpath)
                assert category == 'directories'


# Test de la machine à états
TestFileCategorization = FileCategorization.TestCase


if __name__ == '__main__':
    pytest.main([__file__])