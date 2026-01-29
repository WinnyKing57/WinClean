# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class BasePage(Gtk.Box):
    def __init__(self, main_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_border_width(30)
        self.main_window = main_window
        self._ = main_window._
        self.setup_ui()

    def setup_ui(self):
        pass
