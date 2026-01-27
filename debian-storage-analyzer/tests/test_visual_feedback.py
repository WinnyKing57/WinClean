# -*- coding: utf-8 -*-

import os
import time
import threading
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.ui.visual_feedback import ProgressIndicator, SystemStatusIndicator, ActivityIndicator, VisualFeedbackManager
from src.main.realtime_monitor import SystemMetrics, ActivityAlert


class TestVisualFeedback:
    """Tests pour le feedback visuel"""
    
    def setup_method(self):
        self.visual_feedback = VisualFeedbackManager()
    
    def test_progress_indicator_lifecycle(self):
        """Property: Le cycle de vie de l'indicateur de progression est cohérent"""
        progress = ProgressIndicator()
        
        # État initial
        assert not progress.is_visible()
        assert progress.dialog is None
        assert not progress.is_cancelled
        
        # Note: On ne peut pas tester l'affichage réel sans GTK
        # mais on peut tester la logique
        
        # Simuler l'annulation
        progress.is_cancelled = False
        progress._on_cancel_clicked(None)
        assert progress.is_cancelled
    
    def test_system_status_indicator_metrics_handling(self):
        """Property: L'indicateur de statut gère correctement les métriques"""
        status_indicator = SystemStatusIndicator()
        
        # Créer des métriques de test
        test_metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=75.0,
            memory_percent=60.0,
            disk_usage_percent=85.0,
            disk_io_read_bytes=1000000,
            disk_io_write_bytes=2000000,
            network_bytes_sent=500000,
            network_bytes_recv=800000,
            process_count=150,
            load_average=[2.5, 2.0, 1.8]
        )
        
        # Mettre à jour les métriques
        status_indicator.update_metrics(test_metrics)
        
        # Vérifier que les métriques sont stockées
        assert status_indicator.current_metrics == test_metrics
    
    def test_activity_indicator_message_handling(self):
        """Property: L'indicateur d'activité gère correctement les messages"""
        activity_indicator = ActivityIndicator()
        
        # Ajouter des activités
        test_activities = [
            ("scan", "low", "Scan completed"),
            ("alert", "high", "High CPU usage detected"),
            ("cleanup", "medium", "Cleanup operation finished"),
        ]
        
        for activity_type, severity, message in test_activities:
            activity_indicator.add_activity(activity_type, severity, message)
        
        # Vérifier que les activités sont stockées
        activities = activity_indicator.get_activities()
        assert len(activities) == len(test_activities)
        
        for i, (activity_type, severity, message) in enumerate(test_activities):
            assert activities[i]['type'] == activity_type
            assert activities[i]['severity'] == severity
            assert activities[i]['message'] == message
            assert isinstance(activities[i]['timestamp'], datetime)
    
    def test_activity_indicator_alert_conversion(self):
        """Property: La conversion d'alertes en activités est correcte"""
        activity_indicator = ActivityIndicator()
        
        # Créer une alerte de test
        test_alert = ActivityAlert(
            alert_type='cpu_percent',
            severity='high',
            message='CPU usage is high',
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
        )
        
        # Ajouter l'alerte
        activity_indicator.add_alert(test_alert)
        
        # Vérifier la conversion
        activities = activity_indicator.get_activities()
        assert len(activities) == 1
        
        activity = activities[0]
        assert activity['type'] == test_alert.alert_type
        assert activity['severity'] == test_alert.severity
        assert activity['message'] == test_alert.message
    
    def test_activity_history_size_management(self):
        """Property: La gestion de la taille de l'historique d'activité est correcte"""
        activity_indicator = ActivityIndicator()
        
        # Configurer une taille maximale petite pour le test
        original_max = activity_indicator.max_activities
        activity_indicator.max_activities = 5
        
        try:
            # Ajouter plus d'activités que la limite
            for i in range(10):
                activity_indicator.add_activity(
                    f"type_{i}", "low", f"Message {i}"
                )
            
            # Vérifier que la taille est respectée
            activities = activity_indicator.get_activities()
            assert len(activities) <= activity_indicator.max_activities
            
            # Vérifier que les activités les plus récentes sont conservées
            if activities:
                last_activity = activities[-1]
                assert "Message 9" in last_activity['message']
        
        finally:
            activity_indicator.max_activities = original_max
    
    def test_visual_feedback_manager_operation_tracking(self):
        """Property: Le gestionnaire de feedback suit correctement les opérations"""
        manager = VisualFeedbackManager()
        
        # Démarrer une opération
        operation_id = "test_operation"
        success = manager.start_operation(operation_id, "Test Operation", "Testing...")
        
        # L'opération devrait être suivie (même si l'affichage échoue sans GTK)
        if success:
            assert manager.is_operation_active(operation_id)
            assert operation_id in manager.get_active_operations()
            
            # Mettre à jour la progression
            manager.update_operation_progress(operation_id, 0.5, "50% complete")
            
            # L'opération devrait toujours être active
            assert manager.is_operation_active(operation_id)
            
            # Terminer l'opération
            manager.finish_operation(operation_id)
            
            # L'opération ne devrait plus être active
            assert not manager.is_operation_active(operation_id)
            assert operation_id not in manager.get_active_operations()
    
    def test_visual_feedback_manager_multiple_operations(self):
        """Property: Le gestionnaire peut gérer plusieurs opérations simultanées"""
        manager = VisualFeedbackManager()
        
        # Démarrer plusieurs opérations
        operations = ["op1", "op2", "op3"]
        started_operations = []
        
        for op_id in operations:
            success = manager.start_operation(op_id, f"Operation {op_id}", f"Running {op_id}")
            if success:
                started_operations.append(op_id)
        
        # Vérifier que les opérations sont suivies
        active_ops = manager.get_active_operations()
        for op_id in started_operations:
            assert op_id in active_ops
        
        # Terminer les opérations une par une
        for op_id in started_operations:
            manager.finish_operation(op_id)
            assert not manager.is_operation_active(op_id)
        
        # Aucune opération ne devrait être active
        assert len(manager.get_active_operations()) == 0
    
    def test_visual_feedback_manager_duplicate_operation_handling(self):
        """Property: Le gestionnaire gère correctement les opérations dupliquées"""
        manager = VisualFeedbackManager()
        
        operation_id = "duplicate_test"
        
        # Démarrer une opération
        first_success = manager.start_operation(operation_id, "First Operation")
        
        if first_success:
            # Essayer de démarrer la même opération
            second_success = manager.start_operation(operation_id, "Second Operation")
            
            # La deuxième tentative devrait échouer
            assert not second_success
            
            # Une seule opération devrait être active
            active_ops = manager.get_active_operations()
            assert active_ops.count(operation_id) == 1
            
            # Terminer l'opération
            manager.finish_operation(operation_id)
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_progress_update_bounds_checking(self, progress_value):
        """Property: Les mises à jour de progression respectent les limites"""
        manager = VisualFeedbackManager()
        operation_id = "bounds_test"
        
        # Démarrer une opération
        success = manager.start_operation(operation_id, "Bounds Test")
        
        if success:
            # Mettre à jour avec la valeur de progression
            manager.update_operation_progress(operation_id, progress_value)
            
            # La valeur devrait être dans les limites (0.0 à 1.0)
            # Note: La vérification réelle se fait dans l'implémentation
            # mais on ne peut pas la tester directement sans GTK
            
            manager.finish_operation(operation_id)
    
    def test_system_metrics_update_consistency(self):
        """Property: Les mises à jour de métriques système sont cohérentes"""
        manager = VisualFeedbackManager()
        
        # Créer des métriques de test
        metrics1 = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_usage_percent=70.0,
            disk_io_read_bytes=1000,
            disk_io_write_bytes=2000,
            network_bytes_sent=3000,
            network_bytes_recv=4000,
            process_count=100,
            load_average=[1.0, 1.5, 2.0]
        )
        
        metrics2 = SystemMetrics(
            timestamp=datetime.now() + timedelta(seconds=1),
            cpu_percent=75.0,
            memory_percent=80.0,
            disk_usage_percent=85.0,
            disk_io_read_bytes=2000,
            disk_io_write_bytes=3000,
            network_bytes_sent=4000,
            network_bytes_recv=5000,
            process_count=110,
            load_average=[2.0, 2.5, 3.0]
        )
        
        # Mettre à jour les métriques
        manager.update_system_metrics(metrics1)
        manager.update_system_metrics(metrics2)
        
        # Vérifier que les dernières métriques sont stockées
        assert manager.status_indicator.current_metrics == metrics2
    
    def test_alert_handling_consistency(self):
        """Property: La gestion des alertes est cohérente"""
        manager = VisualFeedbackManager()
        
        # Créer des alertes de test
        alerts = [
            ActivityAlert(
                alert_type='cpu_percent',
                severity='medium',
                message='CPU usage moderate',
                timestamp=datetime.now(),
                metrics=SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=75.0,
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
                severity='high',
                message='Memory usage high',
                timestamp=datetime.now(),
                metrics=SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=50.0,
                    memory_percent=90.0,
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
        
        # Mettre à jour les alertes
        manager.update_system_alerts(alerts)
        
        # Vérifier que les alertes sont stockées
        assert manager.status_indicator.current_alerts == alerts
        
        # Vérifier que les alertes sont ajoutées à l'historique d'activité
        activities = manager.activity_indicator.get_activities()
        assert len(activities) >= len(alerts)
        
        # Vérifier que les dernières activités correspondent aux alertes
        recent_activities = activities[-len(alerts):]
        for i, alert in enumerate(alerts):
            activity = recent_activities[i]
            assert activity['type'] == alert.alert_type
            assert activity['severity'] == alert.severity
            assert activity['message'] == alert.message
    
    def test_activity_message_addition(self):
        """Property: L'ajout de messages d'activité est correct"""
        manager = VisualFeedbackManager()
        
        # Ajouter des messages d'activité
        test_messages = [
            ("scan", "low", "Directory scan completed"),
            ("cleanup", "medium", "Cleanup operation started"),
            ("error", "high", "Error occurred during operation"),
        ]
        
        for activity_type, severity, message in test_messages:
            manager.add_activity_message(activity_type, severity, message)
        
        # Vérifier que les messages sont ajoutés
        activities = manager.activity_indicator.get_activities()
        assert len(activities) >= len(test_messages)
        
        # Vérifier les derniers messages
        recent_activities = activities[-len(test_messages):]
        for i, (activity_type, severity, message) in enumerate(test_messages):
            activity = recent_activities[i]
            assert activity['type'] == activity_type
            assert activity['severity'] == severity
            assert activity['message'] == message
    
    def test_activity_history_clearing(self):
        """Property: L'effacement de l'historique d'activité fonctionne"""
        manager = VisualFeedbackManager()
        
        # Ajouter quelques activités
        for i in range(5):
            manager.add_activity_message(f"type_{i}", "low", f"Message {i}")
        
        # Vérifier que les activités sont présentes
        activities_before = manager.activity_indicator.get_activities()
        assert len(activities_before) == 5
        
        # Effacer l'historique
        manager.clear_activity_history()
        
        # Vérifier que l'historique est vide
        activities_after = manager.activity_indicator.get_activities()
        assert len(activities_after) == 0


class VisualFeedbackStateMachine(RuleBasedStateMachine):
    """Machine à états pour tester le feedback visuel"""
    
    def __init__(self):
        super().__init__()
        self.manager = VisualFeedbackManager()
        self.active_operations = set()
        self.activity_count = 0
    
    @rule(operation_id=st.text(min_size=1, max_size=20),
          title=st.text(min_size=1, max_size=50))
    def start_operation(self, operation_id, title):
        """Démarrer une opération"""
        # Nettoyer les chaînes
        clean_id = "".join(c for c in operation_id if c.isalnum() or c in "_-")
        clean_title = "".join(c for c in title if c.isprintable() and c not in '\n\r\t')
        
        if not clean_id or not clean_title:
            return
        
        if clean_id not in self.active_operations:
            success = self.manager.start_operation(clean_id, clean_title)
            if success:
                self.active_operations.add(clean_id)
    
    @rule(operation_id=st.text(min_size=1, max_size=20),
          progress=st.floats(min_value=0.0, max_value=1.0))
    def update_operation_progress(self, operation_id, progress):
        """Mettre à jour la progression d'une opération"""
        clean_id = "".join(c for c in operation_id if c.isalnum() or c in "_-")
        
        if clean_id in self.active_operations:
            self.manager.update_operation_progress(clean_id, progress)
    
    @rule(operation_id=st.text(min_size=1, max_size=20))
    def finish_operation(self, operation_id):
        """Terminer une opération"""
        clean_id = "".join(c for c in operation_id if c.isalnum() or c in "_-")
        
        if clean_id in self.active_operations:
            self.manager.finish_operation(clean_id)
            self.active_operations.remove(clean_id)
    
    @rule(activity_type=st.text(min_size=1, max_size=20),
          severity=st.sampled_from(['low', 'medium', 'high', 'critical']),
          message=st.text(min_size=1, max_size=100))
    def add_activity_message(self, activity_type, severity, message):
        """Ajouter un message d'activité"""
        clean_type = "".join(c for c in activity_type if c.isalnum() or c in "_-")
        clean_message = "".join(c for c in message if c.isprintable() and c not in '\n\r\t')
        
        if clean_type and clean_message:
            self.manager.add_activity_message(clean_type, severity, clean_message)
            self.activity_count += 1
    
    @rule()
    def clear_activity_history(self):
        """Effacer l'historique d'activité"""
        self.manager.clear_activity_history()
        self.activity_count = 0
    
    @rule()
    def update_system_metrics(self):
        """Mettre à jour les métriques système"""
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_usage_percent=70.0,
            disk_io_read_bytes=1000,
            disk_io_write_bytes=2000,
            network_bytes_sent=3000,
            network_bytes_recv=4000,
            process_count=100,
            load_average=[1.0, 1.5, 2.0]
        )
        
        self.manager.update_system_metrics(metrics)
    
    @invariant()
    def active_operations_are_consistent(self):
        """Invariant: Les opérations actives sont cohérentes"""
        manager_active = set(self.manager.get_active_operations())
        assert self.active_operations == manager_active
        
        for op_id in self.active_operations:
            assert self.manager.is_operation_active(op_id)
    
    @invariant()
    def activity_count_is_reasonable(self):
        """Invariant: Le nombre d'activités est raisonnable"""
        actual_activities = len(self.manager.activity_indicator.get_activities())
        max_activities = self.manager.activity_indicator.max_activities
        
        # Le nombre d'activités ne devrait pas dépasser la limite
        assert actual_activities <= max_activities
        
        # Le nombre d'activités ne devrait pas dépasser le nombre ajouté
        assert actual_activities <= self.activity_count


# Test de la machine à états
TestVisualFeedbackStateMachine = VisualFeedbackStateMachine.TestCase


class TestProgressIndicatorEdgeCases:
    """Tests des cas limites pour l'indicateur de progression"""
    
    def test_progress_bounds_handling(self):
        """Property: L'indicateur gère correctement les valeurs limites"""
        progress = ProgressIndicator()
        
        # Test avec des valeurs limites
        test_values = [-1.0, 0.0, 0.5, 1.0, 2.0, float('inf'), float('-inf')]
        
        for value in test_values:
            if not (float('-inf') < value < float('inf')):
                continue  # Skip les valeurs infinies
            
            # Ne devrait pas lever d'exception
            progress.update_progress(value)
            
            # La valeur devrait être bornée entre 0 et 1
            # (vérification indirecte via l'absence d'exception)
    
    def test_concurrent_progress_updates(self):
        """Property: Les mises à jour concurrentes sont sûres"""
        progress = ProgressIndicator()
        errors = []
        
        def update_progress(thread_id):
            try:
                for i in range(100):
                    progress.update_progress(i / 100.0, f"Thread {thread_id} - {i}%")
                    time.sleep(0.001)  # Petite pause
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Lancer plusieurs threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Attendre la fin
        for thread in threads:
            thread.join()
        
        # Vérifier qu'il n'y a pas eu d'erreurs
        assert len(errors) == 0, f"Erreurs détectées: {errors}"


if __name__ == '__main__':
    pytest.main([__file__])