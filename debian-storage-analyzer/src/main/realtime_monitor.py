# -*- coding: utf-8 -*-

import os
import time
import threading
import subprocess
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import json

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class SystemMetrics:
    """Métriques système en temps réel"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    disk_io_read_bytes: int
    disk_io_write_bytes: int
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: List[float]


@dataclass
class ActivityAlert:
    """Alerte d'activité inhabituelle"""
    alert_type: str  # 'high_cpu', 'high_memory', 'high_disk_io', 'unusual_process'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    timestamp: datetime
    metrics: SystemMetrics
    process_info: Optional[Dict] = None


class RealTimeMonitor:
    """Moniteur système temps réel"""
    
    def __init__(self, update_interval: float = 2.0):
        self.update_interval = update_interval
        self.is_monitoring = False
        self.monitoring_thread = None
        self.logger = logging.getLogger(__name__)
        
        # Callbacks pour les mises à jour
        self.metrics_callbacks: List[Callable[[SystemMetrics], None]] = []
        self.alert_callbacks: List[Callable[[ActivityAlert], None]] = []
        
        # Historique des métriques
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000
        
        # Configuration des seuils d'alerte
        self.alert_thresholds = {
            'cpu_percent': {'medium': 70.0, 'high': 85.0, 'critical': 95.0},
            'memory_percent': {'medium': 75.0, 'high': 90.0, 'critical': 98.0},
            'disk_usage_percent': {'medium': 80.0, 'high': 90.0, 'critical': 95.0},
            'disk_io_rate': {'medium': 50 * 1024 * 1024, 'high': 100 * 1024 * 1024, 'critical': 200 * 1024 * 1024}  # bytes/sec
        }
        
        # État précédent pour calculer les deltas
        self.previous_metrics: Optional[SystemMetrics] = None
        self.previous_disk_io = None
        self.previous_network_io = None
        
        # Processus suspects
        self.suspicious_processes: Dict[int, Dict] = {}
        
        # Vérifier la disponibilité de psutil
        if psutil is None:
            self.logger.warning("psutil non disponible - surveillance système limitée")
    
    def add_metrics_callback(self, callback: Callable[[SystemMetrics], None]):
        """Ajoute un callback pour les mises à jour de métriques"""
        self.metrics_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[ActivityAlert], None]):
        """Ajoute un callback pour les alertes"""
        self.alert_callbacks.append(callback)
    
    def start_monitoring(self):
        """Démarre la surveillance en temps réel"""
        if self.is_monitoring:
            return
        
        if psutil is None:
            self.logger.error("Impossible de démarrer la surveillance - psutil non disponible")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Surveillance système démarrée")
    
    def stop_monitoring(self):
        """Arrête la surveillance"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Surveillance système arrêtée")
    
    def _monitoring_loop(self):
        """Boucle principale de surveillance"""
        while self.is_monitoring:
            try:
                # Collecter les métriques
                metrics = self._collect_metrics()
                if metrics:
                    # Ajouter à l'historique
                    self.metrics_history.append(metrics)
                    if len(self.metrics_history) > self.max_history_size:
                        self.metrics_history.pop(0)
                    
                    # Analyser les alertes
                    alerts = self._analyze_for_alerts(metrics)
                    
                    # Notifier les callbacks
                    for callback in self.metrics_callbacks:
                        try:
                            callback(metrics)
                        except Exception as e:
                            self.logger.error(f"Erreur dans callback métriques: {e}")
                    
                    for alert in alerts:
                        for callback in self.alert_callbacks:
                            try:
                                callback(alert)
                            except Exception as e:
                                self.logger.error(f"Erreur dans callback alerte: {e}")
                    
                    self.previous_metrics = metrics
                
                time.sleep(self.update_interval)
            
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de surveillance: {e}")
                time.sleep(self.update_interval)
    
    def _collect_metrics(self) -> Optional[SystemMetrics]:
        """Collecte les métriques système"""
        if psutil is None:
            return None
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # Mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disque
            disk_usage = psutil.disk_usage('/')
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # I/O disque
            disk_io = psutil.disk_io_counters()
            disk_io_read = disk_io.read_bytes if disk_io else 0
            disk_io_write = disk_io.write_bytes if disk_io else 0
            
            # Réseau
            network_io = psutil.net_io_counters()
            network_sent = network_io.bytes_sent if network_io else 0
            network_recv = network_io.bytes_recv if network_io else 0
            
            # Processus
            process_count = len(psutil.pids())
            
            # Load average
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                load_avg = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                disk_io_read_bytes=disk_io_read,
                disk_io_write_bytes=disk_io_write,
                network_bytes_sent=network_sent,
                network_bytes_recv=network_recv,
                process_count=process_count,
                load_average=list(load_avg)
            )
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la collecte des métriques: {e}")
            return None
    
    def _analyze_for_alerts(self, metrics: SystemMetrics) -> List[ActivityAlert]:
        """Analyse les métriques pour détecter des activités inhabituelles"""
        alerts = []
        
        # Analyser CPU
        cpu_alert = self._check_threshold_alert(
            'cpu_percent', metrics.cpu_percent, 
            "Utilisation CPU élevée", metrics
        )
        if cpu_alert:
            alerts.append(cpu_alert)
        
        # Analyser mémoire
        memory_alert = self._check_threshold_alert(
            'memory_percent', metrics.memory_percent,
            "Utilisation mémoire élevée", metrics
        )
        if memory_alert:
            alerts.append(memory_alert)
        
        # Analyser disque
        disk_alert = self._check_threshold_alert(
            'disk_usage_percent', metrics.disk_usage_percent,
            "Espace disque faible", metrics
        )
        if disk_alert:
            alerts.append(disk_alert)
        
        # Analyser I/O disque
        if self.previous_metrics:
            time_delta = (metrics.timestamp - self.previous_metrics.timestamp).total_seconds()
            if time_delta > 0:
                read_rate = (metrics.disk_io_read_bytes - self.previous_metrics.disk_io_read_bytes) / time_delta
                write_rate = (metrics.disk_io_write_bytes - self.previous_metrics.disk_io_write_bytes) / time_delta
                total_io_rate = read_rate + write_rate
                
                io_alert = self._check_threshold_alert(
                    'disk_io_rate', total_io_rate,
                    f"Activité disque intense ({total_io_rate / (1024*1024):.1f} MB/s)", metrics
                )
                if io_alert:
                    alerts.append(io_alert)
        
        # Analyser les processus suspects
        process_alerts = self._analyze_suspicious_processes(metrics)
        alerts.extend(process_alerts)
        
        return alerts
    
    def _check_threshold_alert(self, metric_name: str, value: float, 
                             message_template: str, metrics: SystemMetrics) -> Optional[ActivityAlert]:
        """Vérifie si une métrique dépasse les seuils d'alerte"""
        thresholds = self.alert_thresholds.get(metric_name, {})
        
        if value >= thresholds.get('critical', float('inf')):
            severity = 'critical'
        elif value >= thresholds.get('high', float('inf')):
            severity = 'high'
        elif value >= thresholds.get('medium', float('inf')):
            severity = 'medium'
        else:
            return None
        
        message = f"{message_template}: {value:.1f}%"
        if metric_name == 'disk_io_rate':
            message = message_template  # Déjà formaté
        
        return ActivityAlert(
            alert_type=metric_name,
            severity=severity,
            message=message,
            timestamp=metrics.timestamp,
            metrics=metrics
        )
    
    def _analyze_suspicious_processes(self, metrics: SystemMetrics) -> List[ActivityAlert]:
        """Analyse les processus pour détecter des activités suspectes"""
        alerts = []
        
        if psutil is None:
            return alerts
        
        try:
            # Obtenir les processus avec forte utilisation CPU/mémoire
            high_cpu_processes = []
            high_memory_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    if info['cpu_percent'] > 20.0:  # Plus de 20% CPU
                        high_cpu_processes.append(info)
                    if info['memory_percent'] > 10.0:  # Plus de 10% mémoire
                        high_memory_processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Créer des alertes pour les processus suspects
            if high_cpu_processes:
                top_cpu = max(high_cpu_processes, key=lambda p: p['cpu_percent'])
                alerts.append(ActivityAlert(
                    alert_type='unusual_process',
                    severity='medium' if top_cpu['cpu_percent'] < 50 else 'high',
                    message=f"Processus {top_cpu['name']} utilise {top_cpu['cpu_percent']:.1f}% CPU",
                    timestamp=metrics.timestamp,
                    metrics=metrics,
                    process_info=top_cpu
                ))
            
            if high_memory_processes:
                top_memory = max(high_memory_processes, key=lambda p: p['memory_percent'])
                alerts.append(ActivityAlert(
                    alert_type='unusual_process',
                    severity='medium' if top_memory['memory_percent'] < 25 else 'high',
                    message=f"Processus {top_memory['name']} utilise {top_memory['memory_percent']:.1f}% mémoire",
                    timestamp=metrics.timestamp,
                    metrics=metrics,
                    process_info=top_memory
                ))
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse des processus: {e}")
        
        return alerts
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Obtient les métriques actuelles"""
        return self._collect_metrics()
    
    def get_metrics_history(self, duration_minutes: int = 60) -> List[SystemMetrics]:
        """Obtient l'historique des métriques pour une durée donnée"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Obtient un résumé du système"""
        if psutil is None:
            return {'error': 'psutil non disponible'}
        
        try:
            # Informations système de base
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # CPU
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Mémoire
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disques
            disk_partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_partitions.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100
                    })
                except (PermissionError, FileNotFoundError):
                    continue
            
            return {
                'uptime_seconds': uptime.total_seconds(),
                'boot_time': boot_time.isoformat(),
                'cpu': {
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'percent': swap.percent
                },
                'disks': disk_partitions
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def set_alert_thresholds(self, thresholds: Dict[str, Dict[str, float]]):
        """Configure les seuils d'alerte"""
        self.alert_thresholds.update(thresholds)
    
    def is_system_under_stress(self) -> bool:
        """Détermine si le système est sous stress"""
        metrics = self.get_current_metrics()
        if not metrics:
            return False
        
        # Critères de stress
        high_cpu = metrics.cpu_percent > 80.0
        high_memory = metrics.memory_percent > 85.0
        high_load = len(metrics.load_average) > 0 and metrics.load_average[0] > psutil.cpu_count() * 2
        
        return high_cpu or high_memory or high_load
    
    def get_resource_intensive_processes(self, limit: int = 10) -> List[Dict]:
        """Obtient les processus les plus gourmands en ressources"""
        if psutil is None:
            return []
        
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    info = proc.info
                    info['memory_mb'] = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                    processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Trier par utilisation CPU + mémoire
            processes.sort(key=lambda p: p['cpu_percent'] + p['memory_percent'], reverse=True)
            return processes[:limit]
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'obtention des processus: {e}")
            return []


class DesktopNotificationManager:
    """Gestionnaire de notifications desktop"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.notification_history: List[Dict] = []
        self.max_history_size = 100
        
        # Vérifier la disponibilité de libnotify
        self.libnotify_available = self._check_libnotify()
    
    def _check_libnotify(self) -> bool:
        """Vérifie si libnotify est disponible"""
        try:
            result = subprocess.run(['which', 'notify-send'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def send_notification(self, title: str, message: str, 
                         urgency: str = 'normal', timeout: int = 5000,
                         icon: str = 'dialog-information') -> bool:
        """Envoie une notification desktop"""
        if not self.libnotify_available:
            self.logger.warning("libnotify non disponible - notification ignorée")
            return False
        
        try:
            cmd = [
                'notify-send',
                '--urgency', urgency,
                '--expire-time', str(timeout),
                '--icon', icon,
                title,
                message
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            success = result.returncode == 0
            
            # Ajouter à l'historique
            self.notification_history.append({
                'timestamp': datetime.now(),
                'title': title,
                'message': message,
                'urgency': urgency,
                'success': success
            })
            
            if len(self.notification_history) > self.max_history_size:
                self.notification_history.pop(0)
            
            return success
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.error(f"Erreur lors de l'envoi de notification: {e}")
            return False
    
    def send_alert_notification(self, alert: ActivityAlert) -> bool:
        """Envoie une notification pour une alerte"""
        urgency_map = {
            'low': 'low',
            'medium': 'normal',
            'high': 'critical',
            'critical': 'critical'
        }
        
        icon_map = {
            'cpu_percent': 'system-monitor',
            'memory_percent': 'system-monitor',
            'disk_usage_percent': 'drive-harddisk',
            'disk_io_rate': 'drive-harddisk',
            'unusual_process': 'system-run'
        }
        
        urgency = urgency_map.get(alert.severity, 'normal')
        icon = icon_map.get(alert.alert_type, 'dialog-warning')
        
        title = f"Alerte Système - {alert.severity.upper()}"
        
        return self.send_notification(
            title=title,
            message=alert.message,
            urgency=urgency,
            timeout=10000 if alert.severity in ['high', 'critical'] else 5000,
            icon=icon
        )
    
    def get_notification_history(self) -> List[Dict]:
        """Obtient l'historique des notifications"""
        return self.notification_history.copy()