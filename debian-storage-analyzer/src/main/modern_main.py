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
from analyzer.package_analyzer import PackageAnalyzer
from analyzer.duplicate_detector import DuplicateDetector
from cleaner import system_cleaner, app_cleaner
from helpers.history_db import HistoryManager
from helpers.report_generator import ReportGenerator
from config.configuration_manager import ConfigurationManager
from cleaner.scheduled_cleaner import ScheduledCleaner, CleaningSchedule
from ui.modern_sidebar import ModernSidebar
from ui.theme_manager import ThemeManager
from ui.tooltip_manager import TooltipManager

class ModernMainWindow(Gtk.ApplicationWindow):
    """Interface principale modernisée avec sidebar et thèmes adaptatifs"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title(_("Analyseur de Stockage Debian 2.0"))
        self.set_default_size(1000, 750)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Charger le CSS
        self._load_css()

        # Initialiser les gestionnaires
        self.theme_manager = ThemeManager(self)
        self.tooltip_manager = TooltipManager()
        self.sidebar = ModernSidebar()
        self.history_manager = HistoryManager()
        self.config_manager = ConfigurationManager()
        self.scheduled_cleaner = ScheduledCleaner()
        self.package_analyzer = PackageAnalyzer()
        self.duplicate_detector = DuplicateDetector()
        self.last_analysis_results = []
        self.abort_event = threading.Event()
        
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
        
        # Initialiser les pages
        self._init_dashboard()
        self._init_analyzer()
        self._init_duplicates()
        self._init_packages()
        self._init_cleaner()
        self._init_history()
        self._init_settings()

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

    def _init_dashboard(self):
        """Initialise le tableau de bord modernisé"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)
        page.get_style_context().add_class("dashboard-page")

        # Header avec titre et description
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title = Gtk.Label(label=_("Tableau de Bord"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_hbox.pack_start(title, False, False, 0)

        version_tag = Gtk.Label(label="v2.0.0")
        version_tag.get_style_context().add_class("version-tag")
        header_hbox.pack_start(version_tag, False, False, 0)

        header_box.pack_start(header_hbox, False, False, 0)
        
        subtitle = Gtk.Label(label=_("Vue d'ensemble de l'utilisation du stockage système"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        
        page.pack_start(header_box, False, False, 0)

        # Container pour les statistiques et graphique
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        
        # Panneau de statistiques
        stats_frame = Gtk.Frame()
        stats_frame.get_style_context().add_class("stat-card")
        stats_frame.set_label(_("Statistiques Système"))
        stats_frame.set_size_request(320, -1)
        
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
        chart_frame.get_style_context().add_class("stat-card")
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

    def _init_packages(self):
        """Initialise la page d'analyse des paquets"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)

        title = Gtk.Label(label=_("Analyse des Paquets"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        refresh_btn = Gtk.Button(label=_("Actualiser la liste"))
        refresh_btn.get_style_context().add_class("suggested-action")
        refresh_btn.connect("clicked", self.on_refresh_packages_clicked)
        toolbar.pack_start(refresh_btn, False, False, 0)

        self.package_spinner = Gtk.Spinner()
        toolbar.pack_start(self.package_spinner, False, False, 0)
        page.pack_start(toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.package_liststore = Gtk.ListStore(str, str, str, str) # Nom, Version, Taille, Type
        self.package_treeview = Gtk.TreeView(model=self.package_liststore)

        for i, col_title in enumerate([_("Nom"), _("Version"), _("Taille"), _("Type")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            self.package_treeview.append_column(column)

        scrolled.add(self.package_treeview)
        page.pack_start(scrolled, True, True, 0)

        self.stack.add_named(page, "packages")

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

    def _init_duplicates(self):
        """Initialise la page de recherche de doublons"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)

        title = Gtk.Label(label=_("Recherche de Doublons"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        select_btn = Gtk.Button(label=_("Scanner un dossier"))
        select_btn.get_style_context().add_class("suggested-action")
        select_btn.connect("clicked", self.on_select_duplicate_folder_clicked)
        toolbar.pack_start(select_btn, False, False, 0)

        self.duplicate_spinner = Gtk.Spinner()
        toolbar.pack_start(self.duplicate_spinner, False, False, 0)
        page.pack_start(toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.duplicate_liststore = Gtk.ListStore(str, str, str) # Hash, Taille, Chemins (concat)
        self.duplicate_treeview = Gtk.TreeView(model=self.duplicate_liststore)

        for i, col_title in enumerate([_("Hash (ID)"), _("Taille"), _("Fichiers")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_sort_column_id(i)
            self.duplicate_treeview.append_column(column)

        scrolled.add(self.duplicate_treeview)
        page.pack_start(scrolled, True, True, 0)

        self.stack.add_named(page, "duplicates")

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
                hash_val[:12],
                self.format_size(group.file_size),
                ", ".join([os.path.basename(p) for p in group.file_paths])
            ])
        self.duplicate_spinner.stop()

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
        
        self.stop_btn = Gtk.Button.new_from_icon_name("process-stop", Gtk.IconSize.BUTTON)
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self.on_stop_analysis_clicked)
        toolbar.pack_start(self.stop_btn, False, False, 0)

        # Spacer
        spacer = Gtk.Box()
        toolbar.pack_start(spacer, True, True, 0)
        
        # Boutons d'action
        self.export_btn = Gtk.Button(label=_("Exporter"))
        self.export_btn.set_sensitive(False)  # Activé après analyse
        self.export_btn.connect("clicked", self.on_export_clicked)
        toolbar.pack_start(self.export_btn, False, False, 0)
        
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
        """Initialise la page d'historique"""
        self.history_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.history_page.set_border_width(30)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Label(label=_("Historique des Opérations"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label=_("Suivez l'évolution de votre stockage et vos actions de nettoyage"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        self.history_page.pack_start(header_box, False, False, 0)

        # Notebook pour séparer scans et nettoyages
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Tab 1: Analyses
        scan_box = self._create_scan_history_view()
        notebook.append_page(scan_box, Gtk.Label(label=_("Analyses")))

        # Tab 2: Nettoyages
        clean_box = self._create_cleaning_history_view()
        notebook.append_page(clean_box, Gtk.Label(label=_("Nettoyages")))

        # Tab 3: Tendances
        trend_box = self._create_trend_view()
        notebook.append_page(trend_box, Gtk.Label(label=_("Tendances")))

        self.history_page.pack_start(notebook, True, True, 0)

        # Barre d'outils historique
        history_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Bouton Actualiser
        refresh_btn = Gtk.Button(label=_("Actualiser"))
        refresh_btn.get_style_context().add_class("suggested-action")
        refresh_btn.connect("clicked", lambda w: self._update_history_views())
        history_toolbar.pack_start(refresh_btn, False, False, 0)

        # Bouton Vider
        clear_history_btn = Gtk.Button(label=_("Vider l'historique"))
        clear_history_btn.get_style_context().add_class("destructive-action")
        clear_history_btn.connect("clicked", self.on_clear_history_clicked)
        history_toolbar.pack_start(clear_history_btn, False, False, 0)

        self.history_page.pack_start(history_toolbar, False, False, 0)

        self.stack.add_named(self.history_page, "history")

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

    def _init_settings(self):
        """Initialise la page de paramètres"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(30)
        
        title = Gtk.Label(label=_("Paramètres"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        # Thème
        theme_frame = Gtk.Frame(label=_("Apparence"))
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        theme_box.set_border_width(10)
        theme_box.pack_start(Gtk.Label(label=_("Thème")), False, False, 0)

        theme_combo = Gtk.ComboBoxText()
        theme_combo.append("auto", _("Automatique"))
        theme_combo.append("light", _("Clair"))
        theme_combo.append("dark", _("Sombre"))

        current_config = self.config_manager.get_configuration()
        theme_combo.set_active_id(current_config.ui.theme)
        theme_combo.connect("changed", self.on_theme_changed)

        theme_box.pack_end(theme_combo, False, False, 0)
        theme_frame.add(theme_box)
        settings_box.pack_start(theme_frame, False, False, 0)

        # Analyse
        analysis_frame = Gtk.Frame(label=_("Analyse"))
        analysis_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        analysis_box.set_border_width(10)

        hidden_switch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hidden_switch.pack_start(Gtk.Label(label=_("Inclure les fichiers cachés")), False, False, 0)
        self.hidden_sw = Gtk.Switch()
        self.hidden_sw.set_active(current_config.analysis.include_hidden_files)
        self.hidden_sw.connect("state-set", self.on_analysis_setting_changed, "include_hidden_files")
        hidden_switch.pack_end(self.hidden_sw, False, False, 0)
        analysis_box.pack_start(hidden_switch, False, False, 0)

        analysis_frame.add(analysis_box)
        settings_box.pack_start(analysis_frame, False, False, 0)

        # Planification
        planning_frame = Gtk.Frame(label=_("Nettoyage Automatique"))
        planning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        planning_box.set_border_width(10)

        planning_box.pack_start(Gtk.Label(label=_("Activer les tâches systemd/cron par défaut")), False, False, 0)

        default_plan_btn = Gtk.Button(label=_("Initialiser les planifications par défaut"))
        default_plan_btn.connect("clicked", self.on_init_default_schedules)
        planning_box.pack_start(default_plan_btn, False, False, 0)

        planning_frame.add(planning_box)
        settings_box.pack_start(planning_frame, False, False, 0)

        scrolled.add(settings_box)
        page.pack_start(scrolled, True, True, 0)
        
        self.stack.add_named(page, "settings")

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
        try:
            results = analyze_directory(folder, self.abort_event)
            GLib.idle_add(self.on_analysis_finished, results, folder)
        except Exception as e:
            GLib.idle_add(self.show_info_dialog, _("Erreur d'analyse"), str(e))
            GLib.idle_add(self.analyzer_spinner.stop)
            GLib.idle_add(self.stop_btn.set_sensitive, False)

    def on_analysis_finished(self, results, folder):
        """Callback fin d'analyse"""
        self.stop_btn.set_sensitive(False)
        if self.abort_event.is_set():
            self.show_info_dialog(_("Analyse annulée"), _("L'analyse a été interrompue par l'utilisateur."))
            self.analyzer_spinner.stop()
            return

        total_size = 0
        categorized_data = {"directory": 0, "file": 0}
        self.last_analysis_results = []

        for item in results:
            file_type_key = "directory" if item.is_dir else "file"
            file_type_display = _("Dossier") if item.is_dir else _("Fichier")

            size_fmt = self.format_size(item.size)
            total_size += item.size
            categorized_data[file_type_key] = categorized_data.get(file_type_key, 0) + item.size

            self.analyzer_liststore.append([
                os.path.basename(item.path),
                size_fmt,
                item.is_dir,
                file_type_display
            ])
            self.last_analysis_results.append((os.path.basename(item.path), size_fmt, file_type_display))

        # Enregistrer dans l'historique
        self.history_manager.record_scan(folder, total_size, categorized_data)

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