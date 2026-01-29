# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage

class DuplicatesPage(BasePage):
    def setup_ui(self):
        title = Gtk.Label(label=self._("Recherche de Doublons"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.pack_start(title, False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        select_btn = Gtk.Button(label=self._("Scanner un dossier"))
        select_btn.get_style_context().add_class("suggested-action")
        select_btn.connect("clicked", self.main_window.on_select_duplicate_folder_clicked)
        toolbar.pack_start(select_btn, False, False, 0)

        self.main_window.duplicate_spinner = Gtk.Spinner()
        toolbar.pack_start(self.main_window.duplicate_spinner, False, False, 0)
        self.pack_start(toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.main_window.duplicate_liststore = Gtk.ListStore(bool, str, str, str) # Checkbox, Hash, Taille, Fichiers
        self.main_window.duplicate_treeview = Gtk.TreeView(model=self.main_window.duplicate_liststore)

        # Colonne Checkbox
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_toggled)
        column_toggle = Gtk.TreeViewColumn(self._("Sél."), renderer_toggle, active=0)
        self.main_window.duplicate_treeview.append_column(column_toggle)

        for i, col_title in enumerate([self._("Hash (ID)"), self._("Taille"), self._("Fichiers")], start=1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            self.main_window.duplicate_treeview.append_column(column)

        scrolled.add(self.main_window.duplicate_treeview)
        self.pack_start(scrolled, True, True, 0)

        # Bouton de suppression des sélectionnés
        delete_btn = Gtk.Button(label=self._("Supprimer les doublons sélectionnés"))
        delete_btn.get_style_context().add_class("destructive-action")
        delete_btn.connect("clicked", self.on_delete_selected_clicked)
        self.pack_start(delete_btn, False, False, 0)

    def on_toggled(self, widget, path):
        self.main_window.duplicate_liststore[path][0] = not self.main_window.duplicate_liststore[path][0]

    def on_delete_selected_clicked(self, widget):
        # Logique de suppression à implémenter dans modern_main ou ici
        count = 0
        for row in self.main_window.duplicate_liststore:
            if row[0]: # Si coché
                count += 1

        if count > 0:
            self.main_window.show_info_dialog(self._("Suppression"),
                                           f"{count} " + self._("groupes de doublons marqués pour suppression (fonctionnalité en cours de finalisation)."))
        else:
            self.main_window.show_info_dialog(self._("Info"), self._("Veuillez sélectionner des doublons à supprimer."))
