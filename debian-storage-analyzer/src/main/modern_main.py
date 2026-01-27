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
from ui.modern_sidebar import ModernSidebar
from ui.theme_manager import ThemeManager
from ui.tooltip_manager import TooltipManager

class ModernMainWindow(Gtk.ApplicationWindow):
    """Interface principale modernisée avec sidebar et thèmes adaptatifs"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title(_("Analyseur de Stockage Debian - Modern"))
        self.set_default_size(1000, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Initialiser les gestionnaires
        self.theme_manager = ThemeManager(self)
        self.tooltip_manager = TooltipManager()
        self.sidebar = ModernSidebar()
        
        # Créer l'interface
        self._setup_ui()
        
        # Configurer les tooltips
        self._setup_tooltips()
        
        self.show_all()
        
        # Activer la première section
        self.sidebar.set_active_section("dashboard")

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
        
        # Initialiser les pages
        self._init_dashboard()
        self._init_analyzer()
        self._init_cleaner()
        self._init_history()
        self._init_settings()

    def _init_dashboard(self):
        """Initialise le tableau de bord modernisé"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)

        # Header avec titre et description
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        title = Gtk.Label(label=_("Tableau de Bord"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)
        
        subtitle = Gtk.Label(label=_("Vue d'ensemble de l'utilisation du stockage système"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        
        page.pack_start(header_box, False, False, 0)

        # Container pour les statistiques et graphique
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        
        # Panneau de statistiques
        stats_frame = Gtk.Frame()
        stats_frame.set_label(_("Statistiques Système"))
        stats_frame.set_size_request(300, -1)
        
        stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        stats_box.set_border_width(20)
        
        # Statistiques disque
        usage = psutil.disk_usage('/')
        
        # Espace total
        total_box = self._create_stat_row(_("Espace Total"), self.format_size(usage.total))
        stats_box.pack_start(total_box, False, False, 0)
        
        # Espace utilisé
        used_box = self._create_stat_row(_("Espace Utilisé"), 
                                       f"{self.format_size(usage.used)} ({usage.percent:.1f}%)")
        stats_box.pack_start(used_box, False, False, 0)
        
        # Espace libre
        free_box = self._create_stat_row(_("Espace Libre"), self.format_size(usage.free))
        stats_box.pack_start(free_box, False, False, 0)
        
        # Barre de progression
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        progress_label = Gtk.Label(label=_("Utilisation"))
        progress_label.set_halign(Gtk.Align.START)
        progress_box.pack_start(progress_label, False, False, 0)
        
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_fraction(usage.percent / 100.0)
        progress_bar.set_show_text(True)
        progress_bar.set_text(f"{usage.percent:.1f}%")
        progress_bar.get_style_context().add_class("progress-modern")
        progress_box.pack_start(progress_bar, False, False, 0)
        
        stats_box.pack_start(progress_box, False, False, 0)
        
        stats_frame.add(stats_box)
        content_box.pack_start(stats_frame, False, False, 0)
        
        # Graphique en camembert modernisé
        chart_frame = Gtk.Frame()
        chart_frame.set_label(_("Répartition de l'Espace"))
        
        fig, ax = plt.subplots(figsize=(6, 5), dpi=100)
        fig.patch.set_facecolor('none')  # Fond transparent
        
        labels = [_('Utilisé'), _('Libre')]
        sizes = [usage.used, usage.free]
        colors = ['#e74c3c', '#2ecc71']  # Rouge pour utilisé, vert pour libre
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                         startangle=90, colors=colors,
                                         textprops={'fontsize': 11})
        
        # Améliorer l'apparence
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.axis('equal')
        
        canvas = FigureCanvas(fig)
        canvas.set_size_request(400, 350)
        chart_frame.add(canvas)
        
        content_box.pack_start(chart_frame, True, True, 0)
        
        page.pack_start(content_box, True, True, 0)
        
        # Actions rapides
        actions_frame = Gtk.Frame()
        actions_frame.set_label(_("Actions Rapides"))
        
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        actions_box.set_border_width(15)
        
        # Bouton analyse rapide
        analyze_btn = Gtk.Button(label=_("Analyser /home"))
        analyze_btn.get_style_context().add_class("suggested-action")
        analyze_btn.connect("clicked", self._on_quick_analyze_home)
        actions_box.pack_start(analyze_btn, False, False, 0)
        
        # Bouton nettoyage rapide
        clean_btn = Gtk.Button(label=_("Nettoyage Rapide"))
        clean_btn.connect("clicked", self._on_quick_clean)
        actions_box.pack_start(clean_btn, False, False, 0)
        
        # Bouton actualiser
        refresh_btn = Gtk.Button(label=_("Actualiser"))
        refresh_btn.connect("clicked", self._on_refresh_dashboard)
        actions_box.pack_start(refresh_btn, False, False, 0)
        
        actions_frame.add(actions_box)
        page.pack_start(actions_frame, False, False, 0)

        self.stack.add_named(page, "dashboard")
    
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

    def _init_analyzer(self):
        """Initialise la page d'analyse modernisée"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        title = Gtk.Label(label=_("Analyse de Stockage"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)
        
        subtitle = Gtk.Label(label=_("Analyser l'utilisation de l'espace disque par dossier"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        
        page.pack_start(header_box, False, False, 0)

        # Toolbar d'analyse
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        
        select_button = Gtk.Button(label=_("Choisir un Dossier"))
        select_button.get_style_context().add_class("suggested-action")
        select_button.connect("clicked", self.on_select_folder_clicked)
        toolbar.pack_start(select_button, False, False, 0)
        
        self.analyzer_spinner = Gtk.Spinner()
        toolbar.pack_start(self.analyzer_spinner, False, False, 0)
        
        # Spacer
        spacer = Gtk.Box()
        toolbar.pack_start(spacer, True, True, 0)
        
        # Boutons d'action
        export_btn = Gtk.Button(label=_("Exporter"))
        export_btn.set_sensitive(False)  # Activé après analyse
        toolbar.pack_start(export_btn, False, False, 0)
        
        page.pack_start(toolbar, False, False, 0)

        # Zone de résultats
        results_frame = Gtk.Frame()
        results_frame.set_label(_("Résultats d'Analyse"))
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 400)
        
        # TreeView amélioré (sera étendu dans la tâche 2)
        self.analyzer_liststore = Gtk.ListStore(str, str, bool, str)  # Nom, Taille, IsDir, Type
        self.analyzer_treeview = Gtk.TreeView(model=self.analyzer_liststore)
        self.analyzer_treeview.get_style_context().add_class("enhanced-treeview")

        # Colonnes
        renderer_text = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn(_("Nom"), renderer_text, text=0)
        column_name.set_sort_column_id(0)
        self.analyzer_treeview.append_column(column_name)

        renderer_size = Gtk.CellRendererText()
        column_size = Gtk.TreeViewColumn(_("Taille"), renderer_size, text=1)
        column_size.set_sort_column_id(1)
        self.analyzer_treeview.append_column(column_size)
        
        renderer_type = Gtk.CellRendererText()
        column_type = Gtk.TreeViewColumn(_("Type"), renderer_type, text=3)
        column_type.set_sort_column_id(3)
        self.analyzer_treeview.append_column(column_type)

        scrolled.add(self.analyzer_treeview)
        results_frame.add(scrolled)
        page.pack_start(results_frame, True, True, 0)

        self.stack.add_named(page, "analyzer")

    def _init_cleaner(self):
        """Initialise la page de nettoyage modernisée"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        title = Gtk.Label(label=_("Nettoyage Système"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)
        
        subtitle = Gtk.Label(label=_("Nettoyer les fichiers temporaires et caches système"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        
        page.pack_start(header_box, False, False, 0)

        # Options de nettoyage
        cleaners_frame = Gtk.Frame()
        cleaners_frame.set_label(_("Options de Nettoyage"))
        
        cleaners_list = Gtk.ListBox()
        cleaners_list.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # Utiliser la fonction existante mais avec un style modernisé
        self._add_modern_cleaner_row(cleaners_list, _("Cache APT"), 
                                   _("Supprime les paquets téléchargés (.deb)"), 
                                   self.on_clean_apt_clicked, "clean_apt")
        
        self._add_modern_cleaner_row(cleaners_list, _("Dépendances inutiles"), 
                                   _("Supprime les paquets orphelins (autoremove)"), 
                                   self.on_autoremove_clicked, "clean_autoremove")
        
        self._add_modern_cleaner_row(cleaners_list, _("Fichiers Temporaires"), 
                                   _("Nettoie /tmp et /var/tmp (> 7 jours)"), 
                                   self.on_clean_temp_clicked, "clean_temp")
        
        self._add_modern_cleaner_row(cleaners_list, _("Journaux Système"), 
                                   _("Réduit la taille des logs journald"), 
                                   self.on_clean_logs_clicked, "clean_logs")
        
        self._add_modern_cleaner_row(cleaners_list, _("Firefox Cache"), 
                                   _("Nettoie le cache de Firefox"), 
                                   self.on_clean_firefox_clicked, "clean_firefox")
        
        self._add_modern_cleaner_row(cleaners_list, _("Flatpak Cache"), 
                                   _("Nettoie le cache des applications Flatpak"), 
                                   self.on_clean_flatpak_clicked, "clean_flatpak")
        
        cleaners_frame.add(cleaners_list)
        page.pack_start(cleaners_frame, True, True, 0)

        self.stack.add_named(page, "cleaner")
    
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

    def _init_history(self):
        """Initialise la page d'historique (placeholder)"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)
        
        title = Gtk.Label(label=_("Historique"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)
        
        placeholder = Gtk.Label(label=_("L'historique sera implémenté dans les prochaines tâches"))
        placeholder.get_style_context().add_class("placeholder-text")
        page.pack_start(placeholder, True, True, 0)
        
        self.stack.add_named(page, "history")

    def _init_settings(self):
        """Initialise la page de paramètres (placeholder)"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)
        
        title = Gtk.Label(label=_("Paramètres"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)
        
        placeholder = Gtk.Label(label=_("Les paramètres seront implémentés dans les prochaines tâches"))
        placeholder.get_style_context().add_class("placeholder-text")
        page.pack_start(placeholder, True, True, 0)
        
        self.stack.add_named(page, "settings")

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

    def start_analysis(self, folder):
        """Démarre l'analyse d'un dossier"""
        self.analyzer_liststore.clear()
        self.analyzer_spinner.start()
        thread = threading.Thread(target=self.run_analysis_thread, args=(folder,))
        thread.daemon = True
        thread.start()

    def run_analysis_thread(self, folder):
        """Thread d'analyse"""
        results = analyze_directory(folder)
        GLib.idle_add(self.on_analysis_finished, results)

    def on_analysis_finished(self, results):
        """Callback fin d'analyse"""
        for item in results:
            file_type = "Dossier" if item.is_dir else "Fichier"
            self.analyzer_liststore.append([
                os.path.basename(item.path),
                self.format_size(item.size),
                item.is_dir,
                file_type
            ])
        self.analyzer_spinner.stop()

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
        self._init_dashboard()

    # Méthodes de nettoyage réutilisées
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
            helper_path = "/usr/libexec/debian-storage-analyzer-helper"
            if not os.path.exists(helper_path):
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                helper_path = os.path.join(project_root, 'src', 'helpers', 'helper.py')

            try:
                cmd = ["pkexec", helper_path, action]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                GLib.idle_add(self.show_info_dialog, name, result.stdout)
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self.show_info_dialog, name, 
                            _("Échec de l'authentification ou erreur système.") + f"\n{e.stderr}")
            except Exception as e:
                GLib.idle_add(self.show_info_dialog, name, _("Erreur: ") + str(e))

        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

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
        super().__init__(*args, application_id="fr.jules.debianstorageanalyzer.modern",
                         flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = ModernMainWindow(application=self)
        self.window.present()


if __name__ == "__main__":
    app = ModernApplication()
    sys.exit(app.run(sys.argv))