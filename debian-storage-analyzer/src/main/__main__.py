# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib
from analyzer import personal_analyzer
from cleaner import app_cleaner
import threading
import subprocess
import psutil
import os

class MainWindow(Gtk.ApplicationWindow):
    """
    Fenêtre principale de l'application, organisée en tableau de bord.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Analyseur de Stockage Debian - Tableau de Bord")
        self.set_default_size(800, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)

        # Conteneur principal horizontal
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add(main_hbox)

        # === Stack et Sidebar pour la navigation ===
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)

        stack_sidebar = Gtk.StackSidebar()
        stack_sidebar.set_stack(self.stack)

        main_hbox.pack_start(stack_sidebar, False, False, 0)
        main_hbox.pack_start(self.stack, True, True, 0)

        # === Page 1: Tableau de Bord (Dashboard) ===
        dashboard_grid = self.create_dashboard_page()
        self.stack.add_titled(dashboard_grid, "dashboard", "Tableau de Bord")

        # === Page 2: Nettoyeur Système ===
        cleaner_grid = self.create_cleaner_page()
        self.stack.add_titled(cleaner_grid, "cleaner", "Nettoyeur")

        # === Page 3: Analyseur Personnel ===
        analyzer_grid = self.create_analyzer_page()
        self.stack.add_titled(analyzer_grid, "analyzer", "Analyseur Fichiers")

        # Lancer la mise à jour des statistiques système
        self.update_system_stats()
        GLib.timeout_add_seconds(2, self.update_system_stats)

        self.show_all()

    def update_system_stats(self):
        """Met à jour les labels du tableau de bord avec les stats système."""
        # CPU
        cpu_percent = psutil.cpu_percent()
        self.cpu_value_label.set_text(f"{cpu_percent:.1f} %")

        # RAM
        mem = psutil.virtual_memory()
        self.ram_value_label.set_text(
            f"{mem.percent:.1f} % "
            f"({mem.used / 1024**3:.1f} Go / {mem.total / 1024**3:.1f} Go)"
        )

        # Disque
        disk = psutil.disk_usage('/')
        self.disk_value_label.set_text(
            f"{disk.percent:.1f} % "
            f"({disk.used / 1024**3:.1f} Go / {disk.total / 1024**3:.1f} Go)"
        )

        # Renvoyer True pour que le timer continue
        return True

    def on_clean_selected(self, widget):
        """Exécute les tâches de nettoyage sélectionnées."""
        total_freed_space = 0

        # --- Nettoyage des applications (sans privilèges) ---
        if self.clean_firefox_check.get_active():
            total_freed_space += app_cleaner.clean_firefox_cache()
        if self.clean_chrome_check.get_active():
            total_freed_space += app_cleaner.clean_chromium_cache()

        # --- Nettoyage système (avec privilèges) ---
        try:
            if self.clean_apt_check.get_active():
                subprocess.run(['pkexec', 'debian-storage-analyzer-helper', 'apt'], check=True)
            if self.clean_temp_check.get_active():
                 subprocess.run(['pkexec', 'debian-storage-analyzer-helper', 'temp'], check=True)
            if self.clean_logs_check.get_active():
                 subprocess.run(['pkexec', 'debian-storage-analyzer-helper', 'logs'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Erreur lors de l'exécution du nettoyage système : {e}")

        # Afficher le résultat
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Nettoyage terminé"
        )
        dialog.format_secondary_text(
            f"L'opération a libéré environ {personal_analyzer.format_size(total_freed_space)} d'espace disque."
        )
        dialog.run()
        dialog.destroy()

    def create_dashboard_page(self):
        """Crée la page du tableau de bord avec des placeholders."""
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=20)

        title = Gtk.Label(xalign=0)
        title.set_markup("<big><b>Statut du Système</b></big>")

        cpu_label = Gtk.Label(label="Utilisation CPU :", xalign=0)
        self.cpu_value_label = Gtk.Label(label="N/A", xalign=0)

        ram_label = Gtk.Label(label="Utilisation RAM :", xalign=0)
        self.ram_value_label = Gtk.Label(label="N/A", xalign=0)

        disk_label = Gtk.Label(label="Utilisation Disque (/) :", xalign=0)
        self.disk_value_label = Gtk.Label(label="N/A", xalign=0)

        grid.attach(title, 0, 0, 2, 1)
        grid.attach(Gtk.Separator(), 0, 1, 2, 1)
        grid.attach(cpu_label, 0, 2, 1, 1)
        grid.attach(self.cpu_value_label, 1, 2, 1, 1)
        grid.attach(ram_label, 0, 3, 1, 1)
        grid.attach(self.ram_value_label, 1, 3, 1, 1)
        grid.attach(disk_label, 0, 4, 1, 1)
        grid.attach(self.disk_value_label, 1, 4, 1, 1)

        return grid

    def create_cleaner_page(self):
        """Crée la page du nettoyeur."""
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=20)

        system_frame = Gtk.Frame(label="Nettoyage du Système")
        system_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=10)
        system_frame.add(system_box)

        self.clean_apt_check = Gtk.CheckButton(label="Nettoyer le cache APT")
        self.clean_temp_check = Gtk.CheckButton(label="Nettoyer les fichiers temporaires (anciens)")
        self.clean_logs_check = Gtk.CheckButton(label="Nettoyer les journaux système")
        system_box.pack_start(self.clean_apt_check, False, False, 0)
        system_box.pack_start(self.clean_temp_check, False, False, 0)
        system_box.pack_start(self.clean_logs_check, False, False, 0)

        apps_frame = Gtk.Frame(label="Nettoyage des Applications")
        apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=10)
        apps_frame.add(apps_box)

        self.clean_firefox_check = Gtk.CheckButton(label="Nettoyer le cache de Firefox")
        self.clean_chrome_check = Gtk.CheckButton(label="Nettoyer le cache de Chromium")
        apps_box.pack_start(self.clean_firefox_check, False, False, 0)
        apps_box.pack_start(self.clean_chrome_check, False, False, 0)

        clean_button = Gtk.Button(label="Lancer le Nettoyage Sélectionné")
        clean_button.set_margin_top(10)
        clean_button.connect("clicked", self.on_clean_selected)

        grid.attach(system_frame, 0, 0, 1, 1)
        grid.attach(apps_frame, 0, 1, 1, 1)
        grid.attach(clean_button, 0, 2, 1, 1)

        return grid

    def create_analyzer_page(self):
        """Crée la page de l'analyseur de fichiers personnels."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=20)
        box.set_hexpand(True)
        box.set_vexpand(True)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        analyze_button = Gtk.Button(label="Analyser le dossier personnel (~)")
        analyze_button.connect("clicked", self.on_analyze_personal_files)
        self.delete_button = Gtk.Button(label="Supprimer la sélection")
        self.delete_button.set_sensitive(False)
        self.delete_button.connect("clicked", self.on_delete_personal_files)

        header_box.pack_start(analyze_button, False, False, 0)
        header_box.pack_start(self.delete_button, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        self.personal_files_store = Gtk.ListStore(bool, str, str, int)
        self.treeview = Gtk.TreeView(model=self.personal_files_store)

        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_file_toggled)
        column_toggle = Gtk.TreeViewColumn("Suppr.", renderer_toggle, active=0)
        self.treeview.append_column(column_toggle)

        renderer_text = Gtk.CellRendererText()
        column_path = Gtk.TreeViewColumn("Chemin", renderer_text, text=1)
        self.treeview.append_column(column_path)

        column_size = Gtk.TreeViewColumn("Taille", renderer_text, text=2)
        self.treeview.append_column(column_size)

        scrolled_window.add(self.treeview)

        self.spinner = Gtk.Spinner()
        self.spinner.set_margin_top(20)

        box.pack_start(header_box, False, False, 0)
        box.pack_start(scrolled_window, True, True, 0)
        box.pack_start(self.spinner, False, False, 0)

        return box

    def on_file_toggled(self, widget, path):
        """Appelé quand une case à cocher est cliquée dans le TreeView."""
        self.personal_files_store[path][0] = not self.personal_files_store[path][0]
        any_selected = any(row[0] for row in self.personal_files_store)
        self.delete_button.set_sensitive(any_selected)

    def on_analyze_personal_files(self, widget):
        """Lance l'analyse des fichiers personnels dans un thread séparé."""
        widget.set_sensitive(False)
        self.personal_files_store.clear()
        self.spinner.start()

        thread = threading.Thread(target=self._analyze_thread, args=(widget,))
        thread.daemon = True
        thread.start()

    def _analyze_thread(self, button):
        """Logique d'analyse exécutée dans le thread."""
        results = personal_analyzer.find_large_files(min_size_mb=50)

        def update_ui():
            self.personal_files_store.clear()
            for item in results:
                readable_size = personal_analyzer.format_size(item.size)
                self.personal_files_store.append([False, item.path, readable_size, item.size])
            self.spinner.stop()
            button.set_sensitive(True)

        GLib.idle_add(update_ui)

    def on_delete_personal_files(self, widget):
        """Supprime les fichiers sélectionnés par l'utilisateur après confirmation."""
        selected_files = []
        total_size = 0
        for i, row in enumerate(self.personal_files_store):
            if row[0]:
                selected_files.append((self.personal_files_store.get_iter(i), row[1], row[3]))
                total_size += row[3]

        if not selected_files:
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Êtes-vous sûr de vouloir supprimer définitivement {len(selected_files)} fichier(s) ?"
        )
        dialog.format_secondary_text(
            f"Cette action est irréversible et libérera environ "
            f"{personal_analyzer.format_size(total_size)} d'espace disque."
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            iters_to_remove = []
            for path_iter, path, size in selected_files:
                try:
                    os.unlink(path)
                    iters_to_remove.append(path_iter)
                except OSError as e:
                    print(f"Erreur lors de la suppression de {path}: {e}")

            for path_iter in reversed(iters_to_remove):
                self.personal_files_store.remove(path_iter)

            self.delete_button.set_sensitive(False)

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
