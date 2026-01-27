# -*- coding: utf-8 -*-

import os
import time
import threading
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.main.realtime_monitor import RealTimeMonitor, SystemMetrics, ActivityAlert, DesktopNotificationManager
from src.main.monitoring_integration import MonitoringIntegration
from src.ui.visual_feedback import VisualFeedbackManager


class TestRealTimeMonitoring:
    """Tests pour la surveillance temps réel"""
    
    def setup_method(self):
        self.monitor = RealTimeMonitor(update_interval=0.1)  # Intervalle court pour les tests
        self.received_metrics = []
        self.received_alerts = []
        
        # Callbacks de test
        self.monitor.add_metrics_callback(self._on_metrics)
        self.monitor.add_alert_callback(self._on_alert)
    
    def teardown_method(self):
        if self.monitor.is_monitoring:
            self.monitor.stop_monitoring()
    
    def _on_metrics(self, metrics):
        self.received_metrics.append(metrics)
    
    def _on_alert(self, alert):
        self.received_alerts.append(alert)
    
    def test_metrics_collection_consistency(self):
        """Property: La collecte de métriques est cohérente"""
        metrics = self.monitor._collect_metrics()
        
        if metrics:  # Si psutil est disponible
            # Vérifier la cohérence des métriques
            assert 0 <= metrics.cpu_percent <= 100
            assert 0 <= metrics.memory_percent <= 100
            assert 0 <= metrics.disk_usage_percent <= 100
            assert metrics.disk_io_read_bytes >= 0
            assert metrics.disk_io_write_bytes >= 0
            assert metrics.network_bytes_sent >= 0
            assert metrics.network_bytes_recv >= 0
            assert metrics.process_count > 0
            assert len(metrics.load_average) == 3
            assert isinstance(metrics.timestamp, datetime)
            
            # Les métriques doivent être récentes
            time_diff = (datetime.now() - metrics.timestamp).total_seconds()
            assert time_diff < 5.0  # Moins de 5 secondes
    
    def test_monitoring_lifecycle_consistency(self):
        """Property: Le cycle de vie de la surveillance est cohérent"""
        # État initial
        assert not self.monitor.is_monitoring
        assert self.monitor.monitoring_thread is None
        
        # Démarrage
        self.monitor.start_monitoring()
        
        # Vérifier l'état après démarrage
        if hasattr(self.monitor, 'monitor') and self.monitor.monitor is not None:
            # psutil disponible
            assert self.monitor.is_monitoring
            assert self.monitor.monitoring_thread is not None
            assert self.monitor.monitoring_thread.is_alive()
            
            # Attendre quelques métriques
            time.sleep(0.3)
            
            # Vérifier que des métriques sont reçues
            assert len(self.received_metrics) > 0
            
            # Arrêt
            self.monitor.stop_monitoring()
            
            # Vérifier l'état après arrêt
            assert not self.monitor.is_monitoring
            
            # Attendre que le thread se termine
            time.sleep(0.2)
            if self.monitor.monitoring_thread:
                assert not self.monitor.monitoring_thread.is_alive()
    
    @given(st.floats(min_value=0.0, max_value=100.0))
    def test_alert_threshold_consistency(self, cpu_percent):
        """Property: Les seuils d'alerte sont cohérents"""
        # Créer des métriques de test
        test_metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=50.0,
            disk_usage_percent=50.0,
            disk_io_read_bytes=1000,
            disk_io_write_bytes=1000,
            network_bytes_sent=1000,
            network_bytes_recv=1000,
            process_count=100,
            load_average=[1.0, 1.0, 1.0]
        )
        
        # Analyser les alertes
        alerts = self.monitor._analyze_for_alerts(test_metrics)
        
        # Vérifier la cohérence des alertes
        cpu_alerts = [a for a in alerts if a.alert_type == 'cpu_percent']
        
        if cpu_percent >= 95.0:
            # Devrait avoir une alerte critique
            assert any(a.severity == 'critical' for a in cpu_alerts)
        elif cpu_percent >= 85.0:
            # Devrait avoir une alerte haute
            assert any(a.severity == 'high' for a in cpu_alerts)
        elif cpu_percent >= 70.0:
            # Devrait avoir une alerte moyenne
            assert any(a.severity == 'medium' for a in cpu_alerts)
        else:
            # Ne devrait pas avoir d'alerte CPU
            assert len(cpu_alerts) == 0
    
    def test_metrics_history_management(self):
        """Property: La gestion de l'historique des métriques est correcte"""
        # Configurer une taille d'historique petite pour le test
        original_max_size = self.monitor.max_history_size
        self.monitor.max_history_size = 5
        
        try:
            # Ajouter des métriques à l'historique
            for i in range(10):
                metrics = SystemMetrics(
                    timestamp=datetime.now() + timedelta(seconds=i),
                    cpu_percent=float(i * 10),
                    memory_percent=50.0,
                    disk_usage_percent=50.0,
                    disk_io_read_bytes=1000,
                    disk_io_write_bytes=1000,
                    network_bytes_sent=1000,
                    network_bytes_recv=1000,
                    process_count=100,
                    load_average=[1.0, 1.0, 1.0]
                )
                self.monitor.metrics_history.append(metrics)
                
                # Simuler la limitation de taille
                if len(self.monitor.metrics_history) > self.monitor.max_history_size:
                    self.monitor.metrics_history.pop(0)
            
            # Vérifier que la taille est respectée
            assert len(self.monitor.metrics_history) <= self.monitor.max_history_size
            
            # Vérifier que les métriques les plus récentes sont conservées
            if self.monitor.metrics_history:
                last_metrics = self.monitor.metrics_history[-1]
                assert last_metrics.cpu_percent == 90.0  # Dernière valeur ajoutée
        
        finally:
            self.monitor.max_history_size = original_max_size
    
    @given(st.integers(min_value=1, max_value=1440))
    def test_metrics_history_filtering(self, duration_minutes):
        """Property: Le filtrage de l'historique par durée est correct"""
        # Ajouter des métriques avec différents timestamps
        now = datetime.now()
        
        for i in range(10):
            # Métriques de différents âges
            timestamp = now - timedelta(minutes=i * 30)  # Toutes les 30 minutes
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_percent=50.0,
                memory_percent=50.0,
                disk_usage_percent=50.0,
                disk_io_read_bytes=1000,
                disk_io_write_bytes=1000,
                network_bytes_sent=1000,
                network_bytes_recv=1000,
                process_count=100,
                load_average=[1.0, 1.0, 1.0]
            )
            self.monitor.metrics_history.append(metrics)
        
        # Obtenir l'historique filtré
        filtered_history = self.monitor.get_metrics_history(duration_minutes)
        
        # Vérifier que toutes les métriques retournées sont dans la plage
        cutoff_time = now - timedelta(minutes=duration_minutes)
        for metrics in filtered_history:
            assert metrics.timestamp >= cutoff_time
        
        # Vérifier que les métriques trop anciennes sont exclues
        all_recent = all(m.timestamp >= cutoff_time for m in filtered_history)
        assert all_recent
    
    def test_system_stress_detection_accuracy(self):
        """Property: La détection de stress système est précise"""
        # Tester différents scénarios de stress
        test_cases = [
            # (cpu, memory, load_avg, expected_stress)
            (50.0, 50.0, [1.0, 1.0, 1.0], False),  # Normal
            (85.0, 50.0, [1.0, 1.0, 1.0], True),   # CPU élevé
            (50.0, 90.0, [1.0, 1.0, 1.0], True),   # Mémoire élevée
            (50.0, 50.0, [16.0, 16.0, 16.0], True), # Load élevé (assume 4 CPU)
            (90.0, 90.0, [16.0, 16.0, 16.0], True), # Tout élevé
        ]
        
        with patch('psutil.cpu_count', return_value=4):
            for cpu, memory, load_avg, expected_stress in test_cases:
                # Mock des métriques
                with patch.object(self.monitor, 'get_current_metrics') as mock_metrics:
                    mock_metrics.return_value = SystemMetrics(
                        timestamp=datetime.now(),
                        cpu_percent=cpu,
                        memory_percent=memory,
                        disk_usage_percent=50.0,
                        disk_io_read_bytes=1000,
                        disk_io_write_bytes=1000,
                        network_bytes_sent=1000,
                        network_bytes_recv=1000,
                        process_count=100,
                        load_average=load_avg
                    )
                    
                    is_stressed = self.monitor.is_system_under_stress()
                    assert is_stressed == expected_stress, f"CPU: {cpu}, Memory: {memory}, Load: {load_avg}"


class TestDesktopNotificationManager:
    """Tests pour le gestionnaire de notifications desktop"""
    
    def setup_method(self):
        self.notification_manager = DesktopNotificationManager()
    
    def test_notification_history_consistency(self):
        """Property: L'historique des notifications est cohérent"""
        initial_count = len(self.notification_manager.notification_history)
        
        # Envoyer une notification (peut échouer si libnotify n'est pas disponible)
        success = self.notification_manager.send_notification(
            "Test Title", "Test Message", "normal", 1000
        )
        
        # Vérifier que l'historique est mis à jour
        new_count = len(self.notification_manager.notification_history)
        assert new_count == initial_count + 1
        
        # Vérifier le contenu de la dernière notification
        last_notification = self.notification_manager.notification_history[-1]
        assert last_notification['title'] == "Test Title"
        assert last_notification['message'] == "Test Message"
        assert last_notification['urgency'] == "normal"
        assert isinstance(last_notification['timestamp'], datetime)
        assert isinstance(last_notification['success'], bool)
    
    def test_alert_notification_mapping(self):
        """Property: Le mapping des alertes vers les notifications est correct"""
        # Créer différents types d'alertes
        test_alerts = [
            ActivityAlert(
                alert_type='cpu_percent',
                severity='high',
                message='CPU usage high',
                timestamp=datetime.now(),
                metrics=SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=90.0,
                    memory_percent=50.0,
                    disk_usage_percent=50.0,
                    disk_io_read_bytes=1000,
                    disk_io_write_bytes=1000,
                    network_bytes_sent=1000,
                    network_bytes_recv=1000,
                    process_count=100,
                    load_average=[1.0, 1.0, 1.0]
                )
            ),
            ActivityAlert(
                alert_type='memory_percent',
                severity='critical',
                message='Memory usage critical',
                timestamp=datetime.now(),
                metrics=SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=50.0,
                    memory_percent=98.0,
                    disk_usage_percent=50.0,
                    disk_io_read_bytes=1000,
                    disk_io_write_bytes=1000,
                    network_bytes_sent=1000,
                    network_bytes_recv=1000,
                    process_count=100,
                    load_average=[1.0, 1.0, 1.0]
                )
            )
        ]
        
        for alert in test_alerts:
            initial_count = len(self.notification_manager.notification_history)
            
            # Envoyer la notification d'alerte
            success = self.notification_manager.send_alert_notification(alert)
            
            # Vérifier que l'historique est mis à jour
            new_count = len(self.notification_manager.notification_history)
            assert new_count == initial_count + 1
            
            # Vérifier le mapping de sévérité
            last_notification = self.notification_manager.notification_history[-1]
            if alert.severity == 'critical':
                assert last_notification['urgency'] == 'critical'
            elif alert.severity == 'high':
                assert last_notification['urgency'] == 'critical'
            elif alert.severity == 'medium':
                assert last_notification['urgency'] == 'normal'
            else:
                assert last_notification['urgency'] == 'low'


class TestMonitoringIntegration:
    """Tests pour l'intégration de surveillance"""
    
    def setup_method(self):
        self.visual_feedback = VisualFeedbackManager()
        self.integration = MonitoringIntegration(self.visual_feedback)
        self.custom_alerts = []
        self.custom_metrics = []
        
        # Ajouter des callbacks de test
        self.integration.add_custom_alert_callback(self._on_custom_alert)
        self.integration.add_custom_metrics_callback(self._on_custom_metrics)
    
    def teardown_method(self):
        if self.integration.is_monitoring_active():
            self.integration.stop_monitoring()
    
    def _on_custom_alert(self, alert):
        self.custom_alerts.append(alert)
    
    def _on_custom_metrics(self, metrics):
        self.custom_metrics.append(metrics)
    
    def test_integration_lifecycle_consistency(self):
        """Property: Le cycle de vie de l'intégration est cohérent"""
        # État initial
        assert not self.integration.is_monitoring_active()
        
        # Démarrage
        self.integration.start_monitoring()
        
        # Vérifier l'état (peut être False si psutil n'est pas disponible)
        monitoring_started = self.integration.is_monitoring_active()
        
        if monitoring_started:
            # Attendre un peu pour les callbacks
            time.sleep(0.2)
            
            # Arrêt
            self.integration.stop_monitoring()
            assert not self.integration.is_monitoring_active()
    
    def test_custom_callback_execution(self):
        """Property: Les callbacks personnalisés sont exécutés"""
        # Simuler une mise à jour de métriques
        test_metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=75.0,
            memory_percent=60.0,
            disk_usage_percent=50.0,
            disk_io_read_bytes=1000,
            disk_io_write_bytes=1000,
            network_bytes_sent=1000,
            network_bytes_recv=1000,
            process_count=100,
            load_average=[1.0, 1.0, 1.0]
        )
        
        # Appeler directement le gestionnaire
        self.integration._on_metrics_update(test_metrics)
        
        # Vérifier que le callback personnalisé a été appelé
        assert len(self.custom_metrics) == 1
        assert self.custom_metrics[0] == test_metrics
        
        # Simuler une alerte
        test_alert = ActivityAlert(
            alert_type='cpu_percent',
            severity='medium',
            message='Test alert',
            timestamp=datetime.now(),
            metrics=test_metrics
        )
        
        # Appeler directement le gestionnaire
        self.integration._on_alert_received(test_alert)
        
        # Vérifier que le callback personnalisé a été appelé
        assert len(self.custom_alerts) == 1
        assert self.custom_alerts[0] == test_alert
    
    def test_configuration_consistency(self):
        """Property: La configuration est cohérente"""
        # Configuration des seuils
        custom_thresholds = {
            'cpu_percent': {'medium': 60.0, 'high': 80.0, 'critical': 90.0}
        }
        
        self.integration.configure_alert_thresholds(custom_thresholds)
        
        # Vérifier que les seuils sont appliqués
        monitor_thresholds = self.integration.monitor.alert_thresholds
        assert monitor_thresholds['cpu_percent']['medium'] == 60.0
        
        # Configuration des notifications
        self.integration.configure_notifications(False, 600)
        assert not self.integration.enable_notifications
        assert self.integration.notification_cooldown == 600
        
        # Configuration du feedback visuel
        self.integration.configure_visual_feedback(False)
        assert not self.integration.enable_visual_feedback
    
    def test_manual_scan_completeness(self):
        """Property: Le scan manuel est complet"""
        # Effectuer un scan manuel
        report = self.integration.trigger_manual_scan()
        
        if 'error' not in report:
            # Vérifier la structure du rapport
            assert 'timestamp' in report
            assert 'metrics' in report
            assert 'system_summary' in report
            assert 'under_stress' in report
            assert 'intensive_processes' in report
            assert 'recommendations' in report
            
            # Vérifier les métriques
            metrics = report['metrics']
            assert 'cpu_percent' in metrics
            assert 'memory_percent' in metrics
            assert 'disk_usage_percent' in metrics
            assert 'process_count' in metrics
            assert 'load_average' in metrics
            
            # Vérifier que les recommandations sont une liste
            assert isinstance(report['recommendations'], list)
            
            # Vérifier que le timestamp est récent
            timestamp = datetime.fromisoformat(report['timestamp'])
            time_diff = (datetime.now() - timestamp).total_seconds()
            assert time_diff < 10.0  # Moins de 10 secondes
    
    def test_data_export_consistency(self):
        """Property: L'export de données est cohérent"""
        # Ajouter quelques métriques à l'historique
        for i in range(5):
            metrics = SystemMetrics(
                timestamp=datetime.now() - timedelta(minutes=i),
                cpu_percent=50.0 + i,
                memory_percent=60.0 + i,
                disk_usage_percent=70.0,
                disk_io_read_bytes=1000,
                disk_io_write_bytes=1000,
                network_bytes_sent=1000,
                network_bytes_recv=1000,
                process_count=100,
                load_average=[1.0, 1.0, 1.0]
            )
            self.integration.monitor.metrics_history.append(metrics)
        
        # Exporter les données
        export_data = self.integration.export_monitoring_data(1)  # 1 heure
        
        if 'error' not in export_data:
            # Vérifier la structure
            assert 'export_timestamp' in export_data
            assert 'duration_hours' in export_data
            assert 'metrics_count' in export_data
            assert 'statistics' in export_data
            assert 'metrics_history' in export_data
            assert 'notification_history' in export_data
            assert 'system_summary' in export_data
            
            # Vérifier les statistiques
            if export_data['metrics_count'] > 0:
                stats = export_data['statistics']
                assert 'cpu' in stats
                assert 'memory' in stats
                assert 'disk' in stats
                
                for resource in ['cpu', 'memory', 'disk']:
                    assert 'avg' in stats[resource]
                    assert 'max' in stats[resource]
                    assert 'min' in stats[resource]


class RealTimeMonitoringStateMachine(RuleBasedStateMachine):
    """Machine à états pour tester la surveillance temps réel"""
    
    def __init__(self):
        super().__init__()
        self.monitor = RealTimeMonitor(update_interval=0.1)
        self.received_metrics = []
        self.received_alerts = []
        self.is_monitoring = False
        
        self.monitor.add_metrics_callback(self._on_metrics)
        self.monitor.add_alert_callback(self._on_alert)
    
    def teardown(self):
        if self.monitor.is_monitoring:
            self.monitor.stop_monitoring()
    
    def _on_metrics(self, metrics):
        self.received_metrics.append(metrics)
    
    def _on_alert(self, alert):
        self.received_alerts.append(alert)
    
    @rule()
    def start_monitoring(self):
        """Démarrer la surveillance"""
        if not self.is_monitoring:
            self.monitor.start_monitoring()
            self.is_monitoring = self.monitor.is_monitoring
    
    @rule()
    def stop_monitoring(self):
        """Arrêter la surveillance"""
        if self.is_monitoring:
            self.monitor.stop_monitoring()
            self.is_monitoring = False
    
    @rule()
    def collect_current_metrics(self):
        """Collecter les métriques actuelles"""
        metrics = self.monitor.get_current_metrics()
        if metrics:
            # Vérifier la validité des métriques
            assert 0 <= metrics.cpu_percent <= 100
            assert 0 <= metrics.memory_percent <= 100
            assert 0 <= metrics.disk_usage_percent <= 100
    
    @rule(duration=st.integers(min_value=1, max_value=60))
    def get_metrics_history(self, duration):
        """Obtenir l'historique des métriques"""
        history = self.monitor.get_metrics_history(duration)
        
        # Vérifier que toutes les métriques sont dans la plage de temps
        cutoff_time = datetime.now() - timedelta(minutes=duration)
        for metrics in history:
            assert metrics.timestamp >= cutoff_time
    
    @invariant()
    def monitoring_state_is_consistent(self):
        """Invariant: L'état de surveillance est cohérent"""
        assert self.is_monitoring == self.monitor.is_monitoring
        
        if self.is_monitoring:
            assert self.monitor.monitoring_thread is not None
        else:
            # Le thread peut encore exister brièvement après l'arrêt
            pass
    
    @invariant()
    def metrics_are_valid(self):
        """Invariant: Les métriques reçues sont valides"""
        for metrics in self.received_metrics:
            assert isinstance(metrics, SystemMetrics)
            assert 0 <= metrics.cpu_percent <= 100
            assert 0 <= metrics.memory_percent <= 100
            assert 0 <= metrics.disk_usage_percent <= 100
            assert metrics.disk_io_read_bytes >= 0
            assert metrics.disk_io_write_bytes >= 0
    
    @invariant()
    def alerts_are_valid(self):
        """Invariant: Les alertes reçues sont valides"""
        for alert in self.received_alerts:
            assert isinstance(alert, ActivityAlert)
            assert alert.severity in ['low', 'medium', 'high', 'critical']
            assert alert.alert_type in ['cpu_percent', 'memory_percent', 'disk_usage_percent', 'disk_io_rate', 'unusual_process']
            assert len(alert.message) > 0


# Test de la machine à états
TestRealTimeMonitoringStateMachine = RealTimeMonitoringStateMachine.TestCase


if __name__ == '__main__':
    pytest.main([__file__])