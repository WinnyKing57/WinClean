# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib
import os

class ThemeManager:
    """Gestionnaire de thèmes pour l'adaptation automatique sombre/clair"""
    
    def __init__(self, window: Gtk.Window):
        self.window = window
        self.css_provider = Gtk.CssProvider()
        self.current_theme = None
        
        # Charger les styles CSS personnalisés
        self._load_custom_css()
        
        # Surveiller les changements de thème système
        self._setup_theme_monitoring()
        
        # Appliquer le thème initial
        self._apply_current_theme()
    
    def _load_custom_css(self):
        """Charge les styles CSS personnalisés"""
        css_content = """
        /* Styles pour la sidebar moderne */
        .sidebar {
            background-color: @theme_bg_color;
            border-right: 1px solid @borders;
        }
        
        .sidebar-title {
            font-weight: bold;
            font-size: 14px;
            color: @theme_fg_color;
        }
        
        .sidebar-subtitle {
            font-size: 11px;
            color: @theme_unfocused_fg_color;
        }
        
        .sidebar-button {
            border-radius: 6px;
            margin: 1px 0;
            background: transparent;
            border: none;
            transition: all 200ms ease;
        }
        
        .sidebar-button:hover {
            background-color: alpha(@theme_selected_bg_color, 0.1);
        }
        
        .sidebar-button-active {
            background-color: @theme_selected_bg_color;
            color: @theme_selected_fg_color;
        }
        
        .sidebar-button-active:hover {
            background-color: @theme_selected_bg_color;
        }
        
        .sidebar-footer {
            font-size: 10px;
            color: @theme_unfocused_fg_color;
        }
        
        /* Styles pour les tooltips */
        .tooltip-custom {
            background-color: @theme_tooltip_bg_color;
            color: @theme_tooltip_fg_color;
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 11px;
        }
        
        /* Styles pour les tableaux interactifs */
        .enhanced-treeview {
            border: 1px solid @borders;
            border-radius: 4px;
        }
        
        .enhanced-treeview header button {
            border-right: 1px solid @borders;
            background: @theme_base_color;
        }
        
        .enhanced-treeview header button:hover {
            background: alpha(@theme_selected_bg_color, 0.1);
        }
        
        /* Styles pour les barres de progression */
        .progress-modern {
            border-radius: 10px;
            background-color: alpha(@theme_selected_bg_color, 0.2);
        }
        
        .progress-modern progress {
            border-radius: 10px;
            background-color: @theme_selected_bg_color;
        }
        
        /* Styles pour les notifications */
        .notification-success {
            background-color: #4CAF50;
            color: white;
            border-radius: 4px;
            padding: 8px 12px;
        }
        
        .notification-error {
            background-color: #F44336;
            color: white;
            border-radius: 4px;
            padding: 8px 12px;
        }
        
        .notification-warning {
            background-color: #FF9800;
            color: white;
            border-radius: 4px;
            padding: 8px 12px;
        }
        
        /* Adaptation pour le thème sombre */
        @define-color dark_sidebar_bg #2d2d2d;
        @define-color dark_sidebar_fg #ffffff;
        @define-color dark_sidebar_border #404040;
        
        .dark .sidebar {
            background-color: @dark_sidebar_bg;
            border-right-color: @dark_sidebar_border;
        }
        
        .dark .sidebar-title {
            color: @dark_sidebar_fg;
        }
        
        .dark .sidebar-subtitle {
            color: alpha(@dark_sidebar_fg, 0.7);
        }
        
        .dark .sidebar-footer {
            color: alpha(@dark_sidebar_fg, 0.6);
        }
        """
        
        try:
            self.css_provider.load_from_data(css_content.encode('utf-8'))
            
            # Appliquer le CSS à l'écran
            screen = self.window.get_screen()
            style_context = Gtk.StyleContext()
            style_context.add_provider_for_screen(
                screen, 
                self.css_provider, 
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Erreur lors du chargement du CSS: {e}")
    
    def _setup_theme_monitoring(self):
        """Configure la surveillance des changements de thème"""
        settings = Gtk.Settings.get_default()
        if settings:
            settings.connect("notify::gtk-theme-name", self._on_theme_changed)
            settings.connect("notify::gtk-application-prefer-dark-theme", self._on_theme_changed)
    
    def _on_theme_changed(self, settings, param):
        """Callback appelé lors du changement de thème"""
        GLib.idle_add(self._apply_current_theme)
    
    def _apply_current_theme(self):
        """Applique le thème actuel"""
        settings = Gtk.Settings.get_default()
        if not settings:
            return
            
        # Détecter si le thème sombre est préféré
        prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
        theme_name = settings.get_property("gtk-theme-name")
        
        # Déterminer si c'est un thème sombre
        is_dark_theme = prefer_dark or self._is_dark_theme(theme_name)
        
        # Appliquer les classes CSS appropriées
        style_context = self.window.get_style_context()
        
        if is_dark_theme:
            style_context.add_class("dark")
            style_context.remove_class("light")
            self.current_theme = "dark"
        else:
            style_context.add_class("light")
            style_context.remove_class("dark")
            self.current_theme = "light"
        
        # Notifier les composants du changement de thème
        self._notify_theme_change(self.current_theme)
    
    def _is_dark_theme(self, theme_name: str) -> bool:
        """Détermine si un thème est sombre basé sur son nom"""
        dark_indicators = ['dark', 'noir', 'black', 'sombre', 'adwaita-dark']
        theme_lower = theme_name.lower()
        return any(indicator in theme_lower for indicator in dark_indicators)
    
    def _notify_theme_change(self, theme_type: str):
        """Notifie les composants du changement de thème"""
        # Émettre un signal personnalisé pour les composants qui en ont besoin
        # Pour l'instant, on utilise une approche simple avec des callbacks
        pass
    
    def get_current_theme(self) -> str:
        """Retourne le thème actuel ('dark' ou 'light')"""
        return self.current_theme or "light"
    
    def force_theme(self, theme_type: str):
        """Force l'utilisation d'un thème spécifique"""
        if theme_type not in ["dark", "light"]:
            return
            
        style_context = self.window.get_style_context()
        
        if theme_type == "dark":
            style_context.add_class("dark")
            style_context.remove_class("light")
        else:
            style_context.add_class("light")
            style_context.remove_class("dark")
            
        self.current_theme = theme_type
        self._notify_theme_change(theme_type)