# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import gettext

_ = gettext.gettext

class TooltipManager:
    """Gestionnaire de tooltips contextuels pour l'interface"""
    
    def __init__(self):
        self.tooltips = {
            # Navigation
            "dashboard": _("Vue d'ensemble de l'utilisation du stockage système"),
            "analyzer": _("Analyser l'utilisation de l'espace disque par dossier"),
            "cleaner": _("Nettoyer les fichiers temporaires et caches système"),
            "history": _("Consulter l'historique des analyses et nettoyages"),
            "settings": _("Configurer les préférences de l'application"),
            
            # Boutons d'action
            "select_folder": _("Sélectionner un dossier à analyser"),
            "start_analysis": _("Démarrer l'analyse du dossier sélectionné"),
            "clean_selected": _("Nettoyer les éléments sélectionnés"),
            "dry_run": _("Prévisualiser les actions sans les exécuter"),
            "schedule_cleaning": _("Programmer un nettoyage automatique"),
            
            # Colonnes de tableau
            "column_name": _("Nom du fichier ou dossier"),
            "column_size": _("Taille en octets - Cliquer pour trier"),
            "column_date": _("Date de dernière modification - Cliquer pour trier"),
            "column_type": _("Type de fichier - Cliquer pour trier"),
            
            # Filtres
            "filter_size": _("Filtrer par taille minimale"),
            "filter_date": _("Filtrer par date de modification"),
            "filter_type": _("Filtrer par type de fichier"),
            
            # Graphiques
            "chart_pie": _("Répartition de l'espace disque par catégorie"),
            "chart_histogram": _("Taille des dossiers - Cliquer pour explorer"),
            
            # Nettoyage
            "clean_apt": _("Supprimer les paquets .deb téléchargés"),
            "clean_temp": _("Supprimer les fichiers temporaires anciens"),
            "clean_logs": _("Réduire la taille des journaux système"),
            "clean_firefox": _("Vider le cache du navigateur Firefox"),
            "clean_flatpak": _("Nettoyer le cache des applications Flatpak"),
            
            # Configuration
            "config_directories": _("Dossiers analysés par défaut"),
            "config_file_types": _("Types de fichiers à inclure/exclure"),
            "config_theme": _("Préférence de thème (auto/clair/sombre)"),
            "config_notifications": _("Activer les notifications desktop"),
            
            # Historique
            "history_analysis": _("Historique des analyses effectuées"),
            "history_cleaning": _("Historique des nettoyages effectués"),
            "export_csv": _("Exporter les données au format CSV"),
            "export_pdf": _("Générer un rapport PDF"),
        }
    
    def setup_tooltip(self, widget: Gtk.Widget, tooltip_key: str, custom_text: str = None):
        """Configure un tooltip pour un widget"""
        tooltip_text = custom_text or self.tooltips.get(tooltip_key, "")
        
        if tooltip_text:
            widget.set_tooltip_text(tooltip_text)
            widget.set_has_tooltip(True)
            
            # Connecter le signal pour les tooltips personnalisés
            widget.connect("query-tooltip", self._on_query_tooltip, tooltip_text)
    
    def setup_tooltips_for_container(self, container: Gtk.Container, tooltip_mapping: dict):
        """Configure les tooltips pour tous les widgets d'un container"""
        def setup_recursive(widget, mapping):
            # Si le widget a un nom, chercher le tooltip correspondant
            widget_name = Gtk.Buildable.get_name(widget) if hasattr(widget, 'get_name') else None
            
            if widget_name and widget_name in mapping:
                self.setup_tooltip(widget, mapping[widget_name])
            
            # Traiter récursivement les enfants
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    setup_recursive(child, mapping)
        
        setup_recursive(container, tooltip_mapping)
    
    def _on_query_tooltip(self, widget: Gtk.Widget, x: int, y: int, keyboard_mode: bool, tooltip: Gtk.Tooltip, tooltip_text: str) -> bool:
        """Callback pour afficher un tooltip personnalisé"""
        tooltip.set_text(tooltip_text)
        return True
    
    def create_rich_tooltip(self, title: str, description: str, shortcut: str = None) -> str:
        """Crée un tooltip riche avec titre, description et raccourci"""
        tooltip_parts = [f"<b>{title}</b>"]
        
        if description:
            tooltip_parts.append(description)
        
        if shortcut:
            tooltip_parts.append(f"<i>Raccourci: {shortcut}</i>")
        
        return "\n".join(tooltip_parts)
    
    def setup_rich_tooltip(self, widget: Gtk.Widget, title: str, description: str, shortcut: str = None):
        """Configure un tooltip riche avec markup"""
        tooltip_markup = self.create_rich_tooltip(title, description, shortcut)
        widget.set_tooltip_markup(tooltip_markup)
        widget.set_has_tooltip(True)
    
    def add_custom_tooltip(self, key: str, text: str):
        """Ajoute un tooltip personnalisé au dictionnaire"""
        self.tooltips[key] = text
    
    def get_tooltip_text(self, key: str) -> str:
        """Récupère le texte d'un tooltip par sa clé"""
        return self.tooltips.get(key, "")
    
    def setup_interactive_tooltip(self, widget: Gtk.Widget, tooltip_callback):
        """Configure un tooltip interactif avec callback personnalisé"""
        widget.set_has_tooltip(True)
        widget.connect("query-tooltip", tooltip_callback)
    
    def create_contextual_tooltip(self, base_key: str, context_data: dict) -> str:
        """Crée un tooltip contextuel basé sur des données"""
        base_text = self.tooltips.get(base_key, "")
        
        if not context_data:
            return base_text
        
        # Ajouter des informations contextuelles
        context_parts = []
        for key, value in context_data.items():
            if value is not None:
                context_parts.append(f"{key}: {value}")
        
        if context_parts:
            return f"{base_text}\n\n" + "\n".join(context_parts)
        
        return base_text