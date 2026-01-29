# -*- coding: utf-8 -*-
"""
Gestionnaire de thèmes v3.0 pour l'Interface Moderne Avancée
Support des thèmes adaptatifs avec variables CSS et détection automatique
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, Gdk
import os

class ThemeManager:
    """Gestionnaire de thèmes avancé pour l'adaptation automatique sombre/clair v3.0"""
    
    def __init__(self, window: Gtk.Window):
        self.window = window
        self.css_provider = Gtk.CssProvider()
        self.accent_provider = Gtk.CssProvider()
        self.current_theme = None
        self.accent_color = None
        self.theme_callbacks = []
        
        # Charger les styles CSS v3.0
        self._load_v3_css()
        
        # Surveiller les changements de thème système
        self._setup_theme_monitoring()
        
        # Appliquer le thème initial
        self._apply_current_theme()

    def set_accent_color(self, color_hex: str):
        """Définit une couleur d'accentuation personnalisée"""
        self.accent_color = color_hex
        accent_css = f"""
        :root {{
            --accent-primary: {color_hex};
            --accent-active: {color_hex};
        }}
        .sidebar-button-active {{
            background-color: var(--accent-primary) !important;
        }}
        .suggested-action {{
            background: linear-gradient(135deg, {color_hex}, var(--accent-info)) !important;
        }}
        """
        try:
            self.accent_provider.load_from_data(accent_css.encode('utf-8'))
            screen = self.window.get_screen() or Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen,
                    self.accent_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
                )
        except Exception as e:
            print(f"Erreur lors de l'application de la couleur d'accent: {e}")
    
    def _load_v3_css(self):
        """Charge les styles CSS v3.0 avec variables et thèmes adaptatifs"""
        # Le CSS principal est déjà chargé depuis style.css
        # Ici on ajoute des styles dynamiques supplémentaires
        
        dynamic_css = """
        /* Styles dynamiques v3.0 pour l'adaptation de thème */
        
        /* Transitions fluides pour les changements de thème */
        * {
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }
        
        /* Styles spécifiques pour l'intégration explorateur */
        .file-context-menu {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 8px 25px var(--shadow-medium);
            padding: 5px 0;
        }
        
        .file-context-menu menuitem {
            padding: 8px 15px;
            color: var(--text-primary);
            font-size: 0.9em;
            transition: background-color 0.2s ease;
        }
        
        .file-context-menu menuitem:hover {
            background-color: var(--explorer-hover);
        }
        
        .file-context-menu separator {
            background-color: var(--border-color);
            margin: 5px 0;
        }
        
        /* Styles pour les notifications v3.0 */
        .notification-modern {
            background-color: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px 20px;
            box-shadow: 0 8px 25px var(--shadow-medium);
            margin: 10px;
        }
        
        .notification-success {
            border-left: 4px solid var(--accent-success);
        }
        
        .notification-error {
            border-left: 4px solid var(--accent-danger);
        }
        
        .notification-warning {
            border-left: 4px solid var(--accent-warning);
        }
        
        .notification-info {
            border-left: 4px solid var(--accent-info);
        }
        
        /* Styles pour les spinners et indicateurs de chargement */
        .loading-spinner {
            color: var(--accent-primary);
        }
        
        /* Styles pour les graphiques matplotlib intégrés */
        .chart-container {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            border: 1px solid var(--border-color);
        }
        
        /* Amélioration des tooltips v3.0 */
        .tooltip-v3 {
            background-color: var(--bg-sidebar);
            color: var(--text-sidebar);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 0.9em;
            font-weight: 500;
            box-shadow: 0 6px 20px var(--shadow-medium);
            max-width: 300px;
        }
        
        /* Styles pour les colonnes redimensionnables */
        .resizable-column {
            border-right: 1px solid var(--border-light);
            min-width: 100px;
        }
        
        .resizable-column:last-child {
            border-right: none;
        }
        
        .column-header {
            background-color: var(--bg-secondary);
            color: var(--column-header);
            font-weight: 600;
            padding: 10px 12px;
            border-bottom: 2px solid var(--border-color);
        }
        
        .column-header:hover {
            background-color: var(--bg-hover);
        }
        
        /* Styles pour les chemins de fichiers */
        .file-path {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            font-size: 0.85em;
            color: var(--path-text);
            background-color: var(--bg-secondary);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid var(--border-light);
        }
        
        /* Animation pour les éléments qui apparaissent */
        .slide-in-right {
            animation: slideInRight 0.3s ease-out;
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        /* Styles pour les badges de version */
        .version-badge {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-info));
            color: white;
            font-size: 0.75em;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 15px;
            box-shadow: 0 2px 8px var(--shadow-light);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Styles pour les indicateurs d'état */
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .status-success {
            background-color: var(--accent-success);
        }
        
        .status-warning {
            background-color: var(--accent-warning);
        }
        
        .status-error {
            background-color: var(--accent-danger);
        }
        
        .status-info {
            background-color: var(--accent-info);
        }
        """
        
        try:
            self.css_provider.load_from_data(dynamic_css.encode('utf-8'))
            
            # Appliquer le CSS à l'écran
            screen = self.window.get_screen() or Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, 
                    self.css_provider, 
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
                )
        except Exception as e:
            print(f"Erreur lors du chargement du CSS dynamique v3.0: {e}")
    
    def _setup_theme_monitoring(self):
        """Configure la surveillance avancée des changements de thème"""
        # Surveiller les paramètres GTK
        settings = Gtk.Settings.get_default()
        if settings:
            settings.connect("notify::gtk-theme-name", self._on_theme_changed)
            settings.connect("notify::gtk-application-prefer-dark-theme", self._on_theme_changed)
        
        # Surveiller les paramètres GNOME/système si disponibles
        try:
            gsettings = Gio.Settings.new("org.gnome.desktop.interface")
            gsettings.connect("changed::gtk-theme", self._on_gsettings_changed)
            gsettings.connect("changed::color-scheme", self._on_gsettings_changed)
        except Exception:
            # Pas de problème si GNOME n'est pas disponible
            pass
    
    def _on_theme_changed(self, settings, param):
        """Callback appelé lors du changement de thème GTK"""
        GLib.idle_add(self._apply_current_theme)
    
    def _on_gsettings_changed(self, settings, key):
        """Callback appelé lors du changement de paramètres GNOME"""
        GLib.idle_add(self._apply_current_theme)
    
    def _apply_current_theme(self):
        """Applique le thème actuel avec détection avancée"""
        theme_type = self._detect_theme_preference()
        
        # Appliquer les classes CSS appropriées à la fenêtre
        style_context = self.window.get_style_context()
        
        # Nettoyer les anciennes classes
        style_context.remove_class("theme-light")
        style_context.remove_class("theme-dark")
        
        # Appliquer la nouvelle classe
        if theme_type == "dark":
            style_context.add_class("theme-dark")
            self.current_theme = "dark"
        else:
            style_context.add_class("theme-light")
            self.current_theme = "light"
        
        # Notifier les composants du changement
        self._notify_theme_change(self.current_theme)
        
        print(f"Thème appliqué: {self.current_theme}")
    
    def _detect_theme_preference(self) -> str:
        """Détection avancée de la préférence de thème"""
        # 1. Vérifier les paramètres GTK
        settings = Gtk.Settings.get_default()
        if settings:
            prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
            if prefer_dark:
                return "dark"
            
            theme_name = settings.get_property("gtk-theme-name")
            if self._is_dark_theme_name(theme_name):
                return "dark"
        
        # 2. Vérifier les paramètres GNOME
        try:
            gsettings = Gio.Settings.new("org.gnome.desktop.interface")
            color_scheme = gsettings.get_string("color-scheme")
            if color_scheme == "prefer-dark":
                return "dark"
            
            gtk_theme = gsettings.get_string("gtk-theme")
            if self._is_dark_theme_name(gtk_theme):
                return "dark"
        except Exception:
            pass
        
        # 3. Détecter via les variables d'environnement
        import os
        if os.environ.get("GTK_THEME", "").lower().find("dark") != -1:
            return "dark"
        
        # 4. Par défaut, utiliser le thème clair
        return "light"
    
    def _is_dark_theme_name(self, theme_name: str) -> bool:
        """Détermine si un nom de thème indique un thème sombre"""
        if not theme_name:
            return False
            
        dark_indicators = [
            'dark', 'noir', 'black', 'sombre', 'adwaita-dark', 
            'breeze-dark', 'arc-dark', 'numix-dark', 'materia-dark',
            'yaru-dark', 'pop-dark', 'elementary-dark'
        ]
        
        theme_lower = theme_name.lower()
        return any(indicator in theme_lower for indicator in dark_indicators)
    
    def _notify_theme_change(self, theme_type: str):
        """Notifie tous les callbacks enregistrés du changement de thème"""
        for callback in self.theme_callbacks:
            try:
                callback(theme_type)
            except Exception as e:
                print(f"Erreur dans callback de thème: {e}")
    
    def register_theme_callback(self, callback):
        """Enregistre un callback pour les changements de thème"""
        if callback not in self.theme_callbacks:
            self.theme_callbacks.append(callback)
    
    def unregister_theme_callback(self, callback):
        """Désenregistre un callback"""
        if callback in self.theme_callbacks:
            self.theme_callbacks.remove(callback)
    
    def get_current_theme(self) -> str:
        """Retourne le thème actuel ('dark' ou 'light')"""
        return self.current_theme or "light"
    
    def is_dark_theme(self) -> bool:
        """Retourne True si le thème actuel est sombre"""
        return self.get_current_theme() == "dark"
    
    def force_theme(self, theme_type: str):
        """Force l'utilisation d'un thème spécifique"""
        if theme_type not in ["dark", "light", "auto"]:
            return
        
        if theme_type == "auto":
            # Réactiver la détection automatique
            self._apply_current_theme()
        else:
            # Forcer le thème spécifique
            style_context = self.window.get_style_context()
            
            # Nettoyer les anciennes classes
            style_context.remove_class("theme-light")
            style_context.remove_class("theme-dark")
            
            # Appliquer la nouvelle classe
            if theme_type == "dark":
                style_context.add_class("theme-dark")
            else:
                style_context.add_class("theme-light")
                
            self.current_theme = theme_type
            self._notify_theme_change(theme_type)
    
    def get_theme_colors(self) -> dict:
        """Retourne un dictionnaire des couleurs du thème actuel"""
        if self.is_dark_theme():
            return {
                'bg_primary': '#1a1a1a',
                'bg_secondary': '#2d2d2d',
                'bg_sidebar': '#1e1e1e',
                'text_primary': '#ffffff',
                'text_secondary': '#adb5bd',
                'accent_primary': '#0d6efd',
                'accent_success': '#198754',
                'accent_danger': '#dc3545',
                'border_color': '#404040'
            }
        else:
            return {
                'bg_primary': '#ffffff',
                'bg_secondary': '#f8f9fa',
                'bg_sidebar': '#343a40',
                'text_primary': '#212529',
                'text_secondary': '#6c757d',
                'accent_primary': '#007bff',
                'accent_success': '#28a745',
                'accent_danger': '#dc3545',
                'border_color': '#dee2e6'
            }
    
    def apply_theme_to_widget(self, widget: Gtk.Widget, style_class: str = None):
        """Applique le thème actuel à un widget spécifique"""
        style_context = widget.get_style_context()
        
        if style_class:
            style_context.add_class(style_class)
        
        # Appliquer la classe de thème
        if self.is_dark_theme():
            style_context.add_class("theme-dark")
            style_context.remove_class("theme-light")
        else:
            style_context.add_class("theme-light")
            style_context.remove_class("theme-dark")