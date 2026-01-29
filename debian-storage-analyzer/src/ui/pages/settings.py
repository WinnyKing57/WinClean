# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage

class SettingsPage(BasePage):
    def setup_ui(self):
        title = Gtk.Label(label=self._("Paramètres"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        self.pack_start(title, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        # Thème
        theme_frame = Gtk.Frame(label=self._("Apparence"))
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        theme_box.set_border_width(10)
        theme_box.pack_start(Gtk.Label(label=self._("Thème")), False, False, 0)

        theme_combo = Gtk.ComboBoxText()
        theme_combo.append("auto", self._("Automatique"))
        theme_combo.append("light", self._("Clair"))
        theme_combo.append("dark", self._("Sombre"))

        current_config = self.main_window.config_manager.get_configuration()
        theme_combo.set_active_id(current_config.ui.theme)
        theme_combo.connect("changed", self.main_window.on_theme_changed)

        theme_box.pack_end(theme_combo, False, False, 0)
        theme_frame.add(theme_box)
        settings_box.pack_start(theme_frame, False, False, 0)

        # Analyse
        analysis_frame = Gtk.Frame(label=self._("Analyse"))
        analysis_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        analysis_box.set_border_width(10)

        hidden_switch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hidden_switch.pack_start(Gtk.Label(label=self._("Inclure les fichiers cachés")), False, False, 0)
        self.main_window.hidden_sw = Gtk.Switch()
        self.main_window.hidden_sw.set_active(current_config.analysis.include_hidden_files)
        self.main_window.hidden_sw.connect("state-set", self.main_window.on_analysis_setting_changed, "include_hidden_files")
        hidden_switch.pack_end(self.main_window.hidden_sw, False, False, 0)
        analysis_box.pack_start(hidden_switch, False, False, 0)

        analysis_frame.add(analysis_box)
        settings_box.pack_start(analysis_frame, False, False, 0)

        # Planification
        planning_frame = Gtk.Frame(label=self._("Nettoyage Automatique"))
        planning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        planning_box.set_border_width(10)
        planning_box.pack_start(Gtk.Label(label=self._("Activer les tâches systemd/cron par défaut")), False, False, 0)

        default_plan_btn = Gtk.Button(label=self._("Initialiser les planifications par défaut"))
        default_plan_btn.connect("clicked", self.main_window.on_init_default_schedules)
        planning_box.pack_start(default_plan_btn, False, False, 0)

        planning_frame.add(planning_box)
        settings_box.pack_start(planning_frame, False, False, 0)

        scrolled.add(settings_box)
        self.pack_start(scrolled, True, True, 0)
