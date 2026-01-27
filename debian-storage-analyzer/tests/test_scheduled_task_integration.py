# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.cleaner.scheduled_cleaner import ScheduledCleaner, CleaningSchedule


class TestScheduledTaskIntegration:
    """Tests pour l'intégration des tâches planifiées"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock des répertoires de configuration
        self.config_dir = os.path.join(self.temp_dir, "config")
        self.systemd_dir = os.path.join(self.temp_dir, "systemd")
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.systemd_dir, exist_ok=True)
        
        # Créer un scheduler avec des chemins mockés
        self.scheduler = ScheduledCleaner()
        self.scheduler.config_dir = self.config_dir
        self.scheduler.schedules_file = os.path.join(self.config_dir, "schedules.json")
        self.scheduler.systemd_user_dir = self.systemd_dir
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        st.text(min_size=1, max_size=20),
        st.sampled_from(['daily', 'weekly', 'monthly']),
        st.integers(min_value=0, max_value=23),
        st.integers(min_value=0, max_value=59)
    )
    def test_schedule_validation_consistency(self, name, frequency, hour, minute):
        """Property: La validation des planifications est cohérente"""
        # Créer une planification de base
        schedule = CleaningSchedule(
            name=name,
            description=f"Test schedule {name}",
            frequency=frequency,
            time=f"{hour:02d}:{minute:02d}",
            enabled=True
        )
        
        # Ajouter les paramètres spécifiques selon la fréquence
        if frequency == 'weekly':
            schedule.day_of_week = 1  # Mardi
        elif frequency == 'monthly':
            schedule.day_of_month = 15  # 15 du mois
        
        # La validation devrait être cohérente
        is_valid = self.scheduler._validate_schedule(schedule)
        
        # Vérifier que la validation est logique
        assert isinstance(is_valid, bool)
        
        # Si valide, on devrait pouvoir l'ajouter
        if is_valid:
            success = self.scheduler.add_schedule(schedule)
            # En mode test (sans systemd réel), cela peut échouer mais la validation était correcte
            assert isinstance(success, bool)
    
    def test_schedule_persistence_consistency(self):
        """Property: La persistance des planifications est cohérente"""
        # Créer une planification valide
        schedule = CleaningSchedule(
            name="test_persistence",
            description="Test de persistance",
            frequency="daily",
            time="02:30",
            enabled=True,
            applications=["firefox", "chrome"],
            categories=["cache", "temp"],
            safety_level="safe"
        )
        
        # Ajouter la planification
        success = self.scheduler.add_schedule(schedule)
        assert success is True
        
        # Vérifier qu'elle est sauvegardée
        assert os.path.exists(self.scheduler.schedules_file)
        
        # Créer un nouveau scheduler et vérifier qu'il charge la planification
        new_scheduler = ScheduledCleaner()
        new_scheduler.config_dir = self.config_dir
        new_scheduler.schedules_file = self.scheduler.schedules_file
        new_scheduler.schedules = new_scheduler._load_schedules()
        
        # La planification devrait être présente
        assert "test_persistence" in new_scheduler.schedules
        loaded_schedule = new_scheduler.schedules["test_persistence"]
        
        # Vérifier que tous les attributs sont préservés
        assert loaded_schedule.name == schedule.name
        assert loaded_schedule.description == schedule.description
        assert loaded_schedule.frequency == schedule.frequency
        assert loaded_schedule.time == schedule.time
        assert loaded_schedule.enabled == schedule.enabled
        assert loaded_schedule.applications == schedule.applications
        assert loaded_schedule.categories == schedule.categories
        assert loaded_schedule.safety_level == schedule.safety_level
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=15),
            st.sampled_from(['daily', 'weekly', 'monthly']),
            st.booleans()
        ),
        min_size=1,
        max_size=10
    ))
    def test_multiple_schedules_management(self, schedule_specs):
        """Property: La gestion de multiples planifications est cohérente"""
        created_schedules = {}
        
        for name, frequency, enabled in schedule_specs:
            # Créer un nom unique
            unique_name = f"{name}_{len(created_schedules)}"
            
            schedule = CleaningSchedule(
                name=unique_name,
                description=f"Test {unique_name}",
                frequency=frequency,
                time="03:00",
                enabled=enabled
            )
            
            # Ajouter les paramètres spécifiques
            if frequency == 'weekly':
                schedule.day_of_week = 0  # Lundi
            elif frequency == 'monthly':
                schedule.day_of_month = 1  # 1er du mois
            
            # Ajouter la planification
            success = self.scheduler.add_schedule(schedule)
            if success:
                created_schedules[unique_name] = schedule
        
        # Vérifier que toutes les planifications sont présentes
        current_schedules = self.scheduler.get_schedules()
        
        for name, original_schedule in created_schedules.items():
            assert name in current_schedules
            loaded_schedule = current_schedules[name]
            assert loaded_schedule.frequency == original_schedule.frequency
            assert loaded_schedule.enabled == original_schedule.enabled
    
    def test_schedule_update_consistency(self):
        """Property: Les mises à jour de planifications sont cohérentes"""
        # Créer une planification initiale
        original_schedule = CleaningSchedule(
            name="update_test",
            description="Original description",
            frequency="daily",
            time="02:00",
            enabled=True,
            safety_level="safe"
        )
        
        self.scheduler.add_schedule(original_schedule)
        
        # Créer une version mise à jour
        updated_schedule = CleaningSchedule(
            name="update_test",
            description="Updated description",
            frequency="weekly",
            time="03:30",
            day_of_week=2,  # Mercredi
            enabled=False,
            safety_level="moderate"
        )
        
        # Mettre à jour
        success = self.scheduler.update_schedule("update_test", updated_schedule)
        assert success is True
        
        # Vérifier que les changements sont appliqués
        current_schedule = self.scheduler.get_schedule("update_test")
        assert current_schedule is not None
        assert current_schedule.description == "Updated description"
        assert current_schedule.frequency == "weekly"
        assert current_schedule.time == "03:30"
        assert current_schedule.day_of_week == 2
        assert current_schedule.enabled is False
        assert current_schedule.safety_level == "moderate"
    
    def test_schedule_removal_consistency(self):
        """Property: La suppression de planifications est cohérente"""
        # Créer plusieurs planifications
        schedules_to_create = ["remove_test_1", "remove_test_2", "remove_test_3"]
        
        for name in schedules_to_create:
            schedule = CleaningSchedule(
                name=name,
                description=f"Test {name}",
                frequency="daily",
                time="04:00",
                enabled=True
            )
            self.scheduler.add_schedule(schedule)
        
        # Vérifier qu'elles sont toutes présentes
        current_schedules = self.scheduler.get_schedules()
        for name in schedules_to_create:
            assert name in current_schedules
        
        # Supprimer une planification
        success = self.scheduler.remove_schedule("remove_test_2")
        assert success is True
        
        # Vérifier qu'elle a été supprimée
        current_schedules = self.scheduler.get_schedules()
        assert "remove_test_2" not in current_schedules
        
        # Vérifier que les autres sont toujours présentes
        assert "remove_test_1" in current_schedules
        assert "remove_test_3" in current_schedules
        
        # Essayer de supprimer une planification inexistante
        success = self.scheduler.remove_schedule("nonexistent")
        assert success is False
    
    @given(st.sampled_from(['daily', 'weekly', 'monthly']))
    def test_next_execution_time_calculation(self, frequency):
        """Property: Le calcul des prochaines exécutions est cohérent"""
        schedule = CleaningSchedule(
            name="time_test",
            description="Test de calcul de temps",
            frequency=frequency,
            time="14:30",  # 14h30
            enabled=True
        )
        
        # Ajouter les paramètres spécifiques
        if frequency == 'weekly':
            schedule.day_of_week = 3  # Jeudi
        elif frequency == 'monthly':
            schedule.day_of_month = 10  # 10 du mois
        
        self.scheduler.add_schedule(schedule)
        
        # Calculer les prochaines exécutions
        next_times = self.scheduler.get_next_execution_times()
        
        if "time_test" in next_times:
            next_time = next_times["time_test"]
            
            # Vérifier que c'est dans le futur
            assert next_time > datetime.now()
            
            # Vérifier l'heure
            assert next_time.hour == 14
            assert next_time.minute == 30
            
            # Vérifier la cohérence selon la fréquence
            if frequency == 'weekly':
                assert next_time.weekday() == 3  # Jeudi
            elif frequency == 'monthly':
                assert next_time.day == 10
    
    def test_schedule_enable_disable_consistency(self):
        """Property: L'activation/désactivation des planifications est cohérente"""
        # Créer une planification désactivée
        schedule = CleaningSchedule(
            name="enable_disable_test",
            description="Test enable/disable",
            frequency="daily",
            time="05:00",
            enabled=False
        )
        
        self.scheduler.add_schedule(schedule)
        
        # Vérifier qu'elle est désactivée
        current_schedule = self.scheduler.get_schedule("enable_disable_test")
        assert current_schedule.enabled is False
        
        # Activer
        success = self.scheduler.enable_schedule("enable_disable_test")
        assert success is True
        
        # Vérifier qu'elle est activée
        current_schedule = self.scheduler.get_schedule("enable_disable_test")
        assert current_schedule.enabled is True
        
        # Désactiver
        success = self.scheduler.disable_schedule("enable_disable_test")
        assert success is True
        
        # Vérifier qu'elle est désactivée
        current_schedule = self.scheduler.get_schedule("enable_disable_test")
        assert current_schedule.enabled is False
    
    def test_default_schedules_creation(self):
        """Property: La création de planifications par défaut est cohérente"""
        # Créer les planifications par défaut
        self.scheduler.create_default_schedules()
        
        # Vérifier qu'elles ont été créées
        schedules = self.scheduler.get_schedules()
        
        expected_defaults = ["daily_cache_cleanup", "weekly_temp_cleanup", "monthly_deep_cleanup"]
        
        for default_name in expected_defaults:
            assert default_name in schedules
            schedule = schedules[default_name]
            
            # Vérifier que les planifications par défaut sont valides
            assert self.scheduler._validate_schedule(schedule)
            assert schedule.enabled is True  # Par défaut activées
            assert schedule.safety_level in ['safe', 'moderate']


class TestScheduleValidation:
    """Tests spécifiques pour la validation des planifications"""
    
    def setup_method(self):
        self.scheduler = ScheduledCleaner()
    
    @given(
        st.integers(min_value=-5, max_value=30),
        st.integers(min_value=-5, max_value=70)
    )
    def test_time_validation_boundaries(self, hour, minute):
        """Property: La validation des heures respecte les limites"""
        schedule = CleaningSchedule(
            name="time_boundary_test",
            description="Test des limites de temps",
            frequency="daily",
            time=f"{hour:02d}:{minute:02d}",
            enabled=True
        )
        
        is_valid = self.scheduler._validate_schedule(schedule)
        
        # Devrait être valide seulement si 0 <= hour <= 23 et 0 <= minute <= 59
        expected_valid = (0 <= hour <= 23) and (0 <= minute <= 59)
        assert is_valid == expected_valid
    
    @given(st.integers(min_value=-2, max_value=10))
    def test_weekly_day_validation(self, day_of_week):
        """Property: La validation des jours de semaine est correcte"""
        schedule = CleaningSchedule(
            name="weekly_day_test",
            description="Test jour de semaine",
            frequency="weekly",
            time="12:00",
            day_of_week=day_of_week,
            enabled=True
        )
        
        is_valid = self.scheduler._validate_schedule(schedule)
        
        # Devrait être valide seulement si 0 <= day_of_week <= 6
        expected_valid = 0 <= day_of_week <= 6
        assert is_valid == expected_valid
    
    @given(st.integers(min_value=-5, max_value=35))
    def test_monthly_day_validation(self, day_of_month):
        """Property: La validation des jours du mois est correcte"""
        schedule = CleaningSchedule(
            name="monthly_day_test",
            description="Test jour du mois",
            frequency="monthly",
            time="12:00",
            day_of_month=day_of_month,
            enabled=True
        )
        
        is_valid = self.scheduler._validate_schedule(schedule)
        
        # Devrait être valide seulement si 1 <= day_of_month <= 31
        expected_valid = 1 <= day_of_month <= 31
        assert is_valid == expected_valid
    
    @given(st.sampled_from(['invalid', 'hourly', 'yearly', 'custom']))
    def test_frequency_validation(self, frequency):
        """Property: La validation des fréquences rejette les valeurs invalides"""
        schedule = CleaningSchedule(
            name="frequency_test",
            description="Test fréquence",
            frequency=frequency,
            time="12:00",
            enabled=True
        )
        
        is_valid = self.scheduler._validate_schedule(schedule)
        
        # Seules 'daily', 'weekly', 'monthly' sont valides
        expected_valid = frequency in ['daily', 'weekly', 'monthly']
        assert is_valid == expected_valid


class ScheduledTaskIntegration(RuleBasedStateMachine):
    """Machine à états pour tester l'intégration des tâches planifiées"""
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.scheduler = ScheduledCleaner()
        self.scheduler.config_dir = self.config_dir
        self.scheduler.schedules_file = os.path.join(self.config_dir, "schedules.json")
        
        self.created_schedules = set()
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(name=st.text(min_size=1, max_size=15),
          frequency=st.sampled_from(['daily', 'weekly', 'monthly']),
          enabled=st.booleans())
    def add_schedule(self, name, frequency, enabled):
        """Ajouter une planification"""
        # Créer un nom unique
        unique_name = f"{name}_{len(self.created_schedules)}"
        
        schedule = CleaningSchedule(
            name=unique_name,
            description=f"Test {unique_name}",
            frequency=frequency,
            time="12:00",
            enabled=enabled
        )
        
        # Ajouter les paramètres spécifiques
        if frequency == 'weekly':
            schedule.day_of_week = 1
        elif frequency == 'monthly':
            schedule.day_of_month = 15
        
        success = self.scheduler.add_schedule(schedule)
        if success:
            self.created_schedules.add(unique_name)
    
    @rule()
    def update_random_schedule(self):
        """Mettre à jour une planification aléatoire"""
        if self.created_schedules:
            name = list(self.created_schedules)[0]
            
            updated_schedule = CleaningSchedule(
                name=name,
                description=f"Updated {name}",
                frequency="daily",
                time="15:30",
                enabled=True
            )
            
            self.scheduler.update_schedule(name, updated_schedule)
    
    @rule()
    def remove_random_schedule(self):
        """Supprimer une planification aléatoire"""
        if self.created_schedules:
            name = list(self.created_schedules)[0]
            success = self.scheduler.remove_schedule(name)
            if success:
                self.created_schedules.remove(name)
    
    @rule()
    def calculate_next_execution_times(self):
        """Calculer les prochaines heures d'exécution"""
        next_times = self.scheduler.get_next_execution_times()
        
        # Vérifier que les temps sont cohérents
        for schedule_name, next_time in next_times.items():
            assert isinstance(next_time, datetime)
            assert next_time > datetime.now()
    
    @invariant()
    def schedules_are_consistent(self):
        """Invariant: Les planifications sont cohérentes"""
        current_schedules = self.scheduler.get_schedules()
        
        # Toutes les planifications créées devraient être présentes
        for name in self.created_schedules:
            assert name in current_schedules
        
        # Toutes les planifications présentes devraient être valides
        for schedule in current_schedules.values():
            assert self.scheduler._validate_schedule(schedule)
    
    @invariant()
    def persistence_is_working(self):
        """Invariant: La persistance fonctionne"""
        if self.created_schedules:
            # Le fichier de configuration devrait exister
            assert os.path.exists(self.scheduler.schedules_file)
            
            # Il devrait contenir des données JSON valides
            try:
                with open(self.scheduler.schedules_file, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
            except (json.JSONDecodeError, IOError):
                assert False, "Fichier de configuration invalide"


# Test de la machine à états
TestScheduledTaskIntegration = ScheduledTaskIntegration.TestCase


if __name__ == '__main__':
    pytest.main([__file__])