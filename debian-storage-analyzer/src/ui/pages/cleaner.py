# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .base_page import BasePage

class CleanerPage(BasePage):
    def setup_ui(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Label(label=self._("Nettoyage Système"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label=self._("Nettoyer les fichiers temporaires et caches système"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)
        self.pack_start(header_box, False, False, 0)

        # Nettoyage Intelligent
        intelligent_frame = Gtk.Frame()
        intelligent_frame.set_label(self._("Nettoyage Intelligent"))
        intelligent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        intelligent_box.set_border_width(15)

        intelligent_desc = Gtk.Label(label=self._("Analyse avancée pour trouver des caches, logs et fichiers temporaires sûrs à supprimer."))
        intelligent_desc.set_line_wrap(True)
        intelligent_desc.set_halign(Gtk.Align.START)
        intelligent_box.pack_start(intelligent_desc, False, False, 0)

        intelligent_btn = Gtk.Button(label=self._("Scanner les opportunités de nettoyage"))
        intelligent_btn.get_style_context().add_class("suggested-action")
        intelligent_btn.connect("clicked", self.on_intelligent_scan_clicked)
        intelligent_box.pack_start(intelligent_btn, False, False, 0)

        self.intelligent_results_list = Gtk.ListBox()
        self.intelligent_results_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled_intelligent = Gtk.ScrolledWindow()
        scrolled_intelligent.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_intelligent.set_min_content_height(200)
        scrolled_intelligent.add(self.intelligent_results_list)
        intelligent_box.pack_start(scrolled_intelligent, True, True, 0)

        intelligent_frame.add(intelligent_box)
        self.pack_start(intelligent_frame, True, True, 0)

        # Options de nettoyage
        cleaners_frame = Gtk.Frame()
        cleaners_frame.set_label(self._("Actions Classiques"))

        cleaners_list = Gtk.ListBox()
        cleaners_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Cache APT"),
                                   self._("Supprime les paquets téléchargés (.deb)"),
                                   self.main_window.on_clean_apt_clicked, "clean_apt")

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Dépendances inutiles"),
                                   self._("Supprime les paquets orphelins (autoremove)"),
                                   self.main_window.on_autoremove_clicked, "clean_autoremove")

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Fichiers Temporaires"),
                                   self._("Nettoie /tmp et /var/tmp (> 7 jours)"),
                                   self.main_window.on_clean_temp_clicked, "clean_temp")

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Journaux Système"),
                                   self._("Réduit la taille des logs journald"),
                                   self.main_window.on_clean_logs_clicked, "clean_logs")

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Firefox Cache"),
                                   self._("Nettoie le cache de Firefox"),
                                   self.main_window.on_clean_firefox_clicked, "clean_firefox")

        self.main_window._add_modern_cleaner_row(cleaners_list, self._("Flatpak Cache"),
                                   self._("Nettoie le cache des applications Flatpak"),
                                   self.main_window.on_clean_flatpak_clicked, "clean_flatpak")

        cleaners_frame.add(cleaners_list)
        self.pack_start(cleaners_frame, False, False, 0)

    def on_intelligent_scan_clicked(self, widget):
        from cleaner.intelligent_cleaner import IntelligentCleaner
        cleaner = IntelligentCleaner(dry_run=True)
        actions = cleaner.scan_for_cleaning_opportunities()

        # Vider la liste
        for child in self.intelligent_results_list.get_children():
            self.intelligent_results_list.remove(child)

        if not actions:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=self._("Aucune opportunité trouvée."))
            label.set_margin_top(10)
            label.set_margin_bottom(10)
            row.add(label)
            self.intelligent_results_list.add(row)
        else:
            for action in actions:
                row = self._create_action_row(action)
                self.intelligent_results_list.add(row)

        self.intelligent_results_list.show_all()

    def _create_action_row(self, action):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label=action.description)
        title.set_halign(Gtk.Align.START)
        title.get_style_context().add_class("cleaner-name")
        vbox.pack_start(title, False, False, 0)

        details = Gtk.Label(label=f"{self.main_window.format_size(action.size_bytes)} - {action.category}")
        details.set_halign(Gtk.Align.START)
        details.get_style_context().add_class("cleaner-description")
        vbox.pack_start(details, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)

        clean_btn = Gtk.Button(label=self._("Nettoyer"))
        clean_btn.get_style_context().add_class("destructive-action")
        clean_btn.connect("clicked", self.on_execute_action_clicked, action)
        hbox.pack_start(clean_btn, False, False, 0)

        row.add(hbox)
        return row

    def on_execute_action_clicked(self, widget, action):
        from cleaner.intelligent_cleaner import IntelligentCleaner
        # Ici on devrait normalement demander confirmation ou gérer les privilèges si nécessaire
        cleaner = IntelligentCleaner(dry_run=False)
        results = cleaner.execute_cleaning_actions([action])
        if results and results[0].success:
            self.main_window.show_info_dialog(self._("Succès"),
                                           self._("Nettoyage effectué : ") + action.description)
            self.on_intelligent_scan_clicked(None)
        else:
            msg = results[0].error_message if results else self._("Erreur inconnue")
            self.main_window.show_info_dialog(self._("Erreur"), msg)
