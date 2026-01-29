# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from .base_page import BasePage

class DashboardPage(BasePage):
    def setup_ui(self):
        self.get_style_context().add_class("dashboard-page")

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title = Gtk.Label(label=self._("Tableau de Bord"))
        title.get_style_context().add_class("page-title")
        title.set_halign(Gtk.Align.START)
        header_hbox.pack_start(title, False, False, 0)

        version_tag = Gtk.Label(label="v3.1.0")
        version_tag.get_style_context().add_class("version-tag")
        header_hbox.pack_start(version_tag, False, False, 0)

        header_box.pack_start(header_hbox, False, False, 0)

        subtitle = Gtk.Label(label=self._("Vue d'ensemble de l'utilisation du stockage système"))
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.pack_start(subtitle, False, False, 0)

        self.pack_start(header_box, False, False, 0)

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)

        # Stats
        stats_frame = Gtk.Frame()
        stats_frame.get_style_context().add_class("stat-card")
        stats_frame.set_label(self._("Statistiques Système"))
        stats_frame.set_size_request(320, -1)

        stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        stats_box.set_border_width(20)

        usage = psutil.disk_usage('/')
        stats_box.pack_start(self.main_window._create_stat_row(self._("Espace Total"), self.main_window.format_size(usage.total)), False, False, 0)
        stats_box.pack_start(self.main_window._create_stat_row(self._("Espace Utilisé"), f"{self.main_window.format_size(usage.used)} ({usage.percent:.1f}%)"), False, False, 0)
        stats_box.pack_start(self.main_window._create_stat_row(self._("Espace Libre"), self.main_window.format_size(usage.free)), False, False, 0)

        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        progress_label = Gtk.Label(label=self._("Utilisation"))
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

        # Chart
        chart_frame = Gtk.Frame()
        chart_frame.get_style_context().add_class("stat-card")
        chart_frame.set_label(self._("Répartition de l'Espace"))

        fig, ax = plt.subplots(figsize=(6, 5), dpi=100)
        fig.patch.set_facecolor('none')

        labels = [self._('Utilisé'), self._('Libre')]
        sizes = [usage.used, usage.free]
        colors = ['#e74c3c', '#2ecc71']

        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                         startangle=90, colors=colors,
                                         textprops={'fontsize': 11})
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        ax.axis('equal')

        canvas = FigureCanvas(fig)
        canvas.set_size_request(400, 350)
        chart_frame.add(canvas)
        content_box.pack_start(chart_frame, True, True, 0)

        self.pack_start(content_box, True, True, 0)

        # Actions
        actions_frame = Gtk.Frame()
        actions_frame.set_label(self._("Actions Rapides"))
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        actions_box.set_border_width(15)

        analyze_btn = Gtk.Button(label=self._("Analyser /home"))
        analyze_btn.get_style_context().add_class("suggested-action")
        analyze_btn.connect("clicked", self.main_window._on_quick_analyze_home)
        actions_box.pack_start(analyze_btn, False, False, 0)

        clean_btn = Gtk.Button(label=self._("Nettoyage Rapide"))
        clean_btn.connect("clicked", self.main_window._on_quick_clean)
        actions_box.pack_start(clean_btn, False, False, 0)

        refresh_btn = Gtk.Button(label=self._("Actualiser"))
        refresh_btn.connect("clicked", self.main_window._on_refresh_dashboard)
        actions_box.pack_start(refresh_btn, False, False, 0)

        actions_frame.add(actions_box)
        self.pack_start(actions_frame, False, False, 0)
