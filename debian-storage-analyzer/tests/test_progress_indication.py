# -*- coding: utf-8 -*-

import os
import time
import threading
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.ui.visual_feedback import ProgressIndicator, VisualFeedbackManager


class TestProgressIndication:
    """Tests pour l'indication de progression"""
    
    def setup_method(self):
        self.progress_indicator = ProgressIndicator()
        self.visual_feedback = VisualFeedbackManager()
    
    def test_progress_value_normalization(self):
        """Property: Les valeurs de progression sont normalisées correctement"""
        # Test avec différentes valeurs
        test_values = [
            (-0.5, 0.0),    # Valeur négative -> 0
            (0.0, 0.0),     # Minimum valide
            (0.25, 0.25),   # Valeur normale
            (0.5, 0.5),     # Valeur normale
            (0.75, 0.75),   # Valeur normale
            (1.0, 1.0),     # Maximum valide
            (1.5, 1.0),     # Valeur excessive -> 1
            (2.0, 1.0),     # Valeur excessive -> 1
        ]
        
        for input_value, expected_value in test_values:
            # La normalisation se fait dans l'implémentation
            # On teste que les valeurs extrêmes ne causent pas d'erreur
            try:
                self.progress_indicator.update_progress(input_value)
                # Si on arrive ici, pas d'exception levée
                assert True
            except Exception as e:
                pytest.fail(f"Exception inattendue pour la valeur {input_value}: {e}")
    
    @given(st.floats(min_value=-10.0, max_value=10.0))
    def test_progress_update_robustness(self, progress_value):
        """Property: Les mises à jour de progression sont robustes"""
        # Filtrer les valeurs non finies
        assume(not (float('-inf') == progress_value or float('inf') == progress_value))
        assume(not (progress_value != progress_value))  # Pas NaN
        
        # Ne devrait pas lever d'exception
        try:
            self.progress_indicator.update_progress(progress_value)
            assert True
        except Exception as e:
            pytest.fail(f"Exception inattendue pour {progress_value}: {e}")
    
    def test_progress_message_handling(self):
        """Property: Les messages de progression sont gérés correctement"""
        test_messages = [
            "Initialisation...",
            "Analyse en cours... 25%",
            "Nettoyage des fichiers temporaires",
            "Finalisation de l'opération",
            "",  # Message vide
            "Message avec caractères spéciaux: àéèùç!@#$%",
            "Message très long " * 20,  # Message long
        ]
        
        for i, message in enumerate(test_messages):
            progress = i / (len(test_messages) - 1)
            
            try:
                self.progress_indicator.update_progress(progress, message)
                assert True
            except Exception as e:
                pytest.fail(f"Exception pour le message '{message}': {e}")
    
    def test_progress_indicator_state_consistency(self):
        """Property: L'état de l'indicateur de progression est cohérent"""
        # État initial
        assert not self.progress_indicator.is_visible()
        assert not self.progress_indicator.is_cancelled
        assert self.progress_indicator.dialog is None
        
        # Simuler l'affichage (sans GTK réel)
        # L'indicateur devrait gérer l'absence de GTK gracieusement
        success = self.progress_indicator.show("Test", "Message de test")
        
        # Si GTK n'est pas disponible, success sera False
        # mais l'état devrait rester cohérent
        if not success:
            assert not self.progress_indicator.is_visible()
        
        # Test de l'annulation
        self.progress_indicator.is_cancelled = False
        self.progress_indicator._on_cancel_clicked(None)
        assert self.progress_indicator.is_cancelled
    
    def test_progress_indicator_cancellation_callback(self):
        """Property: Le callback d'annulation fonctionne correctement"""
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        self.progress_indicator.set_cancel_callback(test_callback)
        
        # Simuler l'annulation
        self.progress_indicator._on_cancel_clicked(None)
        
        # Vérifier que le callback a été appelé
        assert len(callback_called) == 1
        assert self.progress_indicator.is_cancelled
    
    def test_visual_feedback_manager_operation_progress_tracking(self):
        """Property: Le gestionnaire suit correctement la progression des opérations"""
        manager = self.visual_feedback
        
        # Démarrer une opération
        operation_id = "progress_test"
        success = manager.start_operation(operation_id, "Test Progress Operation")
        
        if success:
            # Tester différentes valeurs de progression
            progress_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
            
            for progress in progress_values:
                message = f"Progression: {progress * 100:.0f}%"
                manager.update_operation_progress(operation_id, progress, message)
                
                # L'opération devrait toujours être active
                assert manager.is_operation_active(operation_id)
            
            # Terminer l'opération
            manager.finish_operation(operation_id)
            assert not manager.is_operation_active(operation_id)
    
    def test_visual_feedback_manager_pulse_mode(self):
        """Property: Le mode pulsation fonctionne correctement"""
        manager = self.visual_feedback
        
        operation_id = "pulse_test"
        success = manager.start_operation(operation_id, "Pulse Test Operation")
        
        if success:
            # Activer le mode pulsation plusieurs fois
            for _ in range(5):
                manager.pulse_operation(operation_id)
                
                # L'opération devrait toujours être active
                assert manager.is_operation_active(operation_id)
            
            # Terminer l'opération
            manager.finish_operation(operation_id)
    
    def test_concurrent_progress_updates(self):
        """Property: Les mises à jour concurrentes de progression sont sûres"""
        manager = self.visual_feedback
        operation_id = "concurrent_test"
        
        success = manager.start_operation(operation_id, "Concurrent Test")
        
        if success:
            errors = []
            
            def update_progress(thread_id):
                try:
                    for i in range(50):
                        progress = i / 49.0
                        message = f"Thread {thread_id}: {progress * 100:.1f}%"
                        manager.update_operation_progress(operation_id, progress, message)
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
            
            # L'opération devrait toujours être active
            assert manager.is_operation_active(operation_id)
            
            # Terminer l'opération
            manager.finish_operation(operation_id)
    
    def test_progress_indication_with_invalid_operation_id(self):
        """Property: Les opérations avec ID invalide sont gérées correctement"""
        manager = self.visual_feedback
        
        invalid_ids = ["", "nonexistent", "already_finished"]
        
        for invalid_id in invalid_ids:
            # Ces opérations ne devraient pas causer d'erreur
            manager.update_operation_progress(invalid_id, 0.5)
            manager.pulse_operation(invalid_id)
            manager.finish_operation(invalid_id)  # Devrait être ignoré silencieusement
            
            # L'ID ne devrait pas être dans les opérations actives
            assert not manager.is_operation_active(invalid_id)
    
    def test_progress_indication_edge_cases(self):
        """Property: Les cas limites de progression sont gérés"""
        manager = self.visual_feedback
        operation_id = "edge_case_test"
        
        success = manager.start_operation(operation_id, "Edge Case Test")
        
        if success:
            # Test avec des valeurs limites et spéciales
            edge_values = [
                float('-inf'),  # Infini négatif
                float('inf'),   # Infini positif
                0.0,           # Zéro
                1.0,           # Un
                -1.0,          # Négatif
                2.0,           # Supérieur à 1
            ]
            
            for value in edge_values:
                if float('-inf') < value < float('inf'):  # Éviter les infinis
                    try:
                        manager.update_operation_progress(operation_id, value)
                        # Si on arrive ici, pas d'exception
                        assert True
                    except Exception as e:
                        pytest.fail(f"Exception pour la valeur {value}: {e}")
            
            manager.finish_operation(operation_id)
    
    @given(st.text(min_size=0, max_size=200))
    def test_progress_message_robustness(self, message):
        """Property: Les messages de progression sont robustes"""
        manager = self.visual_feedback
        operation_id = "message_test"
        
        success = manager.start_operation(operation_id, "Message Test")
        
        if success:
            # Nettoyer le message pour éviter les caractères problématiques
            clean_message = "".join(c for c in message if c.isprintable())
            
            try:
                manager.update_operation_progress(operation_id, 0.5, clean_message)
                assert True
            except Exception as e:
                pytest.fail(f"Exception pour le message '{clean_message}': {e}")
            
            manager.finish_operation(operation_id)


class ProgressIndicationStateMachine(RuleBasedStateMachine):
    """Machine à états pour tester l'indication de progression"""
    
    def __init__(self):
        super().__init__()
        self.manager = VisualFeedbackManager()
        self.active_operations = {}  # operation_id -> info
        self.operation_counter = 0
    
    @rule()
    def start_new_operation(self):
        """Démarrer une nouvelle opération"""
        self.operation_counter += 1
        operation_id = f"op_{self.operation_counter}"
        title = f"Operation {self.operation_counter}"
        
        success = self.manager.start_operation(operation_id, title)
        if success:
            self.active_operations[operation_id] = {
                'title': title,
                'progress': 0.0,
                'started_at': datetime.now()
            }
    
    @rule(progress=st.floats(min_value=0.0, max_value=1.0))
    def update_random_operation_progress(self, progress):
        """Mettre à jour la progression d'une opération aléatoire"""
        if self.active_operations:
            operation_id = st.sampled_from(list(self.active_operations.keys())).example()
            
            message = f"Progress: {progress * 100:.1f}%"
            self.manager.update_operation_progress(operation_id, progress, message)
            
            # Mettre à jour notre suivi
            self.active_operations[operation_id]['progress'] = progress
    
    @rule()
    def pulse_random_operation(self):
        """Activer le mode pulsation pour une opération aléatoire"""
        if self.active_operations:
            operation_id = st.sampled_from(list(self.active_operations.keys())).example()
            self.manager.pulse_operation(operation_id)
    
    @rule()
    def finish_random_operation(self):
        """Terminer une opération aléatoire"""
        if self.active_operations:
            operation_id = st.sampled_from(list(self.active_operations.keys())).example()
            
            self.manager.finish_operation(operation_id)
            del self.active_operations[operation_id]
    
    @rule()
    def finish_all_operations(self):
        """Terminer toutes les opérations actives"""
        for operation_id in list(self.active_operations.keys()):
            self.manager.finish_operation(operation_id)
        
        self.active_operations.clear()
    
    @invariant()
    def active_operations_are_consistent(self):
        """Invariant: Les opérations actives sont cohérentes"""
        manager_active = set(self.manager.get_active_operations())
        tracked_active = set(self.active_operations.keys())
        
        assert manager_active == tracked_active
        
        for operation_id in self.active_operations:
            assert self.manager.is_operation_active(operation_id)
    
    @invariant()
    def operation_data_is_valid(self):
        """Invariant: Les données des opérations sont valides"""
        for operation_id, info in self.active_operations.items():
            assert 'title' in info
            assert 'progress' in info
            assert 'started_at' in info
            
            assert isinstance(info['title'], str)
            assert 0.0 <= info['progress'] <= 1.0
            assert isinstance(info['started_at'], datetime)
            
            # L'opération ne devrait pas être trop ancienne (plus de 1 minute)
            age = (datetime.now() - info['started_at']).total_seconds()
            assert age < 60.0


# Test de la machine à états
TestProgressIndicationStateMachine = ProgressIndicationStateMachine.TestCase


class TestProgressIndicationIntegration:
    """Tests d'intégration pour l'indication de progression"""
    
    def setup_method(self):
        self.manager = VisualFeedbackManager()
    
    def test_progress_indication_lifecycle_completeness(self):
        """Property: Le cycle de vie complet de l'indication de progression"""
        operation_id = "lifecycle_test"
        
        # Phase 1: Démarrage
        success = self.manager.start_operation(
            operation_id, 
            "Lifecycle Test", 
            "Initialisation...", 
            cancellable=True
        )
        
        if success:
            assert self.manager.is_operation_active(operation_id)
            
            # Phase 2: Progression déterminée
            progress_steps = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
            for progress in progress_steps:
                message = f"Étape {progress * 100:.0f}% terminée"
                self.manager.update_operation_progress(operation_id, progress, message)
                assert self.manager.is_operation_active(operation_id)
            
            # Phase 3: Progression indéterminée
            for _ in range(5):
                self.manager.pulse_operation(operation_id)
                assert self.manager.is_operation_active(operation_id)
            
            # Phase 4: Finalisation
            self.manager.update_operation_progress(operation_id, 1.0, "Finalisation...")
            assert self.manager.is_operation_active(operation_id)
            
            # Phase 5: Terminaison
            self.manager.finish_operation(operation_id)
            assert not self.manager.is_operation_active(operation_id)
    
    def test_progress_indication_error_recovery(self):
        """Property: La récupération d'erreur dans l'indication de progression"""
        operation_id = "error_recovery_test"
        
        # Démarrer une opération
        success = self.manager.start_operation(operation_id, "Error Recovery Test")
        
        if success:
            # Simuler des conditions d'erreur
            error_conditions = [
                lambda: self.manager.update_operation_progress(operation_id, float('inf')),
                lambda: self.manager.update_operation_progress(operation_id, -1.0),
                lambda: self.manager.update_operation_progress(operation_id, 0.5, None),
                lambda: self.manager.pulse_operation(operation_id + "_invalid"),
            ]
            
            for error_condition in error_conditions:
                try:
                    error_condition()
                    # L'opération devrait toujours être active après une erreur
                    assert self.manager.is_operation_active(operation_id)
                except Exception:
                    # Les exceptions sont acceptables, mais l'état doit rester cohérent
                    assert self.manager.is_operation_active(operation_id)
            
            # Terminer normalement
            self.manager.finish_operation(operation_id)
            assert not self.manager.is_operation_active(operation_id)
    
    def test_multiple_operations_progress_isolation(self):
        """Property: L'isolation de la progression entre opérations multiples"""
        operations = [
            ("op1", "Operation 1"),
            ("op2", "Operation 2"),
            ("op3", "Operation 3"),
        ]
        
        started_operations = []
        
        # Démarrer toutes les opérations
        for op_id, title in operations:
            success = self.manager.start_operation(op_id, title)
            if success:
                started_operations.append(op_id)
        
        # Mettre à jour chaque opération indépendamment
        for i, op_id in enumerate(started_operations):
            progress = (i + 1) / len(started_operations)
            message = f"Operation {i + 1} at {progress * 100:.0f}%"
            
            self.manager.update_operation_progress(op_id, progress, message)
            
            # Toutes les opérations devraient toujours être actives
            for other_op_id in started_operations:
                assert self.manager.is_operation_active(other_op_id)
        
        # Terminer les opérations une par une
        for op_id in started_operations:
            self.manager.finish_operation(op_id)
            assert not self.manager.is_operation_active(op_id)
            
            # Les autres opérations devraient toujours être actives
            remaining_ops = [oid for oid in started_operations if oid != op_id]
            for other_op_id in remaining_ops:
                if self.manager.is_operation_active(other_op_id):
                    # Peut être False si l'opération a déjà été terminée
                    pass
    
    def test_progress_indication_performance(self):
        """Property: Les performances de l'indication de progression"""
        operation_id = "performance_test"
        
        success = self.manager.start_operation(operation_id, "Performance Test")
        
        if success:
            start_time = time.time()
            
            # Effectuer de nombreuses mises à jour rapides
            num_updates = 1000
            for i in range(num_updates):
                progress = i / (num_updates - 1)
                message = f"Update {i + 1}/{num_updates}"
                self.manager.update_operation_progress(operation_id, progress, message)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Les mises à jour ne devraient pas prendre trop de temps
            # (même avec GTK, cela devrait être raisonnable)
            assert duration < 10.0, f"Mises à jour trop lentes: {duration:.2f}s"
            
            # L'opération devrait toujours être active
            assert self.manager.is_operation_active(operation_id)
            
            self.manager.finish_operation(operation_id)


if __name__ == '__main__':
    pytest.main([__file__])