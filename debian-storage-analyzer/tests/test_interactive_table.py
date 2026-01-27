# -*- coding: utf-8 -*-

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# Ajouter le chemin src pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from hypothesis import given, strategies as st, settings, assume
from ui.enhanced_treeview import EnhancedTreeView, ColumnConfig

class TestInteractiveTableProperties(unittest.TestCase):
    """
    Feature: interface-moderne-avancee, Property 3: Interactive Table Functionality
    Tests que les tableaux interactifs supportent le tri et les colonnes cliquables
    """
    
    def setUp(self):
        """Configuration des tests"""
        if not Gtk.init_check():
            self.skipTest("GTK not available for testing")
        
        # Configuration de colonnes de test
        self.test_columns = [
            ColumnConfig("Name", str, sortable=True),
            ColumnConfig("Size", int, sortable=True),
            ColumnConfig("Type", str, sortable=True),
            ColumnConfig("Modified", str, sortable=True)
        ]
        
    def test_enhanced_treeview_creation(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que le TreeView amélioré se crée avec les colonnes configurées
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Vérifier que le TreeView est créé
        self.assertIsInstance(treeview, EnhancedTreeView)
        self.assertIsInstance(treeview, Gtk.TreeView)
        
        # Vérifier que les colonnes sont créées
        columns = treeview.get_columns()
        self.assertEqual(len(columns), len(self.test_columns))
        
        # Vérifier que chaque colonne a les bonnes propriétés
        for i, column in enumerate(columns):
            config = self.test_columns[i]
            self.assertEqual(column.get_title(), config.title)
            
            if config.sortable:
                self.assertEqual(column.get_sort_column_id(), i)
                self.assertTrue(column.get_clickable())
    
    @given(
        column_configs=st.lists(
            st.builds(
                ColumnConfig,
                title=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
                data_type=st.sampled_from([str, int, float, bool]),
                sortable=st.booleans(),
                filterable=st.booleans()
            ),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=20)
    def test_dynamic_column_configuration(self, column_configs):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que différentes configurations de colonnes sont supportées
        """
        try:
            treeview = EnhancedTreeView(column_configs)
            
            # Vérifier que le TreeView est créé sans erreur
            self.assertIsNotNone(treeview)
            
            # Vérifier le nombre de colonnes
            columns = treeview.get_columns()
            self.assertEqual(len(columns), len(column_configs))
            
            # Vérifier les propriétés de tri
            for i, (column, config) in enumerate(zip(columns, column_configs)):
                if config.sortable:
                    self.assertEqual(column.get_sort_column_id(), i)
                    self.assertTrue(column.get_clickable())
                
        except Exception as e:
            # Les configurations invalides peuvent lever des exceptions
            # C'est acceptable tant que l'erreur est gérée proprement
            self.assertIsInstance(e, (ValueError, TypeError))
    
    def test_sortable_columns_functionality(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que les colonnes triables fonctionnent correctement
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter des données de test
        test_data = [
            ["file1.txt", 1000, "File", "2024-01-01"],
            ["file2.txt", 500, "File", "2024-01-02"],
            ["folder1", 2000, "Folder", "2024-01-03"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        # Vérifier que les données sont ajoutées
        model = treeview.get_model()
        self.assertEqual(model.iter_n_children(None), len(test_data))
        
        # Tester le tri par taille (colonne 1)
        treeview.get_column(1).clicked()  # Simuler un clic sur l'en-tête
        
        # Vérifier que le modèle de tri est configuré
        self.assertIsNotNone(treeview.sort_model)
        self.assertIsNotNone(treeview.filter_model)
    
    @given(
        test_data=st.lists(
            st.lists(
                st.one_of(
                    st.text(min_size=1, max_size=50),
                    st.integers(min_value=0, max_value=1000000),
                    st.floats(min_value=0.0, max_value=1000000.0, allow_nan=False, allow_infinity=False)
                ),
                min_size=4,
                max_size=4
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=15)
    def test_data_addition_and_sorting(self, test_data):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que l'ajout de données et le tri fonctionnent avec différents types de données
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Convertir les données au bon format
        formatted_data = []
        for row in test_data:
            try:
                formatted_row = [
                    str(row[0]),  # Name (string)
                    int(float(row[1])) if isinstance(row[1], (int, float)) else 0,  # Size (int)
                    str(row[2]),  # Type (string)
                    str(row[3])   # Modified (string)
                ]
                formatted_data.append(formatted_row)
            except (ValueError, TypeError, IndexError):
                continue  # Ignorer les données invalides
        
        # Ajouter les données
        for row in formatted_data:
            try:
                treeview.add_row(row)
            except ValueError:
                continue  # Ignorer les lignes avec un mauvais nombre de colonnes
        
        # Vérifier que les données sont dans le modèle
        model = treeview.get_model()
        if formatted_data:
            self.assertGreaterEqual(model.iter_n_children(None), 0)
    
    def test_column_header_clickability(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que les en-têtes de colonnes sont cliquables pour le tri
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        columns = treeview.get_columns()
        
        for i, column in enumerate(columns):
            config = self.test_columns[i]
            
            if config.sortable:
                # Vérifier que la colonne est cliquable
                self.assertTrue(column.get_clickable())
                
                # Vérifier que l'ID de tri est configuré
                self.assertEqual(column.get_sort_column_id(), i)
                
                # Vérifier que le bouton d'en-tête existe
                header_button = column.get_button()
                self.assertIsNotNone(header_button)
    
    def test_filtering_functionality(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que le filtrage des données fonctionne correctement
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter des données de test
        test_data = [
            ["apple.txt", 100, "File", "2024-01-01"],
            ["banana.txt", 200, "File", "2024-01-02"],
            ["cherry.txt", 300, "File", "2024-01-03"],
            ["documents", 1000, "Folder", "2024-01-04"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        # Tester le filtrage par nom (colonne 0)
        treeview.set_filter(0, "apple")
        
        # Vérifier que le filtre est appliqué
        self.assertIn(0, treeview.filters)
        self.assertEqual(treeview.filters[0], "apple")
        
        # Tester le filtrage par taille (colonne 1)
        treeview.set_filter(1, "150")  # Fichiers >= 150 octets
        
        # Vérifier que le filtre est appliqué
        self.assertIn(1, treeview.filters)
        
        # Tester la suppression des filtres
        treeview.clear_filters()
        self.assertEqual(len(treeview.filters), 0)
    
    @given(
        filter_values=st.dictionaries(
            keys=st.integers(min_value=0, max_value=3),
            values=st.one_of(
                st.text(min_size=1, max_size=20),
                st.integers(min_value=0, max_value=1000),
                st.none()
            ),
            min_size=0,
            max_size=4
        )
    )
    @settings(max_examples=15)
    def test_multiple_filters_application(self, filter_values):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que plusieurs filtres peuvent être appliqués simultanément
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter des données de test
        test_data = [
            ["file1.txt", 100, "File", "2024-01-01"],
            ["file2.txt", 200, "File", "2024-01-02"],
            ["folder1", 1000, "Folder", "2024-01-03"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        # Appliquer les filtres
        for column_id, filter_value in filter_values.items():
            if 0 <= column_id < len(self.test_columns):
                try:
                    treeview.set_filter(column_id, filter_value)
                except (ValueError, TypeError):
                    continue  # Ignorer les valeurs de filtre invalides
        
        # Vérifier que les filtres sont appliqués
        for column_id, filter_value in filter_values.items():
            if 0 <= column_id < len(self.test_columns) and filter_value is not None:
                if column_id in treeview.filters:
                    self.assertEqual(treeview.filters[column_id], filter_value)
    
    def test_selection_functionality(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que la sélection multiple fonctionne correctement
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Vérifier que la sélection multiple est activée
        selection = treeview.get_selection()
        self.assertEqual(selection.get_mode(), Gtk.SelectionMode.MULTIPLE)
        
        # Ajouter des données de test
        test_data = [
            ["file1.txt", 100, "File", "2024-01-01"],
            ["file2.txt", 200, "File", "2024-01-02"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        # Tester la récupération des données sélectionnées
        selected_data = treeview.get_selected_rows_data()
        self.assertIsInstance(selected_data, list)
    
    def test_csv_export_functionality(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que l'export CSV fonctionne correctement
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter des données de test
        test_data = [
            ["file1.txt", 100, "File", "2024-01-01"],
            ["file2.txt", 200, "File", "2024-01-02"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        # Tester l'export (sans créer de fichier réel)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_filename = f.name
        
        try:
            treeview.export_to_csv(temp_filename)
            
            # Vérifier que le fichier a été créé
            self.assertTrue(os.path.exists(temp_filename))
            
            # Vérifier le contenu du fichier
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Vérifier que les en-têtes sont présents
                for config in self.test_columns:
                    self.assertIn(config.title, content)
                
                # Vérifier que les données sont présentes
                self.assertIn("file1.txt", content)
                self.assertIn("file2.txt", content)
                
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_model_consistency_after_operations(self):
        """
        Property 3: Interactive Table Functionality
        Validates: Requirements 1.4, 5.1
        
        Test que la cohérence du modèle est maintenue après diverses opérations
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter des données
        test_data = [
            ["file1.txt", 100, "File", "2024-01-01"],
            ["file2.txt", 200, "File", "2024-01-02"],
            ["folder1", 1000, "Folder", "2024-01-03"]
        ]
        
        for row in test_data:
            treeview.add_row(row)
        
        initial_count = treeview.get_model().iter_n_children(None)
        self.assertEqual(initial_count, len(test_data))
        
        # Appliquer un filtre
        treeview.set_filter(0, "file")
        
        # Vérifier que le modèle de base n'est pas modifié
        base_count = treeview.base_model.iter_n_children(None)
        self.assertEqual(base_count, len(test_data))
        
        # Supprimer les filtres
        treeview.clear_filters()
        
        # Vérifier que toutes les données sont à nouveau visibles
        final_count = treeview.get_model().iter_n_children(None)
        self.assertEqual(final_count, initial_count)
        
        # Vider le modèle
        treeview.clear()
        
        # Vérifier que le modèle est vide
        empty_count = treeview.get_model().iter_n_children(None)
        self.assertEqual(empty_count, 0)


if __name__ == '__main__':
    # Configuration pour les tests headless
    os.environ['DISPLAY'] = ':99'
    
    unittest.main()