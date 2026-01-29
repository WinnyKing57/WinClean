# -*- coding: utf-8 -*-

import os
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
import logging

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GObject, GLib
    GTK_AVAILABLE = True
    GtkWidget = Gtk.Widget
    GtkProgressBar = Gtk.ProgressBar
except ImportError:
    GTK_AVAILABLE = False
    GtkWidget = object  # Fallback type
    GtkProgressBar = object  # Fallback type
    # Create dummy classes for type annotations
    class Gtk:
        Widget = object
        ProgressBar = object
    class GLib:
        pass

from ..main.realtime_monitor import SystemMetrics, ActivityAlert


class ProgressIndicator:
    """Indicateur de progression pour opérations longues"""
    
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.dialog = None
        self.progress_bar = None
        self.label = None
        self.cancel_button = None
        self.is_cancelled = False
        self.cancel_callback: Optional[Callable] = None
        self.logger = logging.getLogger(__name__)
    
    def show(self, title: str = "Opération en cours", 
             message: str = "Veuillez patienter...", 
             cancellable: bool = True) -> bool:
        """Affiche l'indicateur de progression"""
        if not GTK_AVAILABLE:
            self.logger.warning("GTK non disponible - indicateur de progression ignoré")
            return False
        
        try:
            # Créer la boîte de dialogue
            self.dialog = Gtk.Dialog(
                title=title,
                parent=self.parent_window,
                flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
            )
            
            self.dialog.set_default_size(400, 150)
            self.dialog.set_resizable(False)
            
            # Contenu
            content_area = self.dialog.get_content_area()
            content_area.set_spacing(10)
            content_area.set_margin_left(20)
            content_area.set_margin_right(20)
            content_area.set_margin_top(20)
            content_area.set_margin_bottom(20)
            
            # Label du message
            self.label = Gtk.Label(label=message)
            self.label.set_line_wrap(True)
            self.label.set_justify(Gtk.Justification.CENTER)
            content_area.pack_start(self.label, False, False, 0)
            
            # Barre de progression
            self.progress_bar = Gtk.ProgressBar()
            self.progress_bar.set_show_text(True)
            self.progress_bar.set_text("0%")
            content_area.pack_start(self.progress_bar, False, False, 0)
            
            # Bouton d'annulation
            if cancellable:
                self.cancel_button = Gtk.Button(label="Annuler")
                self.cancel_button.connect("clicked", self._on_cancel_clicked)
                content_area.pack_start(self.cancel_button, False, False, 0)
            
            self.dialog.show_all()
            return True
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'affichage de l'indicateur: {e}")
            return False
    
    def update_progress(self, progress: float, message: str = None):
        """Met à jour la progression (0.0 à 1.0)"""
        if not self.progress_bar:
            return
        
        def update():
            self.progress_bar.set_fraction(max(0.0, min(1.0, progress)))
            self.progress_bar.set_text(f"{progress * 100:.0f}%")
            
            if message and self.label:
                self.label.set_text(message)
            
            return False
        
        GLib.idle_add(update)
    
    def pulse(self):
        """Active le mode pulsation (progression indéterminée)"""
        if not self.progress_bar:
            return
        
        def pulse():
            self.progress_bar.pulse()
            return False
        
        GLib.idle_add(pulse)
    
    def set_cancel_callback(self, callback: Callable):
        """Définit le callback d'annulation"""
        self.cancel_callback = callback
    
    def _on_cancel_clicked(self, button):
        """Gestionnaire du bouton d'annulation"""
        self.is_cancelled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.hide()
    
    def hide(self):
        """Cache l'indicateur de progression"""
        if self.dialog:
            def hide():
                self.dialog.destroy()
                self.dialog = None
                return False
            
            GLib.idle_add(hide)
    
    def is_visible(self) -> bool:
        """Vérifie si l'indicateur est visible"""
        return self.dialog is not None and self.dialog.get_visible()


class SystemStatusIndicator:
    """Indicateur visuel de l'état du système"""
    
    def __init__(self):
        self.status_widget = None
        self.cpu_bar = None
        self.memory_bar = None
        self.disk_bar = None
        self.status_label = None
        self.alert_icon = None
        self.current_metrics: Optional[SystemMetrics] = None
        self.current_alerts: List[ActivityAlert] = []
        self.logger = logging.getLogger(__name__)
    
    def create_widget(self) -> Optional[GtkWidget]:
        """Crée le widget d'indicateur de statut"""
        if not GTK_AVAILABLE:
            return None
        
        try:
            # Conteneur principal
            self.status_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            self.status_widget.set_margin_left(10)
            self.status_widget.set_margin_right(10)
            self.status_widget.set_margin_top(5)
            self.status_widget.set_margin_bottom(5)
            
            # Titre
            title_label = Gtk.Label(label="État du Système")
            title_label.set_markup("<b>État du Système</b>")
            self.status_widget.pack_start(title_label, False, False, 0)
            
            # Barres de progression pour les ressources
            resources_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            
            # CPU
            cpu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            cpu_label = Gtk.Label(label="CPU:")
            cpu_label.set_size_request(60, -1)
            cpu_label.set_xalign(0)
            self.cpu_bar = Gtk.ProgressBar()
            self.cpu_bar.set_show_text(True)
            self.cpu_bar.set_text("0%")
            cpu_box.pack_start(cpu_label, False, False, 0)
            cpu_box.pack_start(self.cpu_bar, True, True, 0)
            resources_box.pack_start(cpu_box, False, False, 0)
            
            # Mémoire
            memory_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            memory_label = Gtk.Label(label="RAM:")
            memory_label.set_size_request(60, -1)
            memory_label.set_xalign(0)
            self.memory_bar = Gtk.ProgressBar()
            self.memory_bar.set_show_text(True)
            self.memory_bar.set_text("0%")
            memory_box.pack_start(memory_label, False, False, 0)
            memory_box.pack_start(self.memory_bar, True, True, 0)
            resources_box.pack_start(memory_box, False, False, 0)
            
            # Disque
            disk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            disk_label = Gtk.Label(label="Disque:")
            disk_label.set_size_request(60, -1)
            disk_label.set_xalign(0)
            self.disk_bar = Gtk.ProgressBar()
            self.disk_bar.set_show_text(True)
            self.disk_bar.set_text("0%")
            disk_box.pack_start(disk_label, False, False, 0)
            disk_box.pack_start(self.disk_bar, True, True, 0)
            resources_box.pack_start(disk_box, False, False, 0)
            
            self.status_widget.pack_start(resources_box, False, False, 0)
            
            # Séparateur
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            self.status_widget.pack_start(separator, False, False, 0)
            
            # Zone d'alerte
            alert_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            self.alert_icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.SMALL_TOOLBAR)
            self.status_label = Gtk.Label(label="Système normal")
            self.status_label.set_line_wrap(True)
            self.status_label.set_xalign(0)
            alert_box.pack_start(self.alert_icon, False, False, 0)
            alert_box.pack_start(self.status_label, True, True, 0)
            self.status_widget.pack_start(alert_box, False, False, 0)
            
            return self.status_widget
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du widget de statut: {e}")
            return None
    
    def update_metrics(self, metrics: SystemMetrics):
        """Met à jour l'affichage avec les nouvelles métriques"""
        self.current_metrics = metrics
        
        if not self.status_widget:
            return
        
        def update():
            try:
                # Mettre à jour les barres de progression
                if self.cpu_bar:
                    self.cpu_bar.set_fraction(metrics.cpu_percent / 100.0)
                    self.cpu_bar.set_text(f"{metrics.cpu_percent:.1f}%")
                    
                    # Couleur selon l'utilisation
                    if metrics.cpu_percent > 80:
                        self._set_progress_bar_color(self.cpu_bar, "red")
                    elif metrics.cpu_percent > 60:
                        self._set_progress_bar_color(self.cpu_bar, "orange")
                    else:
                        self._set_progress_bar_color(self.cpu_bar, "green")
                
                if self.memory_bar:
                    self.memory_bar.set_fraction(metrics.memory_percent / 100.0)
                    self.memory_bar.set_text(f"{metrics.memory_percent:.1f}%")
                    
                    if metrics.memory_percent > 85:
                        self._set_progress_bar_color(self.memory_bar, "red")
                    elif metrics.memory_percent > 70:
                        self._set_progress_bar_color(self.memory_bar, "orange")
                    else:
                        self._set_progress_bar_color(self.memory_bar, "green")
                
                if self.disk_bar:
                    self.disk_bar.set_fraction(metrics.disk_usage_percent / 100.0)
                    self.disk_bar.set_text(f"{metrics.disk_usage_percent:.1f}%")
                    
                    if metrics.disk_usage_percent > 90:
                        self._set_progress_bar_color(self.disk_bar, "red")
                    elif metrics.disk_usage_percent > 80:
                        self._set_progress_bar_color(self.disk_bar, "orange")
                    else:
                        self._set_progress_bar_color(self.disk_bar, "green")
            
            except Exception as e:
                self.logger.error(f"Erreur lors de la mise à jour des métriques: {e}")
            
            return False
        
        GLib.idle_add(update)
    
    def update_alerts(self, alerts: List[ActivityAlert]):
        """Met à jour l'affichage des alertes"""
        self.current_alerts = alerts
        
        if not self.status_widget:
            return
        
        def update():
            try:
                if not alerts:
                    # Pas d'alerte
                    if self.alert_icon:
                        self.alert_icon.set_from_icon_name("dialog-information", Gtk.IconSize.SMALL_TOOLBAR)
                    if self.status_label:
                        self.status_label.set_text("Système normal")
                        self.status_label.set_markup("Système normal")
                else:
                    # Afficher l'alerte la plus critique
                    severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
                    top_alert = max(alerts, key=lambda a: severity_order.get(a.severity, 0))
                    
                    # Icône selon la sévérité
                    icon_map = {
                        'low': 'dialog-information',
                        'medium': 'dialog-warning',
                        'high': 'dialog-warning',
                        'critical': 'dialog-error'
                    }
                    
                    if self.alert_icon:
                        icon_name = icon_map.get(top_alert.severity, 'dialog-warning')
                        self.alert_icon.set_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)
                    
                    if self.status_label:
                        # Couleur selon la sévérité
                        color_map = {
                            'low': 'blue',
                            'medium': 'orange',
                            'high': 'red',
                            'critical': 'darkred'
                        }
                        
                        color = color_map.get(top_alert.severity, 'black')
                        markup = f'<span color="{color}"><b>{top_alert.message}</b></span>'
                        self.status_label.set_markup(markup)
            
            except Exception as e:
                self.logger.error(f"Erreur lors de la mise à jour des alertes: {e}")
            
            return False
        
        GLib.idle_add(update)
    
    def _set_progress_bar_color(self, progress_bar: Gtk.ProgressBar, color: str):
        """Définit la couleur d'une barre de progression"""
        try:
            css_provider = Gtk.CssProvider()
            css_data = f"""
            progressbar progress {{
                background-color: {color};
            }}
            """
            css_provider.load_from_data(css_data.encode())
            
            context = progress_bar.get_style_context()
            context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            self.logger.error(f"Erreur lors de la définition de la couleur: {e}")


class ActivityIndicator:
    """Indicateur d'activité inhabituelle"""
    
    def __init__(self):
        self.indicator_widget = None
        self.activity_list = None
        self.activity_store = None
        self.logger = logging.getLogger(__name__)
        self.recent_activities: List[Dict] = []
        self.max_activities = 50
    
    def create_widget(self) -> Optional[GtkWidget]:
        """Crée le widget d'indicateur d'activité"""
        if not GTK_AVAILABLE:
            return None
        
        try:
            # Conteneur principal
            self.indicator_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            
            # Titre
            title_label = Gtk.Label(label="Activité Récente")
            title_label.set_markup("<b>Activité Récente</b>")
            self.indicator_widget.pack_start(title_label, False, False, 0)
            
            # Liste des activités
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_size_request(-1, 200)
            
            # Modèle de données: timestamp, type, severity, message
            self.activity_store = Gtk.ListStore(str, str, str, str)
            
            self.activity_list = Gtk.TreeView(model=self.activity_store)
            self.activity_list.set_headers_visible(True)
            
            # Colonnes
            time_column = Gtk.TreeViewColumn("Heure")
            time_renderer = Gtk.CellRendererText()
            time_column.pack_start(time_renderer, True)
            time_column.add_attribute(time_renderer, "text", 0)
            time_column.set_min_width(80)
            self.activity_list.append_column(time_column)
            
            severity_column = Gtk.TreeViewColumn("Sévérité")
            severity_renderer = Gtk.CellRendererText()
            severity_column.pack_start(severity_renderer, True)
            severity_column.add_attribute(severity_renderer, "text", 2)
            severity_column.set_min_width(80)
            self.activity_list.append_column(severity_column)
            
            message_column = Gtk.TreeViewColumn("Message")
            message_renderer = Gtk.CellRendererText()
            message_renderer.set_property("wrap-mode", 2)  # WORD_CHAR
            message_renderer.set_property("wrap-width", 300)
            message_column.pack_start(message_renderer, True)
            message_column.add_attribute(message_renderer, "text", 3)
            message_column.set_expand(True)
            self.activity_list.append_column(message_column)
            
            scrolled.add(self.activity_list)
            self.indicator_widget.pack_start(scrolled, True, True, 0)
            
            return self.indicator_widget
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du widget d'activité: {e}")
            return None
    
    def add_activity(self, activity_type: str, severity: str, message: str):
        """Ajoute une activité à la liste"""
        timestamp = datetime.now()
        
        activity = {
            'timestamp': timestamp,
            'type': activity_type,
            'severity': severity,
            'message': message
        }
        
        self.recent_activities.append(activity)
        
        # Limiter la taille de l'historique
        if len(self.recent_activities) > self.max_activities:
            self.recent_activities.pop(0)
        
        # Mettre à jour l'affichage
        if self.activity_store:
            def update():
                try:
                    time_str = timestamp.strftime("%H:%M:%S")
                    self.activity_store.append([time_str, activity_type, severity, message])
                    
                    # Limiter les entrées affichées
                    if len(self.activity_store) > self.max_activities:
                        iter_first = self.activity_store.get_iter_first()
                        if iter_first:
                            self.activity_store.remove(iter_first)
                    
                    # Faire défiler vers le bas
                    if self.activity_list:
                        path = Gtk.TreePath.new_from_indices([len(self.activity_store) - 1])
                        self.activity_list.scroll_to_cell(path, None, False, 0.0, 0.0)
                
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'ajout d'activité: {e}")
                
                return False
            
            GLib.idle_add(update)
    
    def add_alert(self, alert: ActivityAlert):
        """Ajoute une alerte comme activité"""
        self.add_activity(alert.alert_type, alert.severity, alert.message)
    
    def clear_activities(self):
        """Efface toutes les activités"""
        self.recent_activities.clear()
        
        if self.activity_store:
            def clear():
                self.activity_store.clear()
                return False
            
            GLib.idle_add(clear)
    
    def get_activities(self) -> List[Dict]:
        """Obtient la liste des activités récentes"""
        return self.recent_activities.copy()


class VisualFeedbackManager:
    """Gestionnaire centralisé du feedback visuel"""
    
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.progress_indicator = ProgressIndicator(parent_window)
        self.status_indicator = SystemStatusIndicator()
        self.activity_indicator = ActivityIndicator()
        self.logger = logging.getLogger(__name__)
        
        # État des opérations en cours
        self.active_operations: Dict[str, Dict] = {}
    
    def create_status_widget(self) -> Optional[GtkWidget]:
        """Crée le widget de statut système"""
        return self.status_indicator.create_widget()
    
    def create_activity_widget(self) -> Optional[GtkWidget]:
        """Crée le widget d'activité"""
        return self.activity_indicator.create_widget()
    
    def update_system_metrics(self, metrics: SystemMetrics):
        """Met à jour les métriques système"""
        self.status_indicator.update_metrics(metrics)
    
    def update_system_alerts(self, alerts: List[ActivityAlert]):
        """Met à jour les alertes système"""
        self.status_indicator.update_alerts(alerts)
        
        # Ajouter les nouvelles alertes à l'indicateur d'activité
        for alert in alerts:
            self.activity_indicator.add_alert(alert)
    
    def start_operation(self, operation_id: str, title: str, 
                       message: str = "Opération en cours...", 
                       cancellable: bool = True) -> bool:
        """Démarre l'affichage d'une opération longue"""
        if operation_id in self.active_operations:
            self.logger.warning(f"Opération {operation_id} déjà active")
            return False
        
        success = self.progress_indicator.show(title, message, cancellable)
        if success:
            self.active_operations[operation_id] = {
                'title': title,
                'start_time': datetime.now(),
                'cancellable': cancellable
            }
        
        return success
    
    def update_operation_progress(self, operation_id: str, 
                                progress: float, message: str = None):
        """Met à jour la progression d'une opération"""
        if operation_id not in self.active_operations:
            return
        
        self.progress_indicator.update_progress(progress, message)
    
    def pulse_operation(self, operation_id: str):
        """Active le mode pulsation pour une opération"""
        if operation_id not in self.active_operations:
            return
        
        self.progress_indicator.pulse()
    
    def finish_operation(self, operation_id: str):
        """Termine une opération"""
        if operation_id not in self.active_operations:
            return
        
        self.progress_indicator.hide()
        del self.active_operations[operation_id]
    
    def set_operation_cancel_callback(self, operation_id: str, callback: Callable):
        """Définit le callback d'annulation pour une opération"""
        if operation_id not in self.active_operations:
            return
        
        self.progress_indicator.set_cancel_callback(callback)
    
    def is_operation_active(self, operation_id: str) -> bool:
        """Vérifie si une opération est active"""
        return operation_id in self.active_operations
    
    def get_active_operations(self) -> List[str]:
        """Obtient la liste des opérations actives"""
        return list(self.active_operations.keys())
    
    def add_activity_message(self, activity_type: str, severity: str, message: str):
        """Ajoute un message d'activité"""
        self.activity_indicator.add_activity(activity_type, severity, message)
    
    def clear_activity_history(self):
        """Efface l'historique d'activité"""
        self.activity_indicator.clear_activities()