# -*- coding: utf-8 -*-

import sys
import os
import gettext
import threading
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

# Setup i18n
APP_NAME = "debian-storage-analyzer"
LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'share', 'locale')
gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

# Ajout du chemin src pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
from analyzer.storage_analyzer import analyze_directory
from cleaner import system_cleaner, app_cleaner

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title(_("Analyseur de Stockage Debian"))
        self.set_default_size(900, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(self.hbox)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)

        self.sidebar = Gtk.StackSidebar()
        self.sidebar.set_stack(self.stack)
        self.sidebar.set_size_request(200, -1)
        self.hbox.pack_start(self.sidebar, False, False, 0)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.hbox.pack_start(separator, False, False, 0)

        self.hbox.pack_start(self.stack, True, True, 0)

        self._init_dashboard()
        self._init_analyzer()
        self._init_cleaner()
        self._init_large_files()

        self.show_all()

    def _init_dashboard(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(20)

        title = Gtk.Label(label=_("Tableau de Bord"))
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)

        # Stats
        usage = psutil.disk_usage('/')
        stats_text = (_("Partition Racine (/)") + "\n" +
                      _("Total: ") + self.format_size(usage.total) + "\n" +
                      _("Utilisé: ") + self.format_size(usage.used) + f" ({usage.percent}%)\n" +
                      _("Libre: ") + self.format_size(usage.free))

        self.stats_label = Gtk.Label(label=stats_text)
        page.pack_start(self.stats_label, False, False, 0)

        # Chart
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        labels = [_('Utilisé'), _('Libre')]
        sizes = [usage.used, usage.free]
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
        ax.axis('equal')

        canvas = FigureCanvas(fig)
        canvas.set_size_request(400, 300)
        page.pack_start(canvas, True, True, 0)

        self.stack.add_titled(page, "dashboard", "Dashboard")

    def _init_analyzer(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(20)

        title = Gtk.Label(label="Analyseur de Dossiers")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        select_button = Gtk.Button(label="Choisir un dossier")
        select_button.connect("clicked", self.on_select_folder_clicked)
        toolbar.pack_start(select_button, False, False, 0)

        self.analyzer_spinner = Gtk.Spinner()
        toolbar.pack_start(self.analyzer_spinner, False, False, 0)

        page.pack_start(toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.analyzer_liststore = Gtk.ListStore(str, str, bool) # Nom, Taille formatée, Est un dossier
        self.analyzer_treeview = Gtk.TreeView(model=self.analyzer_liststore)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Nom", renderer_text, text=0)
        self.analyzer_treeview.append_column(column_text)

        renderer_size = Gtk.CellRendererText()
        column_size = Gtk.TreeViewColumn("Taille", renderer_size, text=1)
        self.analyzer_treeview.append_column(column_size)

        scrolled.add(self.analyzer_treeview)
        page.pack_start(scrolled, True, True, 0)

        self.stack.add_titled(page, "analyzer", "Analyseur")

    def _init_cleaner(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(20)

        title = Gtk.Label(label="Nettoyeur Système et Apps")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)

        cleaners_list = Gtk.ListBox()
        cleaners_list.set_selection_mode(Gtk.SelectionMode.NONE)
        page.pack_start(cleaners_list, True, True, 0)

        def add_cleaner_row(name, description, action_callback):
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_border_width(10)
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.pack_start(Gtk.Label(label=name, xalign=0), False, False, 0)
            vbox.pack_start(Gtk.Label(label=description, xalign=0), False, False, 0)
            hbox.pack_start(vbox, True, True, 0)
            btn = Gtk.Button(label="Nettoyer")
            btn.connect("clicked", action_callback)
            hbox.pack_start(btn, False, False, 0)
            row.add(hbox)
            cleaners_list.add(row)

        add_cleaner_row("Cache APT", "Supprime les paquets téléchargés (.deb)", self.on_clean_apt_clicked)
        add_cleaner_row("Dépendances inutiles", "Supprime les paquets orphelins (autoremove)", self.on_autoremove_clicked)
        add_cleaner_row("Fichiers Temporaires", "Nettoie /tmp et /var/tmp (> 7 jours)", self.on_clean_temp_clicked)
        add_cleaner_row("Journaux Système", "Réduit la taille des logs journald", self.on_clean_logs_clicked)
        add_cleaner_row("Firefox Cache", "Nettoie le cache de Firefox", self.on_clean_firefox_clicked)
        add_cleaner_row("Flatpak Cache", "Nettoie le cache des applications Flatpak", self.on_clean_flatpak_clicked)

        self.stack.add_titled(page, "cleaner", "Nettoyeur")

    def _init_large_files(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(20)
        title = Gtk.Label(label="Fichiers Volumineux")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)
        self.stack.add_titled(page, "large_files", "Gros Fichiers")

    # --- Callbacks ---

    def on_select_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Choisir un dossier à analyser",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            self.start_analysis(folder)
        dialog.destroy()

    def start_analysis(self, folder):
        self.analyzer_liststore.clear()
        self.analyzer_spinner.start()
        thread = threading.Thread(target=self.run_analysis_thread, args=(folder,))
        thread.daemon = True
        thread.start()

    def run_analysis_thread(self, folder):
        results = analyze_directory(folder)
        GLib.idle_add(self.on_analysis_finished, results)

    def on_analysis_finished(self, results):
        for item in results:
            self.analyzer_liststore.append([
                os.path.basename(item.path),
                self.format_size(item.size),
                item.is_dir
            ])
        self.analyzer_spinner.stop()

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    # Cleaning actions
    def on_clean_apt_clicked(self, widget):
        self.run_privileged_task(_("Nettoyage APT"), "apt")

    def on_clean_temp_clicked(self, widget):
        self.run_privileged_task(_("Nettoyage Temporaires"), "temp")

    def on_clean_logs_clicked(self, widget):
        self.run_privileged_task(_("Nettoyage Journaux"), "logs")

    def on_autoremove_clicked(self, widget):
        self.run_privileged_task(_("Autoremove APT"), "autoremove")

    def on_clean_firefox_clicked(self, widget):
        self.run_clean_task(_("Nettoyage Firefox"), app_cleaner.clean_firefox_cache)

    def on_clean_flatpak_clicked(self, widget):
        self.run_clean_task(_("Nettoyage Flatpak"), app_cleaner.clean_flatpak_cache)

    def run_clean_task(self, name, func):
        """Lance une tâche de nettoyage non privilégiée dans un thread."""
        def task():
            try:
                result = func()
                msg = _("Opération terminée.")
                if isinstance(result, (int, float)):
                    msg += f" {self.format_size(result)} " + _("libérés.")
                GLib.idle_add(self.show_info_dialog, name, msg)
            except Exception as e:
                GLib.idle_add(self.show_info_dialog, name, _("Erreur: ") + str(e))

        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    def run_privileged_task(self, name, action):
        """Lance une tâche privilégiée via pkexec."""
        def task():
            # Chercher le helper
            helper_path = "/usr/libexec/debian-storage-analyzer-helper"
            if not os.path.exists(helper_path):
                # Fallback pour le développement
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                helper_path = os.path.join(project_root, 'src', 'helpers', 'helper.py')

            try:
                cmd = ["pkexec", helper_path, action]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                GLib.idle_add(self.show_info_dialog, name, result.stdout)
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.show_info_dialog, name, _("Échec de l'authentification ou erreur système.") + f"\n{e.stderr}")
            except Exception as e:
                GLib.idle_add(self.show_info_dialog, name, _("Erreur: ") + str(e))

        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    def show_info_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

class Application(Gtk.Application):
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
