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
LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'locale')
gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

# Ajout du chemin src pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
from analyzer.storage_analyzer import analyze_directory
from analyzer.package_analyzer import PackageAnalyzer
from analyzer.duplicate_detector import DuplicateDetector
from cleaner import system_cleaner, app_cleaner
from helpers.history_db import HistoryManager
from helpers.report_generator import ReportGenerator
from config.configuration_manager import ConfigurationManager
from cleaner.scheduled_cleaner import ScheduledCleaner
from ui.modern_sidebar import ModernSidebar
from ui.theme_manager import ThemeManager
from ui.tooltip_manager import TooltipManager
from ui.pages.dashboard import DashboardPage
from ui.pages.analyzer import AnalyzerPage
from ui.pages.duplicates import DuplicatesPage
from ui.pages.packages import PackagesPage
from ui.pages.cleaner import CleanerPage
from ui.pages.history import HistoryPage
from ui.pages.settings import SettingsPage

class ModernMainWindow(Gtk.ApplicationWindow):
    """Interface principale modernisée avec sidebar et thèmes adaptatifs"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title(_("Analyseur de Stockage Debian 3.1"))
        self.set_default_size(1200, 800)  # Taille plus grande pour les nouvelles colonnes
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Charger le CSS
        self._load_css()

        # Initialiser les gestionnaires
        self.config_manager = ConfigurationManager()
        self.theme_manager = ThemeManager(self)
        self.tooltip_manager = TooltipManager()
        self.sidebar = ModernSidebar()
        self.history_manager = HistoryManager()
        self.package_analyzer = PackageAnalyzer()
        self.duplicate_detector = DuplicateDetector()
        self.scheduled_cleaner = ScheduledCleaner()
        self.abort_event = threading.Event()
        self.last_analysis_results = []
        
        # Créer l'interface
        self._setup_ui()
        
        # Configurer les tooltips
        self._setup_tooltips()
        
        self.show_all()
        
        # Activer la première section
        self.sidebar.set_active_section("dashboard")

        # Charger l'historique initialement
        self._update_history_views()

    def _setup_ui(self):
        """Configure l'interface utilisateur principale"""
        
        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(main_box)
        
        # Stack pour les pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(250)
        
        # Créer la sidebar moderne
        sidebar_widget = self.sidebar.create_sidebar(self.stack)
        main_box.pack_start(sidebar_widget, False, False, 0)
        
        # Séparateur
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.pack_start(separator, False, False, 0)
        
        # Zone de contenu principal
        main_box.pack_start(self.stack, True, True, 0)
        
        # Initialiser les pages (v3.1 refactoring)
        self.pages = {
            "dashboard": DashboardPage(self),
            "analyzer": AnalyzerPage(self),
            "duplicates": DuplicatesPage(self),
            "packages": PackagesPage(self),
            "cleaner": CleanerPage(self),
            "history": HistoryPage(self),
            "settings": SettingsPage(self)
        }

        for name, page in self.pages.items():
            self.stack.add_named(page, name)

    def _load_css(self):
        """Charge les styles CSS personnalisés"""
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ui', 'style.css')
        if os.path.exists(css_path):
            try:
                css_provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_screen(
                    gi.repository.Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                print(f"Erreur lors du chargement du CSS : {e}")

    
    def _create_stat_row(self, label: str, value: str) -> Gtk.Widget:
        """Crée une ligne de statistique avec label et valeur"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_halign(Gtk.Align.START)
        label_widget.get_style_context().add_class("stat-label")
        box.pack_start(label_widget, True, True, 0)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.get_style_context().add_class("stat-value")
        box.pack_start(value_widget, False, False, 0)
        
        return box

    
    def _add_modern_cleaner_row(self, listbox: Gtk.ListBox, name: str, description: str, 
                              callback, tooltip_key: str):
        """Ajoute une ligne de nettoyage modernisée"""
        row = Gtk.ListBoxRow()
        row.set_margin_top(5)
        row.set_margin_bottom(5)
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox.set_border_width(15)
        
        # Icône
        icon = Gtk.Image.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        hbox.pack_start(icon, False, False, 0)
        
        # Texte
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        name_label = Gtk.Label(label=name)
        name_label.set_halign(Gtk.Align.START)
        name_label.get_style_context().add_class("cleaner-name")
        vbox.pack_start(name_label, False, False, 0)
        
        desc_label = Gtk.Label(label=description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.get_style_context().add_class("cleaner-description")
        vbox.pack_start(desc_label, False, False, 0)
        
        hbox.pack_start(vbox, True, True, 0)
        
        # Boutons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Bouton dry-run (sera implémenté dans la tâche 5)
        dry_run_btn = Gtk.Button(label=_("Prévisualiser"))
        dry_run_btn.set_sensitive(False)  # Sera activé plus tard
        button_box.pack_start(dry_run_btn, False, False, 0)
        
        # Bouton nettoyer
        clean_btn = Gtk.Button(label=_("Nettoyer"))
        clean_btn.get_style_context().add_class("destructive-action")
        clean_btn.connect("clicked", callback)
        button_box.pack_start(clean_btn, False, False, 0)
        
        hbox.pack_start(button_box, False, False, 0)
        
        row.add(hbox)
        listbox.add(row)

    def _create_scan_history_view(self):
        """Crée la vue pour l'historique des analyses"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.scan_history_store = Gtk.ListStore(str, str, str) # Date, Chemin, Taille
        treeview = Gtk.TreeView(model=self.scan_history_store)

        for i, col_title in enumerate([_("Date"), _("Chemin"), _("Taille Totale")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            treeview.append_column(column)

        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        return box

    def _create_cleaning_history_view(self):
        """Crée la vue pour l'historique des nettoyages"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.clean_history_store = Gtk.ListStore(str, str, str) # Date, Action, Libéré
        treeview = Gtk.TreeView(model=self.clean_history_store)

        for i, col_title in enumerate([_("Date"), _("Action"), _("Espace Libéré")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            treeview.append_column(column)

        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        return box

    def on_refresh_packages_clicked(self, widget):
        self.package_liststore.clear()
        self.package_spinner.start()
        thread = threading.Thread(target=self.run_package_analysis_thread)
        thread.daemon = True
        thread.start()

    def run_package_analysis_thread(self):
        packages = self.package_analyzer.get_installed_packages(['deb', 'flatpak', 'snap'])
        GLib.idle_add(self.on_package_analysis_finished, packages)

    def on_package_analysis_finished(self, packages):
        for pkg_type, pkg_list in packages.items():
            for pkg in pkg_list:
                self.package_liststore.append([
                    pkg.name,
                    pkg.version,
                    self.format_size(pkg.size) if pkg.size > 0 else _("Inconnue"),
                    pkg.package_type.upper()
                ])
        self.package_spinner.stop()

    def on_select_duplicate_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title=_("Choisir un dossier pour les doublons"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            self.start_duplicate_scan(folder)
        dialog.destroy()

    def start_duplicate_scan(self, folder):
        self.duplicate_liststore.clear()
        self.duplicate_spinner.start()
        thread = threading.Thread(target=self.run_duplicate_thread, args=(folder,))
        thread.daemon = True
        thread.start()

    def run_duplicate_thread(self, folder):
        duplicates = self.duplicate_detector.find_duplicates(folder)
        GLib.idle_add(self.on_duplicate_finished, duplicates)

    def on_duplicate_finished(self, duplicates):
        for hash_val, group in duplicates.items():
            self.duplicate_liststore.append([
                False, # Checkbox
                hash_val[:12],
                self.format_size(group.file_size),
                ", ".join([os.path.basename(p) for p in group.file_paths])
            ])
        self.duplicate_spinner.stop()

    def _create_trend_view(self):
        """Crée la vue pour les tendances (graphique)"""
        self.trend_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.trend_box.set_border_width(10)

        # Le graphique sera ajouté lors de l'actualisation
        return self.trend_box

    def _update_history_views(self):
        """Met à jour les données dans l'UI d'historique"""
        # Mise à jour des scans
        self.scan_history_store.clear()
        scans = self.history_manager.get_scan_history()
        for s in scans:
            self.scan_history_store.append([
                s['timestamp'],
                s['path'],
                self.format_size(s['total_size'])
            ])

        # Mise à jour des nettoyages
        self.clean_history_store.clear()
        cleanings = self.history_manager.get_cleaning_history()
        for c in cleanings:
            self.clean_history_store.append([
                c['timestamp'],
                c['action_type'],
                self.format_size(c['freed_space'])
            ])

        # Mise à jour du graphique de tendance
        self._update_trend_chart()

    def _update_trend_chart(self):
        """Génère et affiche le graphique de tendance"""
        for child in self.trend_box.get_children():
            self.trend_box.remove(child)

        trends = self.history_manager.get_trends()
        if not trends:
            label = Gtk.Label(label=_("Pas assez de données pour afficher les tendances."))
            self.trend_box.pack_start(label, True, True, 0)
            self.trend_box.show_all()
            return

        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        fig.patch.set_facecolor('none')

        days = [t['day'] for t in trends]
        sizes = [t['avg_size'] / (1024*1024*1024) for t in trends] # GB

        ax.plot(days, sizes, marker='o', linestyle='-', color='#3498db')
        ax.set_ylabel(_("Taille (GB)"))
        ax.set_title(_("Évolution de l'utilisation du stockage"))
        plt.xticks(rotation=45)
        fig.tight_layout()

        canvas = FigureCanvas(fig)
        self.trend_box.pack_start(canvas, True, True, 0)
        self.trend_box.show_all()


    def on_theme_changed(self, combo):
        theme_id = combo.get_active_id()
        self.config_manager.update_ui_preferences(theme=theme_id)
        # Idéalement, informer le ThemeManager ici

    def on_analysis_setting_changed(self, switch, state, key):
        self.config_manager.update_analysis_preferences(**{key: state})
        return False

    def on_init_default_schedules(self, widget):
        self.scheduled_cleaner.create_default_schedules()
        self.show_info_dialog(_("Planification"), _("Les tâches de nettoyage automatique ont été configurées (systemd/cron)."))

    def on_clear_history_clicked(self, widget):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Vider l'historique"),
        )
        dialog.format_secondary_text(_("Êtes-vous sûr de vouloir supprimer tout l'historique des analyses et nettoyages ?"))
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            # Pour l'instant on réinitialise juste le fichier si on veut faire simple,
            # ou on ajoute une méthode au manager.
            # On va simuler en supprimant les données si le manager le permet (je devrais l'ajouter).
            try:
                os.remove(self.history_manager.db_path)
                self.history_manager._init_db()
                self._update_history_views()
                self.show_info_dialog(_("Historique"), _("L'historique a été vidé."))
            except Exception as e:
                self.show_info_dialog(_("Erreur"), str(e))
        dialog.destroy()

    def _setup_tooltips(self):
        """Configure les tooltips pour l'interface"""
        # Les tooltips seront configurés automatiquement par le TooltipManager
        # basé sur les noms des widgets et les clés prédéfinies
        pass

    # Callbacks existants (réutilisés de l'interface originale)
    def on_select_folder_clicked(self, widget):
        """Callback pour sélectionner un dossier"""
        dialog = Gtk.FileChooserDialog(
            title=_("Choisir un dossier à analyser"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                          Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            self.start_analysis(folder)
        dialog.destroy()

    def on_stop_analysis_clicked(self, widget):
        self.abort_event.set()
        self.stop_btn.set_sensitive(False)

    def start_analysis(self, folder):
        """Démarre l'analyse d'un dossier"""
        self.analyzer_liststore.clear()
        self.analyzer_spinner.start()
        self.stop_btn.set_sensitive(True)
        self.abort_event.clear()

        thread = threading.Thread(target=self.run_analysis_thread, args=(folder,))
        thread.daemon = True
        thread.start()

    def run_analysis_thread(self, folder):
        """Thread d'analyse"""
        results = analyze_directory(folder)
        GLib.idle_add(self.on_analysis_finished, results, folder)

    def on_analysis_finished(self, results, folder):
        """Callback fin d'analyse"""
        total_size = 0
        categorized_data = {"directory": 0, "file": 0}

        for item in results:
            file_type_key = "directory" if item.is_dir else "file"
            file_type_display = _("Dossier") if item.is_dir else _("Fichier")

            total_size += item.size
            categorized_data[file_type_key] = categorized_data.get(file_type_key, 0) + item.size

            size_display = self.format_size(item.size)
            
            # Ajouter le chemin complet comme 5ème colonne
            self.analyzer_liststore.append([
                os.path.basename(item.path),
                size_display,
                item.is_dir,
                file_type_display,
                item.path  # Chemin complet pour le menu contextuel
            ])

        # Enregistrer dans l'historique
        self.history_manager.record_scan(folder, total_size, categorized_data)
        
        # Sauvegarder les résultats pour l'export
        self.last_analysis_results = results

        self.analyzer_spinner.stop()
        self.export_btn.set_sensitive(True)

    def format_size(self, size):
        """Formate une taille en octets"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    # Callbacks de nettoyage (réutilisés)
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

    # Nouveaux callbacks pour les actions rapides
    def _on_quick_analyze_home(self, widget):
        """Analyse rapide du dossier home"""
        home_dir = os.path.expanduser("~")
        self.sidebar.set_active_section("analyzer")
        self.stack.set_visible_child_name("analyzer")
        self.start_analysis(home_dir)

    def _on_quick_clean(self, widget):
        """Nettoyage rapide"""
        self.sidebar.set_active_section("cleaner")
        self.stack.set_visible_child_name("cleaner")

    def _on_refresh_dashboard(self, widget):
        """Actualise le dashboard"""
        # Recréer la page dashboard avec les nouvelles données
        self.stack.remove(self.stack.get_child_by_name("dashboard"))
        self.pages["dashboard"] = DashboardPage(self)
        self.stack.add_named(self.pages["dashboard"], "dashboard")
        self.stack.show_all()
        self.stack.set_visible_child_name("dashboard")

    # Méthodes de nettoyage réutilisées
    def run_clean_task(self, name, func):
        """Lance une tâche de nettoyage non privilégiée dans un thread."""
        def task():
            try:
                result = func()
                msg = _("Opération terminée.")
                if isinstance(result, (int, float)):
                    msg += f" {self.format_size(result)} " + _("libérés.")
                    self.history_manager.record_cleaning(name, int(result))
                GLib.idle_add(self.show_info_dialog, name, msg)
            except Exception as e:
                GLib.idle_add(self.show_info_dialog, name, _("Erreur: ") + str(e))

        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    def run_privileged_task(self, name, action):
        """Lance une tâche privilégiée via pkexec."""
        def task():
            helper_path = "/usr/libexec/debian-storage-analyzer-helper"
            if not os.path.exists(helper_path):
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                helper_path = os.path.join(project_root, 'src', 'helpers', 'helper.py')

            try:
                cmd = ["pkexec", helper_path, action]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                # Essayer d'extraire l'espace libéré du texte (format: "Espace libéré : X.XX MB")
                # On gère plusieurs langues pour "Espace libéré" si nécessaire, mais ici on reste robuste
                freed_space = 0
                import re
                # Cherche un nombre suivi d'une unité (MB, KB, B, GB)
                match = re.search(r'(\d+\.?\d*)\s*(MB|KB|B|GB)', result.stdout)
                if match:
                    try:
                        value = float(match.group(1))
                        unit = match.group(2)
                        multipliers = {"B": 1, "KB": 1024, "MB": 1024*1024, "GB": 1024*1024*1024}
                        freed_space = int(value * multipliers.get(unit, 1))
                    except:
                        pass

                if freed_space > 0:
                    self.history_manager.record_cleaning(name, freed_space)

                GLib.idle_add(self.show_info_dialog, name, result.stdout)
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.show_info_dialog, name, 
                            _("Échec de l'authentification ou erreur système.") + f"\n{e.stderr}")
            except Exception as e:
                GLib.idle_add(self.show_info_dialog, name, _("Erreur: ") + str(e))

        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    def on_export_clicked(self, widget):
        """Gère l'exportation des résultats"""
        if not self.last_analysis_results:
            return

        dialog = Gtk.FileChooserDialog(
            title=_("Exporter les résultats"),
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        # Filtres
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)

        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF files")
        filter_pdf.add_pattern("*.pdf")
        dialog.add_filter(filter_pdf)

        dialog.set_do_overwrite_confirmation(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            success = False
            if filepath.endswith('.csv'):
                success = ReportGenerator.export_to_csv(self.last_analysis_results, filepath)
            elif filepath.endswith('.pdf'):
                success = ReportGenerator.export_to_pdf(self.last_analysis_results, filepath)
            else:
                # Par défaut CSV si pas d'extension reconnue
                filepath += ".csv"
                success = ReportGenerator.export_to_csv(self.last_analysis_results, filepath)

            if success:
                self.show_info_dialog(_("Export réussi"), _("Le rapport a été enregistré sous : ") + filepath)
            else:
                self.show_info_dialog(_("Erreur d'export"), _("Une erreur est survenue lors de l'export."))

        dialog.destroy()

    def show_info_dialog(self, title, message):
        """Affiche un dialogue d'information"""
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


class ModernApplication(Gtk.Application):
    """Application modernisée"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="fr.jules.debianstorageanalyzer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = ModernMainWindow(application=self)
        self.window.present()


if __name__ == "__main__":
    app = ModernApplication()
    sys.exit(app.run(sys.argv))