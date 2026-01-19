# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

class MainWindow(Gtk.ApplicationWindow):
    """
    Fenêtre principale de l'application d'analyse de stockage.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Analyseur de Stockage Debian")
        self.set_default_size(600, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)

        # Conteneur principal
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        self.add(grid)

        # === Boutons d'action ===
        analyze_button = Gtk.Button(label="Analyser un dossier")
        clean_button = Gtk.Button(label="Nettoyage Système")
        delete_button = Gtk.Button(label="Nettoyage Fichiers Personnels")

        # Pour l'instant, ces boutons n'auront pas d'action.
        # analyze_button.connect("clicked", self.on_analyze_clicked)
        # clean_button.connect("clicked", self.on_clean_clicked)
        # delete_button.connect("clicked", self.on_delete_clicked)

        grid.attach(analyze_button, 0, 0, 1, 1)
        grid.attach(clean_button, 1, 0, 1, 1)
        grid.attach(delete_button, 2, 0, 1, 1)

        self.show_all()

class Application(Gtk.Application):
    """
    Classe principale de l'application GTK.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="fr.jules.debianstorageanalyzer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self)
        self.window.present()

if __name__ == "__main__":
    app = Application()
    sys.exit(app.run(sys.argv))
