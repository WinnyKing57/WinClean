# -*- coding: utf-8 -*-

import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import logging

from .realtime_monitor import RealTimeMonitor, DesktopNotificationManager, SystemMetrics, ActivityAlert
from ..ui.visual_feedback import VisualFeedbackManager


class MonitoringIntegration:
    """Intégration entre la surveillance système et l'interface utilisateur"""
    
    def __init__(self, visual_feedback_manager: VisualFeedbackManager):
        self.visual_feedback = visual_feedback_manager
        self.monitor = RealTimeMonitor(update_interval=2.0)
        self.notification_manager = DesktopNotificationManager()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.enable_notifications = True
        self.enable_visual_feedback = True
        self.notification_cooldown = 300  # 5 minutes entre notifications similaires
        
        # Historique des notifications pour éviter le spam
        self.last_notifications: Dict[str, datetime] = {}
        
        # Callbacks personnalisés
        self.custom_alert_callbacks: List[Callable[[ActivityAlert], None]] = []
        self.custom_metrics_callbacks: List[Callable[[SystemMetrics], None]] = []
        
        # Configurer les callbacks du moniteur
        self.monitor.add_metrics_callback(self._on_metrics_update)
        self.monitor.add_alert_callback(self._on_alert_received)
    
    def start_monitoring(self):
        """Démarre la surveillance intégrée"""
        self.monitor.start_monitoring()
        self.logger.info("Surveillance intégrée démarrée")
    
    def stop_monitoring(self):
        """Arrête la surveillance intégrée"""
        self.monitor.stop_monitoring()
        self.logger.info("Surveillance intégrée arrêtée")
    
    def _on_metrics_update(self, metrics: SystemMetrics):
        """Gestionnaire de mise à jour des métriques"""
        try:
            # Mettre à jour l'interface visuelle
            if self.enable_visual_feedback:
                self.visual_feedback.update_system_metrics(metrics)
            
            # Appeler les callbacks personnalisés
            for callback in self.custom_metrics_callbacks:
                try:
                    callback(metrics)
                except Exception as e:
                    self.logger.error(f"Erreur dans callback métriques personnalisé: {e}")
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des métriques: {e}")
    
    def _on_alert_received(self, alert: ActivityAlert):
        """Gestionnaire de réception d'alerte"""
        try:
            # Vérifier le cooldown pour éviter le spam
            alert_key = f"{alert.alert_type}_{alert.severity}"
            now = datetime.now()
            
            if alert_key in self.last_notifications:
                time_since_last = (now - self.last_notifications[alert_key]).total_seconds()
                if time_since_last < self.notification_cooldown:
                    return  # Ignorer l'alerte (trop récente)
            
            self.last_notifications[alert_key] = now
            
            # Envoyer notification desktop
            if self.enable_notifications:
                self.notification_manager.send_alert_notification(alert)
            
            # Mettre à jour l'interface visuelle
            if self.enable_visual_feedback:
                self.visual_feedback.update_system_alerts([alert])
                
                # Ajouter à l'historique d'activité
                self.visual_feedback.add_activity_message(
                    alert.alert_type, alert.severity, alert.message
                )
            
            # Appeler les callbacks personnalisés
            for callback in self.custom_alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Erreur dans callback alerte personnalisé: {e}")
            
            self.logger.info(f"Alerte {alert.severity}: {alert.message}")
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de l'alerte: {e}")
    
    def add_custom_alert_callback(self, callback: Callable[[ActivityAlert], None]):
        """Ajoute un callback personnalisé pour les alertes"""
        self.custom_alert_callbacks.append(callback)
    
    def add_custom_metrics_callback(self, callback: Callable[[SystemMetrics], None]):
        """Ajoute un callback personnalisé pour les métriques"""
        self.custom_metrics_callbacks.append(callback)
    
    def get_current_system_status(self) -> Dict:
        """Obtient l'état actuel du système"""
        metrics = self.monitor.get_current_metrics()
        summary = self.monitor.get_system_summary()
        
        status = {
            'monitoring_active': self.monitor.is_monitoring,
            'system_under_stress': self.monitor.is_system_under_stress(),
            'current_metrics': metrics,
            'system_summary': summary,
            'recent_alerts': len([
                alert for alert in self.last_notifications.keys()
                if (datetime.now() - self.last_notifications[alert]).total_seconds() < 3600
            ])
        }
        
        return status
    
    def get_metrics_history(self, duration_minutes: int = 60) -> List[SystemMetrics]:
        """Obtient l'historique des métriques"""
        return self.monitor.get_metrics_history(duration_minutes)
    
    def get_resource_intensive_processes(self, limit: int = 10) -> List[Dict]:
        """Obtient les processus les plus gourmands"""
        return self.monitor.get_resource_intensive_processes(limit)
    
    def configure_alert_thresholds(self, thresholds: Dict[str, Dict[str, float]]):
        """Configure les seuils d'alerte"""
        self.monitor.set_alert_thresholds(thresholds)
        self.logger.info("Seuils d'alerte mis à jour")
    
    def configure_notifications(self, enabled: bool, cooldown_seconds: int = 300):
        """Configure les notifications"""
        self.enable_notifications = enabled
        self.notification_cooldown = cooldown_seconds
        self.logger.info(f"Notifications {'activées' if enabled else 'désactivées'}")
    
    def configure_visual_feedback(self, enabled: bool):
        """Configure le feedback visuel"""
        self.enable_visual_feedback = enabled
        self.logger.info(f"Feedback visuel {'activé' if enabled else 'désactivé'}")
    
    def trigger_manual_scan(self) -> Dict:
        """Déclenche un scan manuel du système"""
        try:
            # Collecter les métriques actuelles
            metrics = self.monitor.get_current_metrics()
            if not metrics:
                return {'error': 'Impossible de collecter les métriques'}
            
            # Analyser les processus gourmands
            intensive_processes = self.get_resource_intensive_processes(5)
            
            # Obtenir le résumé système
            system_summary = self.monitor.get_system_summary()
            
            # Vérifier l'état de stress
            under_stress = self.monitor.is_system_under_stress()
            
            # Créer un rapport
            report = {
                'timestamp': datetime.now().isoformat(),
                'metrics': {
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'disk_usage_percent': metrics.disk_usage_percent,
                    'process_count': metrics.process_count,
                    'load_average': metrics.load_average
                },
                'system_summary': system_summary,
                'under_stress': under_stress,
                'intensive_processes': intensive_processes,
                'recommendations': self._generate_recommendations(metrics, intensive_processes, under_stress)
            }
            
            # Ajouter à l'historique d'activité
            if self.enable_visual_feedback:
                self.visual_feedback.add_activity_message(
                    'manual_scan', 'low', 
                    f"Scan manuel effectué - CPU: {metrics.cpu_percent:.1f}%, RAM: {metrics.memory_percent:.1f}%"
                )
            
            return report
        
        except Exception as e:
            self.logger.error(f"Erreur lors du scan manuel: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, metrics: SystemMetrics, 
                                intensive_processes: List[Dict], 
                                under_stress: bool) -> List[str]:
        """Génère des recommandations basées sur l'état du système"""
        recommendations = []
        
        # Recommandations CPU
        if metrics.cpu_percent > 80:
            recommendations.append("Utilisation CPU élevée - considérez fermer des applications non essentielles")
            if intensive_processes:
                top_cpu_process = max(intensive_processes, key=lambda p: p.get('cpu_percent', 0))
                recommendations.append(f"Processus gourmand détecté: {top_cpu_process.get('name', 'inconnu')}")
        
        # Recommandations mémoire
        if metrics.memory_percent > 85:
            recommendations.append("Utilisation mémoire élevée - redémarrage recommandé ou fermeture d'applications")
            if intensive_processes:
                top_memory_process = max(intensive_processes, key=lambda p: p.get('memory_percent', 0))
                recommendations.append(f"Processus consommant beaucoup de mémoire: {top_memory_process.get('name', 'inconnu')}")
        
        # Recommandations disque
        if metrics.disk_usage_percent > 90:
            recommendations.append("Espace disque critique - nettoyage urgent recommandé")
        elif metrics.disk_usage_percent > 80:
            recommendations.append("Espace disque faible - nettoyage recommandé")
        
        # Recommandations générales
        if under_stress:
            recommendations.append("Système sous stress - redémarrage recommandé après sauvegarde")
        
        if len(intensive_processes) > 3:
            recommendations.append("Nombreux processus actifs - vérifiez les applications en arrière-plan")
        
        # Recommandations de maintenance
        if not recommendations:  # Système en bon état
            recommendations.append("Système en bon état - maintenance préventive recommandée")
        
        return recommendations
    
    def export_monitoring_data(self, duration_hours: int = 24) -> Dict:
        """Exporte les données de surveillance"""
        try:
            # Obtenir l'historique des métriques
            metrics_history = self.get_metrics_history(duration_hours * 60)
            
            # Calculer des statistiques
            if metrics_history:
                cpu_values = [m.cpu_percent for m in metrics_history]
                memory_values = [m.memory_percent for m in metrics_history]
                disk_values = [m.disk_usage_percent for m in metrics_history]
                
                stats = {
                    'cpu': {
                        'avg': sum(cpu_values) / len(cpu_values),
                        'max': max(cpu_values),
                        'min': min(cpu_values)
                    },
                    'memory': {
                        'avg': sum(memory_values) / len(memory_values),
                        'max': max(memory_values),
                        'min': min(memory_values)
                    },
                    'disk': {
                        'avg': sum(disk_values) / len(disk_values),
                        'max': max(disk_values),
                        'min': min(disk_values)
                    }
                }
            else:
                stats = {}
            
            # Obtenir l'historique des notifications
            notification_history = self.notification_manager.get_notification_history()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'duration_hours': duration_hours,
                'metrics_count': len(metrics_history),
                'statistics': stats,
                'metrics_history': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'cpu_percent': m.cpu_percent,
                        'memory_percent': m.memory_percent,
                        'disk_usage_percent': m.disk_usage_percent,
                        'process_count': m.process_count,
                        'load_average': m.load_average
                    }
                    for m in metrics_history
                ],
                'notification_history': notification_history,
                'system_summary': self.monitor.get_system_summary()
            }
            
            return export_data
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export des données: {e}")
            return {'error': str(e)}
    
    def is_monitoring_active(self) -> bool:
        """Vérifie si la surveillance est active"""
        return self.monitor.is_monitoring
    
    def get_monitoring_stats(self) -> Dict:
        """Obtient les statistiques de surveillance"""
        return {
            'monitoring_active': self.is_monitoring_active(),
            'update_interval': self.monitor.update_interval,
            'metrics_history_size': len(self.monitor.metrics_history),
            'notifications_enabled': self.enable_notifications,
            'visual_feedback_enabled': self.enable_visual_feedback,
            'notification_cooldown': self.notification_cooldown,
            'recent_notifications': len(self.last_notifications),
            'custom_callbacks': {
                'alert_callbacks': len(self.custom_alert_callbacks),
                'metrics_callbacks': len(self.custom_metrics_callbacks)
            }
        }