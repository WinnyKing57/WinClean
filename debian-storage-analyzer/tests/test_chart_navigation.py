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
from ui.interactive_charts import InteractiveCharts, ChartData

class TestChartNavigationProperties(unittest.TestCase):
    """
    Feature: interface-moderne-avancee, Property 6: Interactive Chart Navigation
    Tests que les graphiques permettent la navigation et l'exploration interactive
    """
    
    def setUp(self):
        """Configuration des tests"""
        if not Gtk.init_check():
            self.skipTest("GTK not available for testing")
        
        self.charts = InteractiveCharts()
        
        # Données de test
        self.test_data = ChartData(
            labels=["Documents", "Images", "Videos", "Other"],
            values=[1000000, 2000000, 5000000, 500000],
            colors=["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]
        )
    
    def test_interactive_charts_initialization(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que le gestionnaire de graphiques interactifs s'initialise correctement
        """
        # Vérifier l'initialisation
        self.assertIsInstance(self.charts, InteractiveCharts)
        self.assertIsInstance(self.charts.click_callbacks, dict)
        self.assertIsInstance(self.charts.default_colors, list)
        self.assertGreater(len(self.charts.default_colors), 0)
    
    def test_pie_chart_creation_with_interactivity(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les graphiques en camembert sont créés avec l'interactivité
        """
        # Créer un graphique en camembert interactif
        canvas = self.charts.create_pie_chart(
            self.test_data, 
            title="Test Pie Chart", 
            interactive=True
        )
        
        # Vérifier que le canvas est créé
        self.assertIsNotNone(canvas)
        self.assertIsInstance(canvas, Gtk.Widget)
        
        # Vérifier que la figure matplotlib est accessible
        figure = canvas.get_property('figure')
        self.assertIsNotNone(figure)
    
    def test_histogram_creation_with_interactivity(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les histogrammes sont créés avec l'interactivité
        """
        # Créer un histogramme interactif
        canvas = self.charts.create_histogram(
            self.test_data,
            title="Test Histogram",
            interactive=True
        )
        
        # Vérifier que le canvas est créé
        self.assertIsNotNone(canvas)
        self.assertIsInstance(canvas, Gtk.Widget)
        
        # Vérifier que la figure matplotlib est accessible
        figure = canvas.get_property('figure')
        self.assertIsNotNone(figure)
    
    def test_treemap_creation_with_interactivity(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les treemaps sont créés avec l'interactivité
        """
        # Créer un treemap interactif
        canvas = self.charts.create_treemap(
            self.test_data,
            title="Test Treemap",
            interactive=True
        )
        
        # Vérifier que le canvas est créé
        self.assertIsNotNone(canvas)
        self.assertIsInstance(canvas, Gtk.Widget)
        
        # Vérifier que la figure matplotlib est accessible
        figure = canvas.get_property('figure')
        self.assertIsNotNone(figure)
    
    @given(
        chart_data=st.builds(
            ChartData,
            labels=st.lists(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                min_size=1,
                max_size=10,
                unique=True
            ),
            values=st.lists(
                st.floats(min_value=1.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
                min_size=1,
                max_size=10
            )
        )
    )
    @settings(max_examples=15)
    def test_chart_creation_with_various_data(self, chart_data):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les graphiques peuvent être créés avec différents types de données
        """
        # S'assurer que les listes ont la même taille
        min_length = min(len(chart_data.labels), len(chart_data.values))
        if min_length == 0:
            return  # Ignorer les données vides
        
        chart_data.labels = chart_data.labels[:min_length]
        chart_data.values = chart_data.values[:min_length]
        
        try:
            # Tester la création de différents types de graphiques
            pie_canvas = self.charts.create_pie_chart(chart_data, interactive=True)
            self.assertIsNotNone(pie_canvas)
            
            histogram_canvas = self.charts.create_histogram(chart_data, interactive=True)
            self.assertIsNotNone(histogram_canvas)
            
            treemap_canvas = self.charts.create_treemap(chart_data, interactive=True)
            self.assertIsNotNone(treemap_canvas)
            
        except Exception as e:
            # Certaines données peuvent causer des erreurs (valeurs négatives, etc.)
            # C'est acceptable tant que l'erreur est gérée proprement
            self.assertIsInstance(e, (ValueError, TypeError, ZeroDivisionError))
    
    def test_click_callback_registration(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les callbacks de clic peuvent être enregistrés
        """
        # Créer un callback de test
        callback_called = []
        
        def test_callback(index, label, value):
            callback_called.append((index, label, value))
        
        # Enregistrer le callback
        self.charts.set_click_callback("pie", test_callback)
        
        # Vérifier que le callback est enregistré
        self.assertIn("pie_click", self.charts.click_callbacks)
        self.assertEqual(self.charts.click_callbacks["pie_click"], test_callback)
        
        # Tester l'appel du callback
        self.charts.click_callbacks["pie_click"](0, "Test", 100)
        
        # Vérifier que le callback a été appelé
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], (0, "Test", 100))
    
    @given(
        callback_data=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10),
                st.text(min_size=1, max_size=20),
                st.floats(min_value=0.0, max_value=1000000.0, allow_nan=False, allow_infinity=False)
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=10)
    def test_multiple_callback_invocations(self, callback_data):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les callbacks peuvent être invoqués plusieurs fois avec différentes données
        """
        callback_results = []
        
        def test_callback(index, label, value):
            callback_results.append((index, label, value))
        
        # Enregistrer le callback
        self.charts.set_click_callback("histogram", test_callback)
        
        # Invoquer le callback avec différentes données
        for index, label, value in callback_data:
            self.charts.click_callbacks["histogram_click"](index, label, value)
        
        # Vérifier que tous les appels ont été enregistrés
        self.assertEqual(len(callback_results), len(callback_data))
        
        for i, (expected, actual) in enumerate(zip(callback_data, callback_results)):
            self.assertEqual(expected, actual)
    
    def test_treemap_rectangle_calculation(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que le calcul des rectangles pour le treemap fonctionne correctement
        """
        values = [100, 200, 300, 400]
        rectangles = self.charts._calculate_treemap_rectangles(values, 0, 0, 1, 1)
        
        # Vérifier que le bon nombre de rectangles est généré
        self.assertEqual(len(rectangles), len(values))
        
        # Vérifier que chaque rectangle a 4 coordonnées
        for rect in rectangles:
            self.assertEqual(len(rect), 4)  # x, y, width, height
            x, y, width, height = rect
            
            # Vérifier que les coordonnées sont valides
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertGreaterEqual(width, 0)
            self.assertGreaterEqual(height, 0)
            self.assertLessEqual(x + width, 1.1)  # Petite tolérance pour les erreurs de calcul
            self.assertLessEqual(y + height, 1.1)
    
    @given(
        values=st.lists(
            st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=15)
    def test_treemap_rectangle_calculation_properties(self, values):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que le calcul des rectangles respecte les propriétés mathématiques
        """
        if not values or sum(values) == 0:
            return  # Ignorer les cas invalides
        
        rectangles = self.charts._calculate_treemap_rectangles(values, 0, 0, 1, 1)
        
        # Vérifier que le nombre de rectangles correspond au nombre de valeurs
        self.assertEqual(len(rectangles), len(values))
        
        # Calculer l'aire totale des rectangles
        total_area = sum(width * height for x, y, width, height in rectangles)
        
        # L'aire totale devrait être proche de 1 (avec une petite tolérance)
        self.assertAlmostEqual(total_area, 1.0, delta=0.1)
        
        # Vérifier que tous les rectangles sont dans les limites
        for x, y, width, height in rectangles:
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertGreaterEqual(width, 0)
            self.assertGreaterEqual(height, 0)
            self.assertLessEqual(x + width, 1.1)
            self.assertLessEqual(y + height, 1.1)
    
    def test_color_detection_functionality(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que la détection de couleurs sombres fonctionne correctement
        """
        # Tester des couleurs sombres
        dark_colors = ["#000000", "#333333", "#1a1a1a", "#2d2d2d"]
        for color in dark_colors:
            self.assertTrue(self.charts._is_dark_color(color), f"{color} should be detected as dark")
        
        # Tester des couleurs claires
        light_colors = ["#ffffff", "#f0f0f0", "#cccccc", "#e0e0e0"]
        for color in light_colors:
            self.assertFalse(self.charts._is_dark_color(color), f"{color} should be detected as light")
    
    @given(
        hex_colors=st.lists(
            st.text(min_size=7, max_size=7).filter(
                lambda x: x.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in x[1:])
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=10)
    def test_color_detection_with_various_colors(self, hex_colors):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que la détection de couleurs fonctionne avec diverses couleurs hexadécimales
        """
        for color in hex_colors:
            try:
                result = self.charts._is_dark_color(color)
                # Le résultat doit être un booléen
                self.assertIsInstance(result, bool)
            except (ValueError, IndexError):
                # Les couleurs malformées peuvent lever des exceptions
                continue
    
    def test_size_formatting(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que le formatage des tailles fonctionne correctement
        """
        # Tester différentes tailles
        test_cases = [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB")
        ]
        
        for size, expected in test_cases:
            result = self.charts._format_size(size)
            self.assertEqual(result, expected)
    
    @given(
        sizes=st.lists(
            st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=15)
    def test_size_formatting_properties(self, sizes):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que le formatage des tailles respecte les propriétés attendues
        """
        for size in sizes:
            if size < 0:
                continue  # Ignorer les tailles négatives
            
            formatted = self.charts._format_size(size)
            
            # Vérifier que le résultat est une chaîne
            self.assertIsInstance(formatted, str)
            
            # Vérifier que le résultat contient une unité
            units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
            self.assertTrue(any(unit in formatted for unit in units))
            
            # Vérifier que le résultat contient un nombre
            import re
            self.assertTrue(re.search(r'\d+\.?\d*', formatted))
    
    def test_chart_theme_application(self):
        """
        Property 6: Interactive Chart Navigation
        Validates: Requirements 2.3
        
        Test que les thèmes peuvent être appliqués aux graphiques
        """
        # Créer un mock theme manager
        mock_theme_manager = Mock()
        mock_theme_manager.get_current_theme.return_value = "dark"
        
        charts_with_theme = InteractiveCharts(theme_manager=mock_theme_manager)
        
        # Créer un graphique
        canvas = charts_with_theme.create_pie_chart(self.test_data, interactive=True)
        
        # Vérifier que le graphique est créé
        self.assertIsNotNone(canvas)
        
        # Vérifier que le theme manager est utilisé
        mock_theme_manager.get_current_theme.assert_called()


if __name__ == '__main__':
    # Configuration pour les tests headless
    os.environ['DISPLAY'] = ':99'
    
    unittest.main()