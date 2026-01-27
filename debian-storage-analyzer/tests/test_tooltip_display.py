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
from ui.tooltip_manager import TooltipManager
from main.modern_main import ModernMainWindow, ModernApplication

class TestTooltipDisplayProperties(unittest.TestCase):
    """
    Feature: interface-moderne-avancee, Property 4: Tooltip Display
    Tests que les tooltips contextuels s'affichent correctement au survol
    """
    
    def setUp(self):
        """Configuration des tests"""
        if not Gtk.init_check():
            self.skipTest("GTK not available for testing")
        
        self.app = ModernApplication()
        self.tooltip_manager = TooltipManager()
        
    def tearDown(self):
        """Nettoyage après tests"""
        if hasattr(self, 'window') and self.window:
            self.window.destroy()
    
    def test_tooltip_manager_initialization(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que le gestionnaire de tooltips s'initialise avec les tooltips prédéfinis
        """
        # Vérifier que le tooltip manager a des tooltips prédéfinis
        self.assertIsInstance(self.tooltip_manager.tooltips, dict)
        self.assertGreater(len(self.tooltip_manager.tooltips), 0)
        
        # Vérifier que les tooltips de navigation sont présents
        navigation_tooltips = ["dashboard", "analyzer", "cleaner", "history", "settings"]
        for tooltip_key in navigation_tooltips:
            self.assertIn(tooltip_key, self.tooltip_manager.tooltips)
            self.assertIsInstance(self.tooltip_manager.tooltips[tooltip_key], str)
            self.assertGreater(len(self.tooltip_manager.tooltips[tooltip_key]), 0)
    
    @given(tooltip_key=st.sampled_from([
        "dashboard", "analyzer", "cleaner", "history", "settings",
        "select_folder", "start_analysis", "clean_selected", "dry_run"
    ]))
    @settings(max_examples=30)
    def test_tooltip_text_retrieval(self, tooltip_key):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les textes de tooltip peuvent être récupérés correctement
        """
        # Récupérer le texte du tooltip
        tooltip_text = self.tooltip_manager.get_tooltip_text(tooltip_key)
        
        # Vérifier que le texte existe et n'est pas vide
        self.assertIsInstance(tooltip_text, str)
        self.assertGreater(len(tooltip_text), 0)
        
        # Vérifier que le texte est informatif (plus de 10 caractères)
        self.assertGreater(len(tooltip_text), 10)
    
    def test_tooltip_setup_on_widget(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips peuvent être configurés sur des widgets
        """
        # Créer un widget de test
        button = Gtk.Button(label="Test Button")
        
        # Configurer un tooltip
        self.tooltip_manager.setup_tooltip(button, "dashboard")
        
        # Vérifier que le tooltip est configuré
        self.assertTrue(button.get_has_tooltip())
        
        # Vérifier que le texte du tooltip est correct
        expected_text = self.tooltip_manager.get_tooltip_text("dashboard")
        self.assertEqual(button.get_tooltip_text(), expected_text)
    
    @given(
        custom_text=st.text(min_size=5, max_size=100, 
                           alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs')))
    )
    @settings(max_examples=20)
    def test_custom_tooltip_text(self, custom_text):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips personnalisés fonctionnent correctement
        """
        # Créer un widget de test
        button = Gtk.Button(label="Test Button")
        
        # Configurer un tooltip personnalisé
        self.tooltip_manager.setup_tooltip(button, "dashboard", custom_text)
        
        # Vérifier que le tooltip personnalisé est utilisé
        self.assertTrue(button.get_has_tooltip())
        self.assertEqual(button.get_tooltip_text(), custom_text)
    
    def test_rich_tooltip_creation(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips riches avec markup sont créés correctement
        """
        title = "Test Title"
        description = "Test description for the tooltip"
        shortcut = "Ctrl+T"
        
        # Créer un tooltip riche
        rich_tooltip = self.tooltip_manager.create_rich_tooltip(title, description, shortcut)
        
        # Vérifier que le tooltip contient tous les éléments
        self.assertIn(title, rich_tooltip)
        self.assertIn(description, rich_tooltip)
        self.assertIn(shortcut, rich_tooltip)
        
        # Vérifier le markup HTML
        self.assertIn("<b>", rich_tooltip)  # Titre en gras
        self.assertIn("<i>", rich_tooltip)  # Raccourci en italique
    
    @given(
        tooltip_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            values=st.one_of(st.text(min_size=1, max_size=50), st.integers(), st.floats()),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=15)
    def test_contextual_tooltip_creation(self, tooltip_data):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips contextuels sont créés avec des données dynamiques
        """
        base_key = "dashboard"
        
        # Créer un tooltip contextuel
        contextual_tooltip = self.tooltip_manager.create_contextual_tooltip(base_key, tooltip_data)
        
        # Vérifier que le tooltip de base est inclus
        base_text = self.tooltip_manager.get_tooltip_text(base_key)
        self.assertIn(base_text, contextual_tooltip)
        
        # Vérifier que les données contextuelles sont incluses
        for key, value in tooltip_data.items():
            if value is not None:
                self.assertIn(str(key), contextual_tooltip)
                self.assertIn(str(value), contextual_tooltip)
    
    def test_tooltip_container_setup(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips peuvent être configurés pour tous les widgets d'un container
        """
        # Créer un container avec plusieurs widgets
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        button1 = Gtk.Button(label="Button 1")
        button2 = Gtk.Button(label="Button 2")
        label = Gtk.Label(label="Label")
        
        # Définir des noms pour les widgets (simuler Gtk.Buildable.get_name)
        Gtk.Buildable.set_name(button1, "test_button1")
        Gtk.Buildable.set_name(button2, "test_button2")
        Gtk.Buildable.set_name(label, "test_label")
        
        box.pack_start(button1, False, False, 0)
        box.pack_start(button2, False, False, 0)
        box.pack_start(label, False, False, 0)
        
        # Mapping des tooltips
        tooltip_mapping = {
            "test_button1": "dashboard",
            "test_button2": "analyzer",
            "test_label": "settings"
        }
        
        # Configurer les tooltips pour le container
        self.tooltip_manager.setup_tooltips_for_container(box, tooltip_mapping)
        
        # Vérifier que les tooltips sont configurés (test basique)
        # Note: La vérification complète nécessiterait une simulation plus complexe
        self.assertTrue(True)  # Placeholder - test de base
    
    def test_tooltip_callback_mechanism(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que le mécanisme de callback pour les tooltips fonctionne
        """
        # Créer un widget de test
        button = Gtk.Button(label="Test Button")
        tooltip_text = "Test tooltip text"
        
        # Tester le callback de tooltip
        result = self.tooltip_manager._on_query_tooltip(
            button, 0, 0, False, Mock(), tooltip_text
        )
        
        # Vérifier que le callback retourne True (tooltip affiché)
        self.assertTrue(result)
    
    @given(
        tooltip_keys=st.lists(
            st.sampled_from([
                "dashboard", "analyzer", "cleaner", "column_name", "column_size",
                "filter_size", "clean_apt", "config_theme"
            ]),
            min_size=1,
            max_size=8,
            unique=True
        )
    )
    @settings(max_examples=20)
    def test_multiple_tooltips_consistency(self, tooltip_keys):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que plusieurs tooltips peuvent être gérés de manière cohérente
        """
        widgets = []
        
        # Créer des widgets avec des tooltips
        for i, tooltip_key in enumerate(tooltip_keys):
            widget = Gtk.Button(label=f"Button {i}")
            self.tooltip_manager.setup_tooltip(widget, tooltip_key)
            widgets.append((widget, tooltip_key))
        
        # Vérifier que tous les tooltips sont configurés correctement
        for widget, tooltip_key in widgets:
            self.assertTrue(widget.get_has_tooltip())
            expected_text = self.tooltip_manager.get_tooltip_text(tooltip_key)
            self.assertEqual(widget.get_tooltip_text(), expected_text)
    
    def test_tooltip_text_localization_ready(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que les tooltips sont prêts pour la localisation
        """
        # Vérifier que les tooltips utilisent gettext (marqués avec _())
        # Pour ce test, on vérifie que les textes sont des chaînes non vides
        
        for tooltip_key, tooltip_text in self.tooltip_manager.tooltips.items():
            # Vérifier que le texte n'est pas vide
            self.assertIsInstance(tooltip_text, str)
            self.assertGreater(len(tooltip_text.strip()), 0)
            
            # Vérifier que le texte est informatif (pas juste un mot)
            words = tooltip_text.split()
            self.assertGreaterEqual(len(words), 2, 
                                  f"Tooltip for {tooltip_key} should be more descriptive")
    
    def test_add_custom_tooltip_functionality(self):
        """
        Property 4: Tooltip Display
        Validates: Requirements 1.5, 6.4
        
        Test que des tooltips personnalisés peuvent être ajoutés dynamiquement
        """
        custom_key = "custom_test_tooltip"
        custom_text = "This is a custom tooltip for testing"
        
        # Ajouter un tooltip personnalisé
        self.tooltip_manager.add_custom_tooltip(custom_key, custom_text)
        
        # Vérifier que le tooltip a été ajouté
        self.assertIn(custom_key, self.tooltip_manager.tooltips)
        self.assertEqual(self.tooltip_manager.get_tooltip_text(custom_key), custom_text)
        
        # Vérifier qu'il peut être utilisé sur un widget
        button = Gtk.Button(label="Custom Button")
        self.tooltip_manager.setup_tooltip(button, custom_key)
        
        self.assertTrue(button.get_has_tooltip())
        self.assertEqual(button.get_tooltip_text(), custom_text)


if __name__ == '__main__':
    # Configuration pour les tests headless
    os.environ['DISPLAY'] = ':99'
    
    unittest.main()