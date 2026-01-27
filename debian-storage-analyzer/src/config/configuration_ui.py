"""
Configuration UI for Debian Storage Analyzer.

Provides GTK-based interface for managing application preferences
and configuration settings.
"""

import logging
from typing import Dict, Any, Callable, Optional
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GObject, Gio
except ImportError:
    # Fallback for environments without GTK
    Gtk = None
    GObject = None
    Gio = None

from .configuration_manager import ConfigurationManager, Configuration


class ConfigurationUI:
    """
    GTK-based configuration interface.
    
    Provides user-friendly interface for managing all application settings
    including UI preferences, analysis options, cleaning settings, and more.
    """
    
    def __init__(self, config_manager: ConfigurationManager, parent_window: Optional['Gtk.Window'] = None):
        """Initialize configuration UI."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.parent_window = parent_window
        
        # UI components
        self.dialog: Optional['Gtk.Dialog'] = None
        self.notebook: Optional['Gtk.Notebook'] = None
        
        # Settings widgets
        self.ui_widgets: Dict[str, 'Gtk.Widget'] = {}
        self.analysis_widgets: Dict[str, 'Gtk.Widget'] = {}
        self.cleaning_widgets: Dict[str, 'Gtk.Widget'] = {}
        self.monitoring_widgets: Dict[str, 'Gtk.Widget'] = {}
        self.reporting_widgets: Dict[str, 'Gtk.Widget'] = {}
        
        # Change tracking
        self.has_changes = False
        self.change_callbacks: Dict[str, Callable] = {}
        
        if Gtk is None:
            self.logger.warning("GTK not available, configuration UI disabled")
    
    def show_configuration_dialog(self) -> bool:
        """Show configuration dialog and return True if settings were saved."""
        if Gtk is None:
            self.logger.error("GTK not available")
            return False
        
        try:
            self._create_dialog()
            self._populate_settings()
            
            response = self.dialog.run()
            
            if response == Gtk.ResponseType.OK:
                return self._save_settings()
            elif response == Gtk.ResponseType.APPLY:
                self._save_settings()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error showing configuration dialog: {e}")
            return False
        finally:
            if self.dialog:
                self.dialog.destroy()
    
    def _create_dialog(self):
        """Create the configuration dialog."""
        self.dialog = Gtk.Dialog(
            title="Préférences - Debian Storage Analyzer",
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        
        # Set dialog size
        self.dialog.set_default_size(600, 500)
        self.dialog.set_resizable(True)
        
        # Add buttons
        self.dialog.add_button("Annuler", Gtk.ResponseType.CANCEL)
        self.dialog.add_button("Appliquer", Gtk.ResponseType.APPLY)
        self.dialog.add_button("OK", Gtk.ResponseType.OK)
        
        # Create notebook for tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)
        
        # Add tabs
        self._create_ui_tab()
        self._create_analysis_tab()
        self._create_cleaning_tab()
        self._create_monitoring_tab()
        self._create_reporting_tab()
        self._create_backup_tab()
        
        # Add notebook to dialog
        content_area = self.dialog.get_content_area()
        content_area.pack_start(self.notebook, True, True, 0)
        
        self.dialog.show_all()
    
    def _create_ui_tab(self):
        """Create UI preferences tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Theme selection
        theme_frame = self._create_frame("Apparence")
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        theme_label = Gtk.Label("Thème:")
        theme_label.set_halign(Gtk.Align.START)
        theme_combo = Gtk.ComboBoxText()
        theme_combo.append("auto", "Automatique")
        theme_combo.append("light", "Clair")
        theme_combo.append("dark", "Sombre")
        self.ui_widgets['theme'] = theme_combo
        
        theme_box.pack_start(theme_label, False, False, 0)
        theme_box.pack_start(theme_combo, False, False, 0)
        theme_frame.add(theme_box)
        
        # Window settings
        window_frame = self._create_frame("Fenêtre")
        window_grid = Gtk.Grid()
        window_grid.set_column_spacing(12)
        window_grid.set_row_spacing(6)
        
        # Sidebar width
        sidebar_label = Gtk.Label("Largeur de la barre latérale:")
        sidebar_label.set_halign(Gtk.Align.START)
        sidebar_spin = Gtk.SpinButton.new_with_range(100, 500, 10)
        self.ui_widgets['sidebar_width'] = sidebar_spin
        
        window_grid.attach(sidebar_label, 0, 0, 1, 1)
        window_grid.attach(sidebar_spin, 1, 0, 1, 1)
        
        # Window size
        width_label = Gtk.Label("Largeur de la fenêtre:")
        width_label.set_halign(Gtk.Align.START)
        width_spin = Gtk.SpinButton.new_with_range(800, 2000, 50)
        self.ui_widgets['window_width'] = width_spin
        
        height_label = Gtk.Label("Hauteur de la fenêtre:")
        height_label.set_halign(Gtk.Align.START)
        height_spin = Gtk.SpinButton.new_with_range(600, 1500, 50)
        self.ui_widgets['window_height'] = height_spin
        
        window_grid.attach(width_label, 0, 1, 1, 1)
        window_grid.attach(width_spin, 1, 1, 1, 1)
        window_grid.attach(height_label, 0, 2, 1, 1)
        window_grid.attach(height_spin, 1, 2, 1, 1)
        
        window_frame.add(window_grid)
        
        # Interface options
        options_frame = self._create_frame("Options")
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        tooltips_check = Gtk.CheckButton("Afficher les info-bulles")
        animation_check = Gtk.CheckButton("Activer les animations")
        
        self.ui_widgets['show_tooltips'] = tooltips_check
        self.ui_widgets['animation_enabled'] = animation_check
        
        options_box.pack_start(tooltips_check, False, False, 0)
        options_box.pack_start(animation_check, False, False, 0)
        options_frame.add(options_box)
        
        page.pack_start(theme_frame, False, False, 0)
        page.pack_start(window_frame, False, False, 0)
        page.pack_start(options_frame, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label("Interface"))
    
    def _create_analysis_tab(self):
        """Create analysis preferences tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Default directories
        dirs_frame = self._create_frame("Dossiers par défaut")
        dirs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        # Directory list
        dirs_scrolled = Gtk.ScrolledWindow()
        dirs_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        dirs_scrolled.set_size_request(-1, 150)
        
        dirs_listbox = Gtk.ListBox()
        self.ui_widgets['default_directories'] = dirs_listbox
        dirs_scrolled.add(dirs_listbox)
        
        # Directory buttons
        dirs_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_dir_button = Gtk.Button("Ajouter")
        remove_dir_button = Gtk.Button("Supprimer")
        
        dirs_button_box.pack_start(add_dir_button, False, False, 0)
        dirs_button_box.pack_start(remove_dir_button, False, False, 0)
        
        dirs_box.pack_start(dirs_scrolled, True, True, 0)
        dirs_box.pack_start(dirs_button_box, False, False, 0)
        dirs_frame.add(dirs_box)
        
        # Analysis options
        options_frame = self._create_frame("Options d'analyse")
        options_grid = Gtk.Grid()
        options_grid.set_column_spacing(12)
        options_grid.set_row_spacing(6)
        
        # Hidden files
        hidden_check = Gtk.CheckButton("Inclure les fichiers cachés")
        self.ui_widgets['include_hidden_files'] = hidden_check
        options_grid.attach(hidden_check, 0, 0, 2, 1)
        
        # Follow symlinks
        symlinks_check = Gtk.CheckButton("Suivre les liens symboliques")
        self.ui_widgets['follow_symlinks'] = symlinks_check
        options_grid.attach(symlinks_check, 0, 1, 2, 1)
        
        # Max depth
        depth_label = Gtk.Label("Profondeur maximale:")
        depth_label.set_halign(Gtk.Align.START)
        depth_spin = Gtk.SpinButton.new_with_range(-1, 20, 1)
        self.ui_widgets['max_depth'] = depth_spin
        
        options_grid.attach(depth_label, 0, 2, 1, 1)
        options_grid.attach(depth_spin, 1, 2, 1, 1)
        
        # File size threshold
        size_label = Gtk.Label("Seuil de taille (octets):")
        size_label.set_halign(Gtk.Align.START)
        size_spin = Gtk.SpinButton.new_with_range(0, 1000000, 1024)
        self.ui_widgets['file_size_threshold'] = size_spin
        
        options_grid.attach(size_label, 0, 3, 1, 1)
        options_grid.attach(size_spin, 1, 3, 1, 1)
        
        options_frame.add(options_grid)
        
        # Duplicate detection
        duplicates_frame = self._create_frame("Détection de doublons")
        duplicates_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        duplicates_check = Gtk.CheckButton("Activer la détection de doublons")
        self.ui_widgets['enable_duplicate_detection'] = duplicates_check
        
        hash_label = Gtk.Label("Algorithme de hachage:")
        hash_label.set_halign(Gtk.Align.START)
        hash_combo = Gtk.ComboBoxText()
        hash_combo.append("md5", "MD5")
        hash_combo.append("sha1", "SHA1")
        hash_combo.append("sha256", "SHA256")
        self.ui_widgets['hash_algorithm'] = hash_combo
        
        duplicates_box.pack_start(duplicates_check, False, False, 0)
        duplicates_box.pack_start(hash_label, False, False, 0)
        duplicates_box.pack_start(hash_combo, False, False, 0)
        duplicates_frame.add(duplicates_box)
        
        page.pack_start(dirs_frame, True, True, 0)
        page.pack_start(options_frame, False, False, 0)
        page.pack_start(duplicates_frame, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label("Analyse"))
    
    def _create_cleaning_tab(self):
        """Create cleaning preferences tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Safety options
        safety_frame = self._create_frame("Sécurité")
        safety_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        dry_run_check = Gtk.CheckButton("Mode simulation par défaut")
        confirm_check = Gtk.CheckButton("Confirmer avant suppression")
        backup_check = Gtk.CheckButton("Sauvegarder avant nettoyage")
        
        self.ui_widgets['dry_run_by_default'] = dry_run_check
        self.ui_widgets['confirm_before_delete'] = confirm_check
        self.ui_widgets['backup_before_clean'] = backup_check
        
        safety_box.pack_start(dry_run_check, False, False, 0)
        safety_box.pack_start(confirm_check, False, False, 0)
        safety_box.pack_start(backup_check, False, False, 0)
        safety_frame.add(safety_box)
        
        # Backup settings
        backup_frame = self._create_frame("Sauvegardes")
        backup_grid = Gtk.Grid()
        backup_grid.set_column_spacing(12)
        backup_grid.set_row_spacing(6)
        
        retention_label = Gtk.Label("Durée de rétention (jours):")
        retention_label.set_halign(Gtk.Align.START)
        retention_spin = Gtk.SpinButton.new_with_range(1, 365, 1)
        self.ui_widgets['backup_retention_days'] = retention_spin
        
        backup_grid.attach(retention_label, 0, 0, 1, 1)
        backup_grid.attach(retention_spin, 1, 0, 1, 1)
        backup_frame.add(backup_grid)
        
        # Application-specific cleaning
        apps_frame = self._create_frame("Nettoyage par application")
        apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        firefox_check = Gtk.CheckButton("Firefox")
        chrome_check = Gtk.CheckButton("Chrome/Chromium")
        flatpak_check = Gtk.CheckButton("Flatpak")
        snap_check = Gtk.CheckButton("Snap")
        
        self.ui_widgets['app_firefox'] = firefox_check
        self.ui_widgets['app_chrome'] = chrome_check
        self.ui_widgets['app_flatpak'] = flatpak_check
        self.ui_widgets['app_snap'] = snap_check
        
        apps_box.pack_start(firefox_check, False, False, 0)
        apps_box.pack_start(chrome_check, False, False, 0)
        apps_box.pack_start(flatpak_check, False, False, 0)
        apps_box.pack_start(snap_check, False, False, 0)
        apps_frame.add(apps_box)
        
        page.pack_start(safety_frame, False, False, 0)
        page.pack_start(backup_frame, False, False, 0)
        page.pack_start(apps_frame, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label("Nettoyage"))
    
    def _create_monitoring_tab(self):
        """Create monitoring preferences tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Real-time monitoring
        realtime_frame = self._create_frame("Surveillance temps réel")
        realtime_grid = Gtk.Grid()
        realtime_grid.set_column_spacing(12)
        realtime_grid.set_row_spacing(6)
        
        enable_check = Gtk.CheckButton("Activer la surveillance")
        self.ui_widgets['enable_realtime'] = enable_check
        realtime_grid.attach(enable_check, 0, 0, 2, 1)
        
        interval_label = Gtk.Label("Intervalle de mise à jour (secondes):")
        interval_label.set_halign(Gtk.Align.START)
        interval_spin = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.ui_widgets['update_interval'] = interval_spin
        
        realtime_grid.attach(interval_label, 0, 1, 1, 1)
        realtime_grid.attach(interval_spin, 1, 1, 1, 1)
        realtime_frame.add(realtime_grid)
        
        # Notifications
        notif_frame = self._create_frame("Notifications")
        notif_grid = Gtk.Grid()
        notif_grid.set_column_spacing(12)
        notif_grid.set_row_spacing(6)
        
        notif_check = Gtk.CheckButton("Activer les notifications")
        self.ui_widgets['enable_notifications'] = notif_check
        notif_grid.attach(notif_check, 0, 0, 2, 1)
        
        cooldown_label = Gtk.Label("Délai entre notifications (secondes):")
        cooldown_label.set_halign(Gtk.Align.START)
        cooldown_spin = Gtk.SpinButton.new_with_range(60, 3600, 60)
        self.ui_widgets['notification_cooldown'] = cooldown_spin
        
        notif_grid.attach(cooldown_label, 0, 1, 1, 1)
        notif_grid.attach(cooldown_spin, 1, 1, 1, 1)
        notif_frame.add(notif_grid)
        
        # Thresholds
        thresholds_frame = self._create_frame("Seuils d'alerte (%)")
        thresholds_grid = Gtk.Grid()
        thresholds_grid.set_column_spacing(12)
        thresholds_grid.set_row_spacing(6)
        
        disk_label = Gtk.Label("Utilisation disque:")
        disk_label.set_halign(Gtk.Align.START)
        disk_spin = Gtk.SpinButton.new_with_range(50, 99, 1)
        self.ui_widgets['disk_usage_threshold'] = disk_spin
        
        cpu_label = Gtk.Label("Utilisation CPU:")
        cpu_label.set_halign(Gtk.Align.START)
        cpu_spin = Gtk.SpinButton.new_with_range(50, 99, 1)
        self.ui_widgets['cpu_usage_threshold'] = cpu_spin
        
        memory_label = Gtk.Label("Utilisation mémoire:")
        memory_label.set_halign(Gtk.Align.START)
        memory_spin = Gtk.SpinButton.new_with_range(50, 99, 1)
        self.ui_widgets['memory_usage_threshold'] = memory_spin
        
        thresholds_grid.attach(disk_label, 0, 0, 1, 1)
        thresholds_grid.attach(disk_spin, 1, 0, 1, 1)
        thresholds_grid.attach(cpu_label, 0, 1, 1, 1)
        thresholds_grid.attach(cpu_spin, 1, 1, 1, 1)
        thresholds_grid.attach(memory_label, 0, 2, 1, 1)
        thresholds_grid.attach(memory_spin, 1, 2, 1, 1)
        
        thresholds_frame.add(thresholds_grid)
        
        page.pack_start(realtime_frame, False, False, 0)
        page.pack_start(notif_frame, False, False, 0)
        page.pack_start(thresholds_frame, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label("Surveillance"))
    
    def _create_reporting_tab(self):
        """Create reporting preferences tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Export format
        format_frame = self._create_frame("Format d'export")
        format_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        format_label = Gtk.Label("Format par défaut:")
        format_label.set_halign(Gtk.Align.START)
        format_combo = Gtk.ComboBoxText()
        format_combo.append("pdf", "PDF")
        format_combo.append("csv", "CSV")
        format_combo.append("html", "HTML")
        self.ui_widgets['default_format'] = format_combo
        
        format_box.pack_start(format_label, False, False, 0)
        format_box.pack_start(format_combo, False, False, 0)
        format_frame.add(format_box)
        
        # Chart options
        charts_frame = self._create_frame("Graphiques")
        charts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        charts_check = Gtk.CheckButton("Inclure les graphiques")
        self.ui_widgets['include_charts'] = charts_check
        
        style_label = Gtk.Label("Style des graphiques:")
        style_label.set_halign(Gtk.Align.START)
        style_combo = Gtk.ComboBoxText()
        style_combo.append("modern", "Moderne")
        style_combo.append("classic", "Classique")
        style_combo.append("minimal", "Minimal")
        self.ui_widgets['chart_style'] = style_combo
        
        charts_box.pack_start(charts_check, False, False, 0)
        charts_box.pack_start(style_label, False, False, 0)
        charts_box.pack_start(style_combo, False, False, 0)
        charts_frame.add(charts_box)
        
        # Export directory
        export_frame = self._create_frame("Dossier d'export")
        export_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        export_entry = Gtk.Entry()
        export_button = Gtk.Button("Parcourir...")
        self.ui_widgets['export_directory'] = export_entry
        
        export_box.pack_start(export_entry, True, True, 0)
        export_box.pack_start(export_button, False, False, 0)
        export_frame.add(export_box)
        
        # Auto-save
        auto_frame = self._create_frame("Sauvegarde automatique")
        auto_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        auto_check = Gtk.CheckButton("Sauvegarder automatiquement les rapports")
        self.ui_widgets['auto_save_reports'] = auto_check
        
        auto_box.pack_start(auto_check, False, False, 0)
        auto_frame.add(auto_box)
        
        page.pack_start(format_frame, False, False, 0)
        page.pack_start(charts_frame, False, False, 0)
        page.pack_start(export_frame, False, False, 0)
        page.pack_start(auto_frame, False, False, 0)
        
        self.notebook.append_page(page, Gtk.Label("Rapports"))
    
    def _create_backup_tab(self):
        """Create backup and restore tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(12)
        
        # Backup operations
        backup_frame = self._create_frame("Sauvegarde de configuration")
        backup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        backup_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        create_backup_button = Gtk.Button("Créer une sauvegarde")
        export_button = Gtk.Button("Exporter la configuration")
        
        backup_button_box.pack_start(create_backup_button, False, False, 0)
        backup_button_box.pack_start(export_button, False, False, 0)
        
        backup_box.pack_start(backup_button_box, False, False, 0)
        backup_frame.add(backup_box)
        
        # Restore operations
        restore_frame = self._create_frame("Restauration")
        restore_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        restore_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        restore_button = Gtk.Button("Restaurer une sauvegarde")
        import_button = Gtk.Button("Importer une configuration")
        reset_button = Gtk.Button("Réinitialiser aux valeurs par défaut")
        
        restore_button_box.pack_start(restore_button, False, False, 0)
        restore_button_box.pack_start(import_button, False, False, 0)
        restore_button_box.pack_start(reset_button, False, False, 0)
        
        restore_box.pack_start(restore_button_box, False, False, 0)
        restore_frame.add(restore_box)
        
        # Backup list
        list_frame = self._create_frame("Sauvegardes disponibles")
        list_scrolled = Gtk.ScrolledWindow()
        list_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        list_scrolled.set_size_request(-1, 200)
        
        backup_listbox = Gtk.ListBox()
        self.ui_widgets['backup_list'] = backup_listbox
        list_scrolled.add(backup_listbox)
        list_frame.add(list_scrolled)
        
        page.pack_start(backup_frame, False, False, 0)
        page.pack_start(restore_frame, False, False, 0)
        page.pack_start(list_frame, True, True, 0)
        
        self.notebook.append_page(page, Gtk.Label("Sauvegarde"))
    
    def _create_frame(self, title: str) -> 'Gtk.Frame':
        """Create a frame with title."""
        frame = Gtk.Frame()
        frame.set_label(title)
        frame.set_label_align(0.02, 0.5)
        frame.set_border_width(6)
        return frame
    
    def _populate_settings(self):
        """Populate UI widgets with current settings."""
        try:
            config = self.config_manager.get_configuration()
            
            # UI preferences
            if 'theme' in self.ui_widgets:
                self.ui_widgets['theme'].set_active_id(config.ui.theme)
            if 'sidebar_width' in self.ui_widgets:
                self.ui_widgets['sidebar_width'].set_value(config.ui.sidebar_width)
            if 'window_width' in self.ui_widgets:
                self.ui_widgets['window_width'].set_value(config.ui.window_width)
            if 'window_height' in self.ui_widgets:
                self.ui_widgets['window_height'].set_value(config.ui.window_height)
            if 'show_tooltips' in self.ui_widgets:
                self.ui_widgets['show_tooltips'].set_active(config.ui.show_tooltips)
            if 'animation_enabled' in self.ui_widgets:
                self.ui_widgets['animation_enabled'].set_active(config.ui.animation_enabled)
            
            # Analysis preferences
            if 'include_hidden_files' in self.ui_widgets:
                self.ui_widgets['include_hidden_files'].set_active(config.analysis.include_hidden_files)
            if 'follow_symlinks' in self.ui_widgets:
                self.ui_widgets['follow_symlinks'].set_active(config.analysis.follow_symlinks)
            if 'max_depth' in self.ui_widgets:
                self.ui_widgets['max_depth'].set_value(config.analysis.max_depth)
            if 'file_size_threshold' in self.ui_widgets:
                self.ui_widgets['file_size_threshold'].set_value(config.analysis.file_size_threshold)
            if 'enable_duplicate_detection' in self.ui_widgets:
                self.ui_widgets['enable_duplicate_detection'].set_active(config.analysis.enable_duplicate_detection)
            if 'hash_algorithm' in self.ui_widgets:
                self.ui_widgets['hash_algorithm'].set_active_id(config.analysis.hash_algorithm)
            
            # Cleaning preferences
            if 'dry_run_by_default' in self.ui_widgets:
                self.ui_widgets['dry_run_by_default'].set_active(config.cleaning.dry_run_by_default)
            if 'confirm_before_delete' in self.ui_widgets:
                self.ui_widgets['confirm_before_delete'].set_active(config.cleaning.confirm_before_delete)
            if 'backup_before_clean' in self.ui_widgets:
                self.ui_widgets['backup_before_clean'].set_active(config.cleaning.backup_before_clean)
            if 'backup_retention_days' in self.ui_widgets:
                self.ui_widgets['backup_retention_days'].set_value(config.cleaning.backup_retention_days)
            
            # App-specific cleaning
            if 'app_firefox' in self.ui_widgets:
                self.ui_widgets['app_firefox'].set_active(config.cleaning.app_specific_cleaning.get('firefox', True))
            if 'app_chrome' in self.ui_widgets:
                self.ui_widgets['app_chrome'].set_active(config.cleaning.app_specific_cleaning.get('chrome', True))
            if 'app_flatpak' in self.ui_widgets:
                self.ui_widgets['app_flatpak'].set_active(config.cleaning.app_specific_cleaning.get('flatpak', True))
            if 'app_snap' in self.ui_widgets:
                self.ui_widgets['app_snap'].set_active(config.cleaning.app_specific_cleaning.get('snap', True))
            
            # Monitoring preferences
            if 'enable_realtime' in self.ui_widgets:
                self.ui_widgets['enable_realtime'].set_active(config.monitoring.enable_realtime)
            if 'update_interval' in self.ui_widgets:
                self.ui_widgets['update_interval'].set_value(config.monitoring.update_interval)
            if 'enable_notifications' in self.ui_widgets:
                self.ui_widgets['enable_notifications'].set_active(config.monitoring.enable_notifications)
            if 'notification_cooldown' in self.ui_widgets:
                self.ui_widgets['notification_cooldown'].set_value(config.monitoring.notification_cooldown)
            if 'disk_usage_threshold' in self.ui_widgets:
                self.ui_widgets['disk_usage_threshold'].set_value(config.monitoring.disk_usage_threshold)
            if 'cpu_usage_threshold' in self.ui_widgets:
                self.ui_widgets['cpu_usage_threshold'].set_value(config.monitoring.cpu_usage_threshold)
            if 'memory_usage_threshold' in self.ui_widgets:
                self.ui_widgets['memory_usage_threshold'].set_value(config.monitoring.memory_usage_threshold)
            
            # Reporting preferences
            if 'default_format' in self.ui_widgets:
                self.ui_widgets['default_format'].set_active_id(config.reporting.default_format)
            if 'include_charts' in self.ui_widgets:
                self.ui_widgets['include_charts'].set_active(config.reporting.include_charts)
            if 'chart_style' in self.ui_widgets:
                self.ui_widgets['chart_style'].set_active_id(config.reporting.chart_style)
            if 'export_directory' in self.ui_widgets:
                self.ui_widgets['export_directory'].set_text(config.reporting.export_directory)
            if 'auto_save_reports' in self.ui_widgets:
                self.ui_widgets['auto_save_reports'].set_active(config.reporting.auto_save_reports)
            
        except Exception as e:
            self.logger.error(f"Error populating settings: {e}")
    
    def _save_settings(self) -> bool:
        """Save settings from UI widgets."""
        try:
            config = self.config_manager.get_configuration()
            
            # UI preferences
            if 'theme' in self.ui_widgets:
                config.ui.theme = self.ui_widgets['theme'].get_active_id() or "auto"
            if 'sidebar_width' in self.ui_widgets:
                config.ui.sidebar_width = int(self.ui_widgets['sidebar_width'].get_value())
            if 'window_width' in self.ui_widgets:
                config.ui.window_width = int(self.ui_widgets['window_width'].get_value())
            if 'window_height' in self.ui_widgets:
                config.ui.window_height = int(self.ui_widgets['window_height'].get_value())
            if 'show_tooltips' in self.ui_widgets:
                config.ui.show_tooltips = self.ui_widgets['show_tooltips'].get_active()
            if 'animation_enabled' in self.ui_widgets:
                config.ui.animation_enabled = self.ui_widgets['animation_enabled'].get_active()
            
            # Analysis preferences
            if 'include_hidden_files' in self.ui_widgets:
                config.analysis.include_hidden_files = self.ui_widgets['include_hidden_files'].get_active()
            if 'follow_symlinks' in self.ui_widgets:
                config.analysis.follow_symlinks = self.ui_widgets['follow_symlinks'].get_active()
            if 'max_depth' in self.ui_widgets:
                config.analysis.max_depth = int(self.ui_widgets['max_depth'].get_value())
            if 'file_size_threshold' in self.ui_widgets:
                config.analysis.file_size_threshold = int(self.ui_widgets['file_size_threshold'].get_value())
            if 'enable_duplicate_detection' in self.ui_widgets:
                config.analysis.enable_duplicate_detection = self.ui_widgets['enable_duplicate_detection'].get_active()
            if 'hash_algorithm' in self.ui_widgets:
                config.analysis.hash_algorithm = self.ui_widgets['hash_algorithm'].get_active_id() or "sha256"
            
            # Cleaning preferences
            if 'dry_run_by_default' in self.ui_widgets:
                config.cleaning.dry_run_by_default = self.ui_widgets['dry_run_by_default'].get_active()
            if 'confirm_before_delete' in self.ui_widgets:
                config.cleaning.confirm_before_delete = self.ui_widgets['confirm_before_delete'].get_active()
            if 'backup_before_clean' in self.ui_widgets:
                config.cleaning.backup_before_clean = self.ui_widgets['backup_before_clean'].get_active()
            if 'backup_retention_days' in self.ui_widgets:
                config.cleaning.backup_retention_days = int(self.ui_widgets['backup_retention_days'].get_value())
            
            # App-specific cleaning
            if 'app_firefox' in self.ui_widgets:
                config.cleaning.app_specific_cleaning['firefox'] = self.ui_widgets['app_firefox'].get_active()
            if 'app_chrome' in self.ui_widgets:
                config.cleaning.app_specific_cleaning['chrome'] = self.ui_widgets['app_chrome'].get_active()
            if 'app_flatpak' in self.ui_widgets:
                config.cleaning.app_specific_cleaning['flatpak'] = self.ui_widgets['app_flatpak'].get_active()
            if 'app_snap' in self.ui_widgets:
                config.cleaning.app_specific_cleaning['snap'] = self.ui_widgets['app_snap'].get_active()
            
            # Monitoring preferences
            if 'enable_realtime' in self.ui_widgets:
                config.monitoring.enable_realtime = self.ui_widgets['enable_realtime'].get_active()
            if 'update_interval' in self.ui_widgets:
                config.monitoring.update_interval = int(self.ui_widgets['update_interval'].get_value())
            if 'enable_notifications' in self.ui_widgets:
                config.monitoring.enable_notifications = self.ui_widgets['enable_notifications'].get_active()
            if 'notification_cooldown' in self.ui_widgets:
                config.monitoring.notification_cooldown = int(self.ui_widgets['notification_cooldown'].get_value())
            if 'disk_usage_threshold' in self.ui_widgets:
                config.monitoring.disk_usage_threshold = self.ui_widgets['disk_usage_threshold'].get_value()
            if 'cpu_usage_threshold' in self.ui_widgets:
                config.monitoring.cpu_usage_threshold = self.ui_widgets['cpu_usage_threshold'].get_value()
            if 'memory_usage_threshold' in self.ui_widgets:
                config.monitoring.memory_usage_threshold = self.ui_widgets['memory_usage_threshold'].get_value()
            
            # Reporting preferences
            if 'default_format' in self.ui_widgets:
                config.reporting.default_format = self.ui_widgets['default_format'].get_active_id() or "pdf"
            if 'include_charts' in self.ui_widgets:
                config.reporting.include_charts = self.ui_widgets['include_charts'].get_active()
            if 'chart_style' in self.ui_widgets:
                config.reporting.chart_style = self.ui_widgets['chart_style'].get_active_id() or "modern"
            if 'export_directory' in self.ui_widgets:
                config.reporting.export_directory = self.ui_widgets['export_directory'].get_text()
            if 'auto_save_reports' in self.ui_widgets:
                config.reporting.auto_save_reports = self.ui_widgets['auto_save_reports'].get_active()
            
            # Save configuration
            return self.config_manager.save_configuration(config)
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False