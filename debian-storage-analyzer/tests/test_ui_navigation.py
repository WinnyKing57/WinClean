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

from hypothesis import given, strategies as st, settings, assume
from ui.modern_sidebar import ModernSidebar
from ui.theme_manager import ThemeManager
from main.modern_main import ModernMainWindow, ModernApplication

class TestUINavigationProperties(unittest.TestCase):
    """
    Feature: interface-moderne-avancee, Property 1: UI Navigation and Layout
    Tests que l'interface affiche toutes les sections requises et maintient la cohérence visuelle
    """
    
    def setUp(self):
        """Configuration des tests"""
        # Initialiser GTK pour les tests (mode headless)
        if not Gtk.init_check():
            self.skipTest("GTK not available for testing")
        
        # Créer une application de test
        self.app = ModernApplication()
        
    def tearDown(self):
        """Nettoyage après tests"""
        if hasattr(self, 'window') and self.window:
            self.window.destroy()
    
    def test_ui_displays_required_navigation_sections(self):
        """
        Property 1: UI Navigation and Layout
        Validates: Requirements 1.1, 1.2
        
        Test que l'interface affiche toutes les sections de navigation requises
        """
        # Créer la fenêtre principale
        self.window = ModernMainWindow(application=self.app)
        
        # Vérifier que la sidebar existe
        self.assertIsNotNone(self.window.sidebar)
        
        # Vérifier que toutes les sections requises sont présentes
        required_sections = ["dashboard", "analyzer", "cleaner", "history", "settings"]
        
        for section_id in required_sections:
            # Vérifier que la section existe dans la sidebar
            self.assertIn(section_id, [s[0] for s in self.window.sidebar.sections])
            
            # Vérifier que la page correspondante existe dans le stack
            page = self.window.stack.get_child_by_name(section_id)
            self.assertIsNotNone(page, f"Page {section_id} should exist in stack")
    
    @given(section_id=st.sampled_from(["dashboard", "analyzer", "cleaner", "history", "settings"]))
    @settings(max_examples=50)
    def test_section_transitions_maintain_consistency(self, section_id):
        """
        Property 1: UI Navigation and Layout  
        Validates: Requirements 1.1, 1.2
        
        Test que les transitions entre sections maintiennent la cohérence visuelle
        """
        # Créer la fenêtre principale
        self.window = ModernMainWindow(application=self.app)
        
        # Obtenir l'état initial
        initial_stack_child = self.window.stack.get_visible_child_name()
        
        # Effectuer la transition vers la section
        self.window.sidebar.set_active_section(section_id)
        self.window.stack.set_visible_child_name(section_id)
        
        # Vérifier que la transition a eu lieu
        current_child = self.window.stack.get_visible_child_name()
        self.assertEqual(current_child, section_id)
        
        # Vérifier que le bouton correspondant est marqué comme actif
        if section_id in self.window.sidebar.nav_buttons:
            button = self.window.sidebar.nav_buttons[section_id]
            style_context = button.get_style_context()
            self.assertTrue(style_context.has_class("sidebar-button-active"))
        
        # Vérifier que les autres boutons ne sont pas actifs
        for other_section, other_button in self.window.sidebar.nav_buttons.items():
            if other_section != section_id:
                other_style_context = other_button.get_style_context()
                self.assertFalse(other_style_context.has_class("sidebar-button-active"))
    
    def test_sidebar_structure_consistency(self):
        """
        Property 1: UI Navigation and Layout
        Validates: Requirements 1.1, 1.2
        
        Test que la structure de la sidebar est cohérente
        """
        sidebar = ModernSidebar()
        stack = Gtk.Stack()
        
        # Créer la sidebar
        sidebar_widget = sidebar.create_sidebar(stack)
        
        # Vérifier que le widget sidebar est créé
        self.assertIsNotNone(sidebar_widget)
        self.assertIsInstance(sidebar_widget, Gtk.Widget)
        
        # Vérifier que toutes les sections sont définies
        self.assertEqual(len(sidebar.sections), 5)
        
        # Vérifier que chaque section a les bonnes propriétés
        for section_id, section_name, icon_name in sidebar.sections:
            self.assertIsInstance(section_id, str)
            self.assertIsInstance(section_name, str)
            self.assertIsInstance(icon_name, str)
            self.assertTrue(len(section_id) > 0)
            self.assertTrue(len(section_name) > 0)
            self.assertTrue(len(icon_name) > 0)
    
    @given(
        sections=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu'))),
                st.text(min_size=1, max_size=50),
                st.text(min_size=1, max_size=30)
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=20)
    def test_sidebar_handles_various_section_configurations(self, sections):
        """
        Property 1: UI Navigation and Layout
        Validates: Requirements 1.1, 1.2
        
        Test que la sidebar gère différentes configurations de sections
        """
        # Créer une sidebar avec des sections personnalisées
        sidebar = ModernSidebar()
        original_sections = sidebar.sections
        
        try:
            # Remplacer temporairement les sections
            sidebar.sections = sections
            stack = Gtk.Stack()
            
            # Créer la sidebar
            sidebar_widget = sidebar.create_sidebar(stack)
            
            # Vérifier que le widget est créé sans erreur
            self.assertIsNotNone(sidebar_widget)
            
            # Vérifier que le nombre de boutons correspond au nombre de sections
            self.assertEqual(len(sidebar.nav_buttons), len(sections))
            
            # Vérifier que chaque section a un bouton correspondant
            for section_id, _, _ in sections:
                self.assertIn(section_id, sidebar.nav_buttons)
                
        finally:
            # Restaurer les sections originales
            sidebar.sections = original_sections
    
    def test_navigation_button_creation(self):
        """
        Property 1: UI Navigation and Layout
        Validates: Requirements 1.1, 1.2
        
        Test que les boutons de navigation sont créés correctement
        """
        sidebar = ModernSidebar()
        stack = Gtk.Stack()
        
        # Créer la sidebar
        sidebar_widget = sidebar.create_sidebar(stack)
        
        # Vérifier que tous les boutons de navigation sont créés
        expected_sections = ["dashboard", "analyzer", "cleaner", "history", "settings"]
        
        for section_id in expected_sections:
            self.assertIn(section_id, sidebar.nav_buttons)
            button = sidebar.nav_buttons[section_id]
            
            # Vérifier que c'est bien un bouton
            self.assertIsInstance(button, Gtk.Button)
            
            # Vérifier que le bouton a les bonnes classes CSS
            style_context = button.get_style_context()
            self.assertTrue(style_context.has_class("sidebar-button"))
    
    def test_visual_consistency_during_navigation(self):
        """
        Property 1: UI Navigation and Layout
        Validates: Requirements 1.1, 1.2
        
        Test que la cohérence visuelle est maintenue pendant la navigation
        """
        self.window = ModernMainWindow(application=self.app)
        
        # Tester la navigation vers chaque section
        sections = ["dashboard", "analyzer", "cleaner", "history", "settings"]
        
        for section_id in sections:
            # Naviguer vers la section
            self.window.sidebar.set_active_section(section_id)
            
            # Vérifier qu'exactement un bouton est actif
            active_buttons = []
            for btn_id, button in self.window.sidebar.nav_buttons.items():
                if button.get_style_context().has_class("sidebar-button-active"):
                    active_buttons.append(btn_id)
            
            self.assertEqual(len(active_buttons), 1, 
                           f"Exactly one button should be active, got: {active_buttons}")
            self.assertEqual(active_buttons[0], section_id,
                           f"Active button should be {section_id}, got: {active_buttons[0]}")


if __name__ == '__main__':
    # Configuration pour les tests headless
    os.environ['DISPLAY'] = ':99'  # Display virtuel pour les tests CI
    
    unittest.main()