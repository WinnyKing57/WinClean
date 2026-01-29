# -*- coding: utf-8 -*-
import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage
from ui.file_explorer_integration import setup_treeview_context_menu

class AnalyzerPage(BasePage):
    def setup_ui(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Label(label=self._("Analyse de Stockage"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label=self._("Analyser l'utilisation de l'espace disque par dossier"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        self.pack_start(header_box, False, False, 0)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        select_button = Gtk.Button(label=self._("Choisir un Dossier"))
        select_button.get_style_context().add_class("suggested-action")
        select_button.connect("clicked", self.main_window.on_select_folder_clicked)
        toolbar.pack_start(select_button, False, False, 0)

        self.main_window.analyzer_spinner = Gtk.Spinner()
        toolbar.pack_start(self.main_window.analyzer_spinner, False, False, 0)

        self.main_window.stop_btn = Gtk.Button.new_from_icon_name("process-stop", Gtk.IconSize.BUTTON)
        self.main_window.stop_btn.set_sensitive(False)
        self.main_window.stop_btn.connect("clicked", self.main_window.on_stop_analysis_clicked)
        toolbar.pack_start(self.main_window.stop_btn, False, False, 0)

        spacer = Gtk.Box()
        toolbar.pack_start(spacer, True, True, 0)

        self.main_window.export_btn = Gtk.Button(label=self._("Exporter"))
        self.main_window.export_btn.set_sensitive(False)
        self.main_window.export_btn.connect("clicked", self.main_window.on_export_clicked)
        toolbar.pack_start(self.main_window.export_btn, False, False, 0)

        # Bouton Gros Fichiers
        large_files_btn = Gtk.Button(label=self._("Gros Fichiers"))
        large_files_btn.connect("clicked", self.on_large_files_clicked)
        toolbar.pack_start(large_files_btn, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

        # Search Bar (Future step 4 improvement included here for efficiency)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        search_label = Gtk.Label(label=self._("Filtrer :"))
        search_box.pack_start(search_label, False, False, 0)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        self.pack_start(search_box, False, False, 0)

        # Results
        results_frame = Gtk.Frame()
        results_frame.set_label(self._("Résultats d'Analyse"))
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 400)

        self.main_window.analyzer_liststore = Gtk.ListStore(str, str, bool, str, str)

        # Filter model for search
        self.filter_model = self.main_window.analyzer_liststore.filter_new()
        self.filter_model.set_visible_func(self.filter_func)

        self.main_window.analyzer_treeview = Gtk.TreeView(model=self.filter_model)
        self.main_window.analyzer_treeview.get_style_context().add_class("enhanced-treeview")

        renderer_text = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn(self._("Nom"), renderer_text, text=0)
        column_name.set_sort_column_id(0)
        column_name.set_resizable(True)
        column_name.set_min_width(200)
        self.main_window.analyzer_treeview.append_column(column_name)

        renderer_size = Gtk.CellRendererText()
        column_size = Gtk.TreeViewColumn(self._("Taille"), renderer_size, text=1)
        column_size.set_sort_column_id(1)
        column_size.set_resizable(True)
        self.main_window.analyzer_treeview.append_column(column_size)

        renderer_type = Gtk.CellRendererText()
        column_type = Gtk.TreeViewColumn(self._("Type"), renderer_type, text=3)
        column_type.set_sort_column_id(3)
        column_type.set_resizable(True)
        self.main_window.analyzer_treeview.append_column(column_type)

        renderer_path = Gtk.CellRendererText()
        renderer_path.set_property("ellipsize", 3)
        column_path = Gtk.TreeViewColumn(self._("Emplacement"), renderer_path, text=4)
        column_path.set_sort_column_id(4)
        column_path.set_resizable(True)
        column_path.set_min_width(300)
        self.main_window.analyzer_treeview.append_column(column_path)

        self.main_window.context_handler = setup_treeview_context_menu(self.main_window.analyzer_treeview, 4)

        scrolled.add(self.main_window.analyzer_treeview)
        results_frame.add(scrolled)
        self.pack_start(results_frame, True, True, 0)

    def on_search_changed(self, entry):
        self.filter_model.refilter()

    def filter_func(self, model, iter, data):
        search_query = self.search_entry.get_text().lower()
        if not search_query:
            return True

        # Filtre spécial pour les gros fichiers
        if search_query == ">100mb":
            try:
                # La taille est stockée formatée en colonne 1, mais on peut essayer de la recalculer
                # ou mieux, on aurait dû stocker la taille brute dans le modèle.
                # Pour l'instant on regarde si "GB" est présent ou si "MB" > 100
                size_str = model[iter][1]
                if "GB" in size_str or "TB" in size_str:
                    return True
                if "MB" in size_str:
                    val = float(size_str.split()[0])
                    return val > 100
                return False
            except:
                return True

        name = model[iter][0].lower()
        path = model[iter][4].lower()
        return search_query in name or search_query in path

    def on_large_files_clicked(self, widget):
        """Recherche les fichiers > 100MB dans le dossier actuel"""
        if not hasattr(self.main_window, 'last_analysis_results') or not self.main_window.last_analysis_results:
            self.main_window.show_info_dialog(self._("Info"), self._("Veuillez d'abord effectuer une analyse."))
            return

        # On va juste filtrer les résultats actuels pour l'instant ou refaire un scan plat
        self.search_entry.set_text(">100MB") # On pourrait implémenter un filtre spécial
        self.filter_model.refilter()
