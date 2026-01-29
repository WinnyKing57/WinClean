# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage

class PackagesPage(BasePage):
    def setup_ui(self):
        title = Gtk.Label(label=self._("Analyse des Paquets"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.pack_start(title, False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        refresh_btn = Gtk.Button(label=self._("Actualiser la liste"))
        refresh_btn.get_style_context().add_class("suggested-action")
        refresh_btn.connect("clicked", self.main_window.on_refresh_packages_clicked)
        toolbar.pack_start(refresh_btn, False, False, 0)

        self.main_window.package_spinner = Gtk.Spinner()
        toolbar.pack_start(self.main_window.package_spinner, False, False, 0)
        self.pack_start(toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.main_window.package_liststore = Gtk.ListStore(str, str, str, str)
        self.main_window.package_treeview = Gtk.TreeView(model=self.main_window.package_liststore)

        for i, col_title in enumerate([self._("Nom"), self._("Version"), self._("Taille"), self._("Type")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            self.main_window.package_treeview.append_column(column)

        scrolled.add(self.main_window.package_treeview)
        self.pack_start(scrolled, True, True, 0)
