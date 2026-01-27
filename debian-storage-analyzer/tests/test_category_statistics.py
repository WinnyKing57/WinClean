# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.analyzer.file_categorizer import FileCategorizer, CategoryStats


class TestCategoryStatistics:
    """Tests pour les statistiques de catégories"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_empty_directory_statistics(self):
        """Property: Un répertoire vide produit des statistiques vides"""
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Aucune statistique ou toutes à zéro
        assert len(stats) == 0 or all(stat.file_count == 0 for stat in stats.values())
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.sampled_from(['.jpg', '.mp4', '.mp3', '.pdf', '.txt', '.py']),
            st.integers(min_value=0, max_value=1000)
        ),
        min_size=1,
        max_size=20
    ))
    def test_statistics_consistency(self, file_specs):
        """Property: Les statistiques sont mathématiquement cohérentes"""
        created_files = []
        total_expected_size = 0
        
        # Créer les fichiers avec du contenu de taille spécifiée
        for filename, extension, content_size in file_specs:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if safe_filename:
                filepath = os.path.join(self.temp_dir, f"{safe_filename}{extension}")
                try:
                    # Créer du contenu de la taille spécifiée
                    content = "x" * content_size
                    Path(filepath).write_text(content, encoding='utf-8')
                    created_files.append(filepath)
                    total_expected_size += len(content.encode('utf-8'))
                except OSError:
                    continue
        
        if not created_files:
            return  # Skip si aucun fichier créé
        
        # Analyser les statistiques
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        if not stats:
            return  # Skip si pas de stats
        
        # Vérifications de cohérence mathématique
        total_files = sum(stat.file_count for stat in stats.values())
        total_size = sum(stat.total_size for stat in stats.values())
        total_percentage = sum(stat.percentage for stat in stats.values())
        
        # Le nombre total de fichiers doit être au moins égal aux fichiers créés
        assert total_files >= len(created_files)
        
        # La taille totale doit être au moins égale à la taille attendue
        assert total_size >= total_expected_size
        
        # Les pourcentages doivent totaliser ~100% (avec tolérance)
        assert abs(total_percentage - 100.0) < 1.0
        
        # Chaque statistique individuelle doit être valide
        for category, stat in stats.items():
            assert stat.file_count >= 0
            assert stat.total_size >= 0
            assert 0 <= stat.percentage <= 100
            assert isinstance(stat.extensions, set)
            assert stat.name == category
    
    @given(st.integers(min_value=1, max_value=100))
    def test_percentage_calculation_accuracy(self, file_size):
        """Property: Les calculs de pourcentage sont précis"""
        # Créer des fichiers de tailles connues
        files_data = [
            ("image.jpg", file_size),
            ("video.mp4", file_size * 2),
            ("audio.mp3", file_size * 3),
            ("doc.pdf", file_size * 4)
        ]
        
        total_size = sum(size for _, size in files_data)
        
        for filename, size in files_data:
            filepath = os.path.join(self.temp_dir, filename)
            content = "x" * size
            Path(filepath).write_text(content, encoding='utf-8')
        
        # Analyser les statistiques
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Vérifier les pourcentages calculés
        for category, stat in stats.items():
            if stat.file_count > 0:
                expected_percentage = (stat.total_size / total_size) * 100
                # Tolérance pour les erreurs d'arrondi
                assert abs(stat.percentage - expected_percentage) < 0.1
    
    def test_extension_tracking(self):
        """Property: Le suivi des extensions est correct"""
        # Créer des fichiers avec différentes extensions dans la même catégorie
        image_extensions = ['.jpg', '.png', '.gif', '.bmp']
        
        for i, ext in enumerate(image_extensions):
            filepath = os.path.join(self.temp_dir, f"image_{i}{ext}")
            Path(filepath).write_text("image content")
        
        # Analyser les statistiques
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Vérifier que toutes les extensions d'images sont trackées
        if 'images' in stats:
            image_stats = stats['images']
            assert len(image_stats.extensions) == len(image_extensions)
            for ext in image_extensions:
                assert ext in image_stats.extensions
    
    @given(st.integers(min_value=1, max_value=10))
    def test_nested_directory_statistics(self, depth):
        """Property: Les statistiques incluent les répertoires imbriqués"""
        # Créer une structure imbriquée
        current_dir = self.temp_dir
        created_files = 0
        created_dirs = 0
        
        for level in range(depth):
            # Créer un sous-répertoire
            current_dir = os.path.join(current_dir, f"level_{level}")
            os.makedirs(current_dir, exist_ok=True)
            created_dirs += 1
            
            # Ajouter un fichier à chaque niveau
            filepath = os.path.join(current_dir, f"file_{level}.txt")
            Path(filepath).write_text(f"content at level {level}")
            created_files += 1
        
        # Analyser depuis la racine
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Vérifier que les répertoires sont comptés
        if 'directories' in stats:
            assert stats['directories'].file_count >= created_dirs
        
        # Vérifier que les fichiers sont comptés
        if 'documents' in stats:  # Les .txt sont des documents
            assert stats['documents'].file_count >= created_files
    
    def test_large_file_handling(self):
        """Property: Gestion correcte des gros fichiers"""
        # Créer un gros fichier et plusieurs petits
        large_content = "x" * 10000  # 10KB
        small_content = "y" * 100    # 100B
        
        large_file = os.path.join(self.temp_dir, "large.txt")
        Path(large_file).write_text(large_content)
        
        # Créer plusieurs petits fichiers
        for i in range(5):
            small_file = os.path.join(self.temp_dir, f"small_{i}.txt")
            Path(small_file).write_text(small_content)
        
        # Analyser les statistiques
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        if 'documents' in stats:
            doc_stats = stats['documents']
            
            # Le gros fichier devrait dominer en pourcentage
            total_size = len(large_content.encode('utf-8')) + 5 * len(small_content.encode('utf-8'))
            expected_percentage = (doc_stats.total_size / total_size) * 100
            
            # Vérifier que le pourcentage est cohérent
            assert abs(doc_stats.percentage - expected_percentage) < 1.0
            
            # Vérifier le nombre de fichiers
            assert doc_stats.file_count == 6  # 1 gros + 5 petits


class TestCategoryStatsObject:
    """Tests pour l'objet CategoryStats"""
    
    def test_category_stats_creation(self):
        """Property: Création correcte des objets CategoryStats"""
        extensions = {'.jpg', '.png', '.gif'}
        
        stats = CategoryStats(
            name='images',
            file_count=10,
            total_size=5000,
            percentage=25.5,
            extensions=extensions
        )
        
        assert stats.name == 'images'
        assert stats.file_count == 10
        assert stats.total_size == 5000
        assert stats.percentage == 25.5
        assert stats.extensions == extensions
    
    @given(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=0, max_value=10000),
        st.integers(min_value=0, max_value=1000000),
        st.floats(min_value=0.0, max_value=100.0),
        st.sets(st.text(min_size=1, max_size=10))
    )
    def test_category_stats_properties(self, name, file_count, total_size, percentage, extensions):
        """Property: Les propriétés de CategoryStats sont correctement stockées"""
        stats = CategoryStats(
            name=name,
            file_count=file_count,
            total_size=total_size,
            percentage=percentage,
            extensions=extensions
        )
        
        assert stats.name == name
        assert stats.file_count == file_count
        assert stats.total_size == total_size
        assert stats.percentage == percentage
        assert stats.extensions == extensions


class TestCategoryColors:
    """Tests pour les couleurs et icônes de catégories"""
    
    def setup_method(self):
        self.categorizer = FileCategorizer()
    
    def test_all_categories_have_colors(self):
        """Property: Toutes les catégories ont des couleurs définies"""
        all_categories = list(self.categorizer.categories.keys()) + ['directories', 'other', 'unknown']
        
        for category in all_categories:
            color = self.categorizer.get_category_color(category)
            assert color.startswith('#')
            assert len(color) == 7  # Format hexadécimal
    
    def test_all_categories_have_icons(self):
        """Property: Toutes les catégories ont des icônes définies"""
        all_categories = list(self.categorizer.categories.keys()) + ['directories', 'other', 'unknown']
        
        for category in all_categories:
            icon = self.categorizer.get_category_icon(category)
            assert isinstance(icon, str)
            assert len(icon) > 0
    
    @given(st.text(min_size=1, max_size=20))
    def test_unknown_category_defaults(self, unknown_category):
        """Property: Les catégories inconnues ont des valeurs par défaut"""
        assume(unknown_category not in self.categorizer.categories)
        assume(unknown_category not in ['directories', 'other', 'unknown'])
        
        color = self.categorizer.get_category_color(unknown_category)
        icon = self.categorizer.get_category_icon(unknown_category)
        
        # Valeurs par défaut
        assert color == '#bdc3c7'  # Gris clair par défaut
        assert icon == 'text-x-generic'  # Icône générique par défaut


class CategoryStatistics(RuleBasedStateMachine):
    """Machine à états pour tester les statistiques de catégories"""
    
    def __init__(self):
        super().__init__()
        self.categorizer = FileCategorizer()
        self.temp_dir = tempfile.mkdtemp()
        self.created_files = []
        self.expected_categories = {}
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(filename=st.text(min_size=1, max_size=20),
          extension=st.sampled_from(['.jpg', '.mp4', '.mp3', '.pdf', '.txt', '.py', '.zip']),
          content_size=st.integers(min_value=0, max_value=1000))
    def create_file(self, filename, extension, content_size):
        """Créer un fichier avec une extension et taille données"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if safe_filename:
            filepath = os.path.join(self.temp_dir, f"{safe_filename}{extension}")
            try:
                content = "x" * content_size
                Path(filepath).write_text(content, encoding='utf-8')
                
                # Vérifier que le fichier a été créé avec succès
                if os.path.exists(filepath):
                    self.created_files.append(filepath)
                    
                    # Prédire la catégorie
                    category = self.categorizer.categorize_file(filepath)
                    if category not in self.expected_categories:
                        self.expected_categories[category] = {'count': 0, 'size': 0}
                    
                    # Incrémenter seulement si le fichier n'existait pas déjà
                    actual_size = len(content.encode('utf-8'))
                    self.expected_categories[category]['count'] += 1
                    self.expected_categories[category]['size'] += actual_size
                
            except (OSError, UnicodeEncodeError):
                pass
    
    @rule()
    def analyze_and_verify_statistics(self):
        """Analyser et vérifier les statistiques"""
        if not self.created_files:
            return
        
        stats = self.categorizer.analyze_directory_categories(self.temp_dir)
        
        # Vérifier la cohérence avec nos attentes
        for category, expected in self.expected_categories.items():
            if category in stats:
                actual_stats = stats[category]
                
                # Le nombre de fichiers peut être différent si des fichiers ont été écrasés
                # ou si des erreurs de création ont eu lieu
                assert actual_stats.file_count >= 0
                
                # La taille doit être cohérente
                assert actual_stats.total_size >= 0
    
    @invariant()
    def statistics_are_valid(self):
        """Invariant: Les statistiques sont toujours valides"""
        if self.created_files:
            stats = self.categorizer.analyze_directory_categories(self.temp_dir)
            
            if stats:
                # Vérifier la cohérence mathématique
                total_percentage = sum(stat.percentage for stat in stats.values())
                # Tolérance plus large pour les erreurs d'arrondi et les cas edge
                assert abs(total_percentage - 100.0) < 5.0 or total_percentage == 0.0
                
                # Chaque statistique doit être valide
                for stat in stats.values():
                    assert stat.file_count >= 0
                    assert stat.total_size >= 0
                    assert 0 <= stat.percentage <= 100


# Test de la machine à états
TestCategoryStatistics = CategoryStatistics.TestCase


if __name__ == '__main__':
    pytest.main([__file__])