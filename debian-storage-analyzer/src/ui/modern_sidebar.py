# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib
import gettext

_ = gettext.gettext

class ModernSidebar:
    """Sidebar moderne avec navigation fluide et support des thèmes"""
    
    def __init__(self):
        self.sections = [
            ("dashboard", _("Dashboard"), "view-grid-symbolic"),
            ("analyzer", _("Analyse"), "folder-symbolic"),
            ("cleaner", _("Nettoyage"), "edit-clear-symbolic"),
            ("history", _("Historique"), "document-open-recent-symbolic"),
            ("settings", _("Paramètres"), "preferences-system-symbolic")
        ]
        
    def create_sidebar(self, stack: Gtk.Stack) -> Gtk.Widget:
        """Crée la sidebar moderne avec icônes et transitions fluides"""
        
        # Container principal pour la sidebar
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.set_size_request(220, -1)
        sidebar_box.get_style_context().add_class("sidebar")
        
        # Header de la sidebar
        header = self._create_header()
        sidebar_box.pack_start(header, False, False, 0)
        
        # Séparateur
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_box.pack_start(separator, False, False, 0)
        
        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        nav_box.set_margin_top(10)
        nav_box.set_margin_bottom(10)
        nav_box.set_margin_left(10)
        nav_box.set_margin_right(10)
        
        self.nav_buttons = {}
        
        for section_id, section_name, icon_name in self.sections:
            button = self._create_nav_button(section_id, section_name, icon_name, stack)
            nav_box.pack_start(button, False, False, 0)
            self.nav_buttons[section_id] = button
            
        sidebar_box.pack_start(nav_box, False, False, 0)
        
        # Spacer pour pousser le footer vers le bas
        spacer = Gtk.Box()
        sidebar_box.pack_start(spacer, True, True, 0)
        
        # Footer avec informations système
        footer = self._create_footer()
        sidebar_box.pack_start(footer, False, False, 0)
        
        return sidebar_box
    
    def _create_header(self) -> Gtk.Widget:
        """Crée le header de la sidebar avec titre et logo"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        header_box.set_margin_top(15)
        header_box.set_margin_bottom(15)
        header_box.set_margin_left(15)
        header_box.set_margin_right(15)
        
        # Logo/Icône
        icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_margin_bottom(5)
        header_box.pack_start(icon, False, False, 0)
        
        # Titre
        title = Gtk.Label(label=_("Storage Analyzer"))
        title.get_style_context().add_class("sidebar-title")
        title.set_halign(Gtk.Align.CENTER)
        header_box.pack_start(title, False, False, 0)
        
        # Sous-titre
        subtitle = Gtk.Label(label=_("Debian Edition"))
        subtitle.get_style_context().add_class("sidebar-subtitle")
        subtitle.set_halign(Gtk.Align.CENTER)
        header_box.pack_start(subtitle, False, False, 0)
        
        return header_box
    
    def _create_nav_button(self, section_id: str, section_name: str, icon_name: str, stack: Gtk.Stack) -> Gtk.Widget:
        """Crée un bouton de navigation avec icône"""
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class("sidebar-button")
        
        # Container pour icône + texte
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_left(12)
        box.set_margin_right(12)
        
        # Icône
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        box.pack_start(icon, False, False, 0)
        
        # Label
        label = Gtk.Label(label=section_name)
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, True, True, 0)
        
        button.add(box)
        
        # Connecter le signal de clic
        button.connect("clicked", self._on_nav_button_clicked, section_id, stack)
        
        return button
    
    def _create_footer(self) -> Gtk.Widget:
        """Crée le footer avec informations système"""
        footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        footer_box.set_margin_top(10)
        footer_box.set_margin_bottom(15)
        footer_box.set_margin_left(15)
        footer_box.set_margin_right(15)
        
        # Séparateur
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        footer_box.pack_start(separator, False, False, 0)
        
        # Version info
        version_label = Gtk.Label(label=_("Version 2.0"))
        version_label.get_style_context().add_class("sidebar-footer")
        version_label.set_halign(Gtk.Align.CENTER)
        version_label.set_margin_top(10)
        footer_box.pack_start(version_label, False, False, 0)
        
        return footer_box
    
    def _on_nav_button_clicked(self, button: Gtk.Button, section_id: str, stack: Gtk.Stack):
        """Gère le clic sur un bouton de navigation"""
        # Mettre à jour l'état visuel des boutons
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == section_id:
                btn.get_style_context().add_class("sidebar-button-active")
            else:
                btn.get_style_context().remove_class("sidebar-button-active")
        
        # Changer de page dans le stack
        stack.set_visible_child_name(section_id)
    
    def set_active_section(self, section_id: str):
        """Met à jour visuellement la section active"""
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == section_id:
                btn.get_style_context().add_class("sidebar-button-active")
            else:
                btn.get_style_context().remove_class("sidebar-button-active")