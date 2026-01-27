# -*- coding: utf-8 -*-

import os
import time
import subprocess
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.main.realtime_monitor import DesktopNotificationManager, ActivityAlert, SystemMetrics


class TestNotificationSystem:
    """Tests pour le système de notifications"""
    
    def setup_method(self):
        self.notification_manager = DesktopNotificationManager()
    
    def test_notification_delivery_consistency(self):
        """Property: La livraison des notifications est cohérente"""
        # Test avec différents paramètres
        test_cases = [
            ("Test Title", "Test Message", "normal", 5000, "dialog-information"),
            ("Warning", "Warning message", "critical", 10000, "dialog-warning"),
            ("Info", "Info message", "low", 3000, "dialog-information"),
        ]
        
        for title, message, urgency, timeout, icon in test_cases:
            initial_count = len(self.notification_manager.notification_history)
            
            # Envoyer la notification
            success = self.notification_manager.send_notification(
                title, message, urgency, timeout, icon
            )
            
            # Vérifier que l'historique est mis à jour
            new_count = len(self.notification_manager.notification_history)
            assert new_count == initial_count + 1
            
            # Vérifier le contenu de la notification
            last_notification = self.notification_manager.notification_history[-1]
            assert last_notification['title'] == title
            assert last_notification['message'] == message
            assert last_notification['urgency'] == urgency
            assert isinstance(last_notification['timestamp'], datetime)
            assert isinstance(last_notification['success'], bool)
            
            # Le timestamp doit être récent
            time_diff = (datetime.now() - last_notification['timestamp']).total_seconds()
            assert time_diff < 5.0
    
    @given(st.text(min_size=1, max_size=100), 
           st.text(min_size=1, max_size=500),
           st.sampled_from(['low', 'normal', 'critical']))
    def test_notification_parameter_handling(self, title, message, urgency):
        """Property: Les paramètres de notification sont gérés correctement"""
        # Nettoyer les chaînes pour éviter les caractères problématiques
        clean_title = "".join(c for c in title if c.isprintable() and c not in '\n\r\t')
        clean_message = "".join(c for c in message if c.isprintable() and c not in '\n\r\t')
        
        if not clean_title or not clean_message:
            return  # Skip si les chaînes sont vides après nettoyage
        
        initial_count = len(self.notification_manager.notification_history)
        
        # Envoyer la notification
        success = self.notification_manager.send_notification(
            clean_title, clean_message, urgency
        )
        
        # Vérifier que l'historique est mis à jour
        new_count = len(self.notification_manager.notification_history)
        assert new_count == initial_count + 1
        
        # Vérifier que les paramètres sont préservés
        last_notification = self.notification_manager.notification_history[-1]
        assert last_notification['title'] == clean_title
        assert last_notification['message'] == clean_message
        assert last_notification['urgency'] == urgency
    
    def test_notification_history_size_management(self):
        """Property: La gestion de la taille de l'historique est correcte"""
        # Configurer une taille d'historique petite pour le test
        original_max_size = self.notification_manager.max_history_size
        self.notification_manager.max_history_size = 5
        
        try:
            # Envoyer plus de notifications que la taille maximale
            for i in range(10):
                self.notification_manager.send_notification(
                    f"Title {i}", f"Message {i}", "normal"
                )
            
            # Vérifier que la taille est respectée
            history_size = len(self.notification_manager.notification_history)
            assert history_size <= self.notification_manager.max_history_size
            
            # Vérifier que les notifications les plus récentes sont conservées
            if self.notification_manager.notification_history:
                last_notification = self.notification_manager.notification_history[-1]
                assert "Title 9" in last_notification['title']  # Dernière notification
        
        finally:
            self.notification_manager.max_history_size = original_max_size
    
    def test_alert_notification_mapping_accuracy(self):
        """Property: Le mapping des alertes vers les notifications est précis"""
        # Tester tous les types d'alertes et sévérités
        alert_types = ['cpu_percent', 'memory_percent', 'disk_usage_percent', 'disk_io_rate', 'unusual_process']
        severities = ['low', 'medium', 'high', 'critical']
        
        for alert_type in alert_types:
            for severity in severities:
                # Créer une alerte de test
                test_alert = ActivityAlert(
                    alert_type=alert_type,
                    severity=severity,
                    message=f"Test {alert_type} {severity}",
                    timestamp=datetime.now(),
                    metrics=SystemMetrics(
                        timestamp=datetime.now(),
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
                )
                
                initial_count = len(self.notification_manager.notification_history)
                
                # Envoyer la notification d'alerte
                success = self.notification_manager.send_alert_notification(test_alert)
                
                # Vérifier que l'historique est mis à jour
                new_count = len(self.notification_manager.notification_history)
                assert new_count == initial_count + 1
                
                # Vérifier le mapping de sévérité
                last_notification = self.notification_manager.notification_history[-1]
                
                expected_urgency = {
                    'low': 'low',
                    'medium': 'normal',
                    'high': 'critical',
                    'critical': 'critical'
                }[severity]
                
                assert last_notification['urgency'] == expected_urgency
                
                # Vérifier que le titre contient la sévérité
                assert severity.upper() in last_notification['title']
                
                # Vérifier que le message est préservé
                assert test_alert.message in last_notification['message']
    
    def test_notification_command_construction(self):
        """Property: La construction des commandes de notification est correcte"""
        # Mock subprocess.run pour capturer les commandes
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Envoyer une notification
            self.notification_manager.send_notification(
                "Test Title", "Test Message", "normal", 5000, "dialog-information"
            )
            
            # Vérifier que subprocess.run a été appelé
            if self.notification_manager.libnotify_available:
                mock_run.assert_called_once()
                
                # Vérifier la structure de la commande
                call_args = mock_run.call_args[0][0]  # Premier argument (la commande)
                assert call_args[0] == 'notify-send'
                assert '--urgency' in call_args
                assert 'normal' in call_args
                assert '--expire-time' in call_args
                assert '5000' in call_args
                assert '--icon' in call_args
                assert 'dialog-information' in call_args
                assert 'Test Title' in call_args
                assert 'Test Message' in call_args
    
    def test_libnotify_availability_detection(self):
        """Property: La détection de libnotify est correcte"""
        # Test avec libnotify disponible
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            manager = DesktopNotificationManager()
            assert manager._check_libnotify() is True
        
        # Test avec libnotify non disponible
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            manager = DesktopNotificationManager()
            assert manager._check_libnotify() is False
        
        # Test avec exception
        with patch('subprocess.run', side_effect=FileNotFoundError):
            manager = DesktopNotificationManager()
            assert manager._check_libnotify() is False
    
    def test_notification_timeout_handling(self):
        """Property: La gestion des timeouts est correcte"""
        # Test avec différents timeouts
        timeouts = [1000, 5000, 10000, 0, -1]  # Inclure des valeurs limites
        
        for timeout in timeouts:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                
                success = self.notification_manager.send_notification(
                    "Test", "Message", "normal", timeout
                )
                
                if self.notification_manager.libnotify_available:
                    # Vérifier que le timeout est passé correctement
                    call_args = mock_run.call_args[0][0]
                    timeout_index = call_args.index('--expire-time')
                    assert call_args[timeout_index + 1] == str(timeout)
    
    @given(st.integers(min_value=1, max_value=100))
    def test_notification_history_retrieval(self, num_notifications):
        """Property: La récupération de l'historique est cohérente"""
        # Vider l'historique
        self.notification_manager.notification_history.clear()
        
        # Envoyer un nombre variable de notifications
        for i in range(num_notifications):
            self.notification_manager.send_notification(
                f"Title {i}", f"Message {i}", "normal"
            )
        
        # Récupérer l'historique
        history = self.notification_manager.get_notification_history()
        
        # Vérifier que c'est une copie (pas la référence originale)
        assert history is not self.notification_manager.notification_history
        
        # Vérifier le contenu
        expected_size = min(num_notifications, self.notification_manager.max_history_size)
        assert len(history) == expected_size
        
        # Vérifier l'ordre (plus récent en dernier)
        if len(history) > 1:
            for i in range(len(history) - 1):
                assert history[i]['timestamp'] <= history[i + 1]['timestamp']


class NotificationSystemStateMachine(RuleBasedStateMachine):
    """Machine à états pour tester le système de notifications"""
    
    def __init__(self):
        super().__init__()
        self.notification_manager = DesktopNotificationManager()
        self.sent_notifications = []
        self.expected_history_size = 0
    
    @rule(title=st.text(min_size=1, max_size=50),
          message=st.text(min_size=1, max_size=200),
          urgency=st.sampled_from(['low', 'normal', 'critical']))
    def send_notification(self, title, message, urgency):
        """Envoyer une notification"""
        # Nettoyer les chaînes
        clean_title = "".join(c for c in title if c.isprintable() and c not in '\n\r\t')
        clean_message = "".join(c for c in message if c.isprintable() and c not in '\n\r\t')
        
        if not clean_title or not clean_message:
            return
        
        # Envoyer la notification
        success = self.notification_manager.send_notification(
            clean_title, clean_message, urgency
        )
        
        # Suivre les notifications envoyées
        self.sent_notifications.append({
            'title': clean_title,
            'message': clean_message,
            'urgency': urgency,
            'timestamp': datetime.now()
        })
        
        # Mettre à jour la taille attendue de l'historique
        self.expected_history_size = min(
            len(self.sent_notifications),
            self.notification_manager.max_history_size
        )
    
    @rule(alert_type=st.sampled_from(['cpu_percent', 'memory_percent', 'disk_usage_percent']),
          severity=st.sampled_from(['low', 'medium', 'high', 'critical']))
    def send_alert_notification(self, alert_type, severity):
        """Envoyer une notification d'alerte"""
        alert = ActivityAlert(
            alert_type=alert_type,
            severity=severity,
            message=f"Test {alert_type} alert",
            timestamp=datetime.now(),
            metrics=SystemMetrics(
                timestamp=datetime.now(),
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
        )
        
        success = self.notification_manager.send_alert_notification(alert)
        
        # Suivre les notifications envoyées
        self.sent_notifications.append({
            'title': f"Alerte Système - {severity.upper()}",
            'message': alert.message,
            'urgency': {'low': 'low', 'medium': 'normal', 'high': 'critical', 'critical': 'critical'}[severity],
            'timestamp': datetime.now()
        })
        
        self.expected_history_size = min(
            len(self.sent_notifications),
            self.notification_manager.max_history_size
        )
    
    @rule()
    def get_notification_history(self):
        """Récupérer l'historique des notifications"""
        history = self.notification_manager.get_notification_history()
        
        # Vérifier que c'est une copie
        assert history is not self.notification_manager.notification_history
        
        # Vérifier la taille
        assert len(history) == self.expected_history_size
    
    @invariant()
    def history_size_is_consistent(self):
        """Invariant: La taille de l'historique est cohérente"""
        actual_size = len(self.notification_manager.notification_history)
        assert actual_size == self.expected_history_size
        assert actual_size <= self.notification_manager.max_history_size
    
    @invariant()
    def history_entries_are_valid(self):
        """Invariant: Les entrées de l'historique sont valides"""
        for entry in self.notification_manager.notification_history:
            assert 'title' in entry
            assert 'message' in entry
            assert 'urgency' in entry
            assert 'timestamp' in entry
            assert 'success' in entry
            
            assert isinstance(entry['title'], str)
            assert isinstance(entry['message'], str)
            assert entry['urgency'] in ['low', 'normal', 'critical']
            assert isinstance(entry['timestamp'], datetime)
            assert isinstance(entry['success'], bool)
    
    @invariant()
    def history_is_chronologically_ordered(self):
        """Invariant: L'historique est ordonné chronologiquement"""
        history = self.notification_manager.notification_history
        if len(history) > 1:
            for i in range(len(history) - 1):
                assert history[i]['timestamp'] <= history[i + 1]['timestamp']


# Test de la machine à états
TestNotificationSystemStateMachine = NotificationSystemStateMachine.TestCase


class TestNotificationIntegration:
    """Tests d'intégration pour le système de notifications"""
    
    def setup_method(self):
        self.notification_manager = DesktopNotificationManager()
    
    def test_notification_system_robustness(self):
        """Property: Le système de notifications est robuste"""
        # Test avec des conditions d'erreur
        error_conditions = [
            # Commande qui échoue
            lambda: patch('subprocess.run', return_value=MagicMock(returncode=1)),
            # Timeout
            lambda: patch('subprocess.run', side_effect=subprocess.TimeoutExpired('notify-send', 10)),
            # Fichier non trouvé
            lambda: patch('subprocess.run', side_effect=FileNotFoundError),
        ]
        
        for error_condition in error_conditions:
            with error_condition():
                # Le système ne devrait pas planter
                success = self.notification_manager.send_notification(
                    "Test", "Message", "normal"
                )
                
                # L'historique devrait quand même être mis à jour
                assert len(self.notification_manager.notification_history) > 0
                
                # Le succès devrait être False en cas d'erreur
                last_entry = self.notification_manager.notification_history[-1]
                if not self.notification_manager.libnotify_available:
                    assert last_entry['success'] is False
    
    def test_concurrent_notification_handling(self):
        """Property: La gestion concurrente des notifications est sûre"""
        import threading
        
        results = []
        errors = []
        
        def send_notifications(thread_id):
            try:
                for i in range(10):
                    success = self.notification_manager.send_notification(
                        f"Thread {thread_id} - Notification {i}",
                        f"Message from thread {thread_id}",
                        "normal"
                    )
                    results.append((thread_id, i, success))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Lancer plusieurs threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=send_notifications, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Attendre la fin de tous les threads
        for thread in threads:
            thread.join()
        
        # Vérifier qu'il n'y a pas eu d'erreurs
        assert len(errors) == 0, f"Erreurs détectées: {errors}"
        
        # Vérifier que toutes les notifications ont été traitées
        assert len(results) == 30  # 3 threads * 10 notifications
        
        # Vérifier l'intégrité de l'historique
        history_size = len(self.notification_manager.notification_history)
        expected_size = min(30, self.notification_manager.max_history_size)
        assert history_size == expected_size


if __name__ == '__main__':
    pytest.main([__file__])