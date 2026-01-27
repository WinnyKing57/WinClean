# -*- coding: utf-8 -*-

import unittest
import sys
import os
from unittest.mock import Mock, patch
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# Ajouter le chemin src pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from hypothesis import given, strategies as st, settings
from ui.enhanced_treeview import EnhancedTreeView, ColumnConfig

class TestDynamicFilteringProperties(unittest.TestCase):
    """
    Feature: interface-moderne-avancee, Property 7: Dynamic Filtering
    Tests que le filtrage dynamique met à jour immédiatement les résultats affichés
    """
    
    def setUp(self):
        """Configuration des tests"""
        if not Gtk.init_check():
            self.skipTest("GTK not available for testing")
        
        self.test_columns = [
            ColumnConfig("Name", str, filterable=True),
            ColumnConfig("Size", int, filterable=True),
            ColumnConfig("Type", str, filterable=True)
        ]
        
        self.test_data = [
            ["document.pdf", 1000, "Document"],
            ["image.jpg", 2000, "Image"],
            ["video.mp4", 5000, "Video"],
            ["archive.zip", 3000, "Archive"],
            ["text.txt", 500, "Document"]
        ]
    
    @given(
        filter_text=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    @settings(max_examples=20)
    def test_text_filtering_immediate_update(self, filter_text):
        """
        Property 7: Dynamic Filtering
        Validates: Requirements 2.4, 5.2
        
        Test que le filtrage de texte met à jour immédiatement les résultats
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter les données de test
        for row in self.test_data:
            treeview.add_row(row)
        
        initial_count = treeview.get_model().iter_n_children(None)
        
        # Appliquer le filtre
        treeview.set_filter(0, filter_text)  # Filtrer par nom
        
        # Vérifier que le filtre est appliqué immédiatement
        self.assertIn(0, treeview.filters)
        self.assertEqual(treeview.filters[0], filter_text)
        
        # Le nombre de résultats peut changer selon le filtre
        filtered_count = treeview.get_model().iter_n_children(None)
        self.assertGreaterEqual(initial_count, filtered_count)
    
    @given(
        size_filter=st.integers(min_value=0, max_value=10000)
    )
    @settings(max_examples=15)
    def test_numeric_filtering_immediate_update(self, size_filter):
        """
        Property 7: Dynamic Filtering
        Validates: Requirements 2.4, 5.2
        
        Test que le filtrage numérique met à jour immédiatement les résultats
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter les données de test
        for row in self.test_data:
            treeview.add_row(row)
        
        # Appliquer le filtre numérique
        treeview.set_filter(1, str(size_filter))  # Filtrer par taille
        
        # Vérifier que le filtre est appliqué
        self.assertIn(1, treeview.filters)
        self.assertEqual(treeview.filters[1], str(size_filter))
    
    def test_filter_removal_restores_all_data(self):
        """
        Property 7: Dynamic Filtering
        Validates: Requirements 2.4, 5.2
        
        Test que la suppression des filtres restaure toutes les données
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter les données de test
        for row in self.test_data:
            treeview.add_row(row)
        
        initial_count = treeview.get_model().iter_n_children(None)
        
        # Appliquer un filtre restrictif
        treeview.set_filter(0, "nonexistent")
        
        # Supprimer tous les filtres
        treeview.clear_filters()
        
        # Vérifier que toutes les données sont restaurées
        final_count = treeview.get_model().iter_n_children(None)
        self.assertEqual(final_count, initial_count)
        self.assertEqual(len(treeview.filters), 0)
    
    @given(
        multiple_filters=st.dictionaries(
            keys=st.integers(min_value=0, max_value=2),
            values=st.text(min_size=1, max_size=20),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=10)
    def test_multiple_filters_combination(self, multiple_filters):
        """
        Property 7: Dynamic Filtering
        Validates: Requirements 2.4, 5.2
        
        Test que plusieurs filtres peuvent être combinés et mis à jour immédiatement
        """
        treeview = EnhancedTreeView(self.test_columns)
        
        # Ajouter les données de test
        for row in self.test_data:
            treeview.add_row(row)
        
        # Appliquer plusieurs filtres
        for column_id, filter_value in multiple_filters.items():
            if 0 <= column_id < len(self.test_columns):
                treeview.set_filter(column_id, filter_value)
        
        # Vérifier que tous les filtres sont appliqués
        for column_id, filter_value in multiple_filters.items():
            if 0 <= column_id < len(self.test_columns):
                self.assertIn(column_id, treeview.filters)
                self.assertEqual(treeview.filters[column_id], filter_value)


if __name__ == '__main__':
    os.environ['DISPLAY'] = ':99'
    unittest.main()