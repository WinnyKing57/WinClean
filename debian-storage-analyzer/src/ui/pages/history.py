# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage

class HistoryPage(BasePage):
    def setup_ui(self):
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Label(label=self._("Historique des Opérations"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label=self._("Suivez l'évolution de votre stockage et vos actions de nettoyage"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        self.pack_start(header_box, False, False, 0)

        # Notebook
        notebook = Gtk.Notebook()

        # Tab 1: Analyses
        scan_box = self.main_window._create_scan_history_view()
        notebook.append_page(scan_box, Gtk.Label(label=self._("Analyses")))

        # Tab 2: Nettoyages
        clean_box = self.main_window._create_cleaning_history_view()
        notebook.append_page(clean_box, Gtk.Label(label=self._("Nettoyages")))

        # Tab 3: Tendances
        self.main_window.trend_box = self.main_window._create_trend_view()
        notebook.append_page(self.main_window.trend_box, Gtk.Label(label=self._("Tendances")))

        self.pack_start(notebook, True, True, 0)

        # Bouton Actualiser
        refresh_btn = Gtk.Button(label=self._("Actualiser l'historique"))
        refresh_btn.connect("clicked", lambda w: self.main_window._update_history_views())
        self.pack_start(refresh_btn, False, False, 0)
