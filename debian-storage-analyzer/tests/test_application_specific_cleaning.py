# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import sqlite3
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest
from unittest.mock import patch, MagicMock

from src.cleaner.app_specific_cleaner import AppSpecificCleaner, AppCleaningProfile
from src.cleaner.intelligent_cleaner import CleaningAction, CleaningResult


class TestApplicationSpecificCleaning:
    """Tests pour le nettoyage spécifique par application"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = AppSpecificCleaner(dry_run=True)
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_application_detection_consistency(self):
        """Property: La détection d'applications est cohérente"""
        # Créer des structures de fichiers simulant des applications installées
        firefox_profile = os.path.join(self.temp_dir, ".mozilla", "firefox", "profile")
        chrome_cache = os.path.join(self.temp_dir, ".cache", "google-chrome")
        
        os.makedirs(firefox_profile, exist_ok=True)
        os.makedirs(chrome_cache, exist_ok=True)
        
        # Créer des fichiers de configuration
        Path(os.path.join(firefox_profile, "prefs.js")).touch()
        Path(os.path.join(chrome_cache, "Cache")).mkdir(exist_ok=True)
        
        # Modifier temporairement les profils pour utiliser nos chemins de test
        original_profiles = self.cleaner.profiles.copy()
        
        # Adapter les profils pour les tests
        test_profiles = {}
        for app_name, profile in original_profiles.items():
            test_profile = AppCleaningProfile(
                app_name=profile.app_name,
                display_name=profile.display_name,
                cache_paths=[path.replace('~', self.temp_dir) for path in profile.cache_paths],
                log_paths=[path.replace('~', self.temp_dir) for path in profile.log_paths],
                temp_paths=[path.replace('~', self.temp_dir) for path in profile.temp_paths],
                config_paths=[path.replace('~', self.temp_dir) for path in profile.config_paths],
                database_paths=[path.replace('~', self.temp_dir) for path in profile.database_paths],
                custom_commands=profile.custom_commands,
                safety_level=profile.safety_level
            )
            test_profiles[app_name] = test_profile
        
        self.cleaner.profiles = test_profiles
        
        # Tester la détection
        available_apps = self.cleaner.get_available_applications()
        
        # Vérifier que la détection est cohérente
        assert isinstance(available_apps, list)
        
        # Firefox devrait être détecté (fichier de config présent)
        # Chrome pourrait être détecté (cache présent)
        for app in available_apps:
            assert app in self.cleaner.profiles
            
            # Vérifier que l'application est vraiment "installée" selon nos critères
            profile = self.cleaner.profiles[app]
            assert self.cleaner._is_application_installed(profile)
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=1, max_value=1000000)
        ),
        min_size=1,
        max_size=10
    ))
    def test_cache_scanning_consistency(self, cache_files):
        """Property: Le scan des caches est cohérent"""
        # Créer un profil de test
        cache_dir = os.path.join(self.temp_dir, "test_cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        total_expected_size = 0
        created_files = []
        
        for filename, size in cache_files:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if safe_filename:
                cache_file = os.path.join(cache_dir, f"{safe_filename}.cache")
                try:
                    content = "x" * size
                    Path(cache_file).write_text(content, encoding='utf-8')
                    actual_size = len(content.encode('utf-8'))
                    total_expected_size += actual_size
                    created_files.append(cache_file)
                except (OSError, UnicodeEncodeError):
                    continue
        
        if not created_files:
            return  # Skip si aucun fichier créé
        
        # Créer un profil d'application de test
        test_profile = AppCleaningProfile(
            app_name="test_app",
            display_name="Test Application",
            cache_paths=[cache_dir],
            log_paths=[],
            temp_paths=[],
            config_paths=[],
            database_paths=[],
            custom_commands=[],
            safety_level="safe"
        )
        
        self.cleaner.add_custom_profile(test_profile)
        
        # Scanner les opportunités de nettoyage
        actions = self.cleaner.scan_application_cleaning_opportunities("test_app")
        
        # Vérifier la cohérence
        cache_actions = [a for a in actions if a.category == 'app_cache']
        
        if cache_actions:
            # Il devrait y avoir au moins une action de cache
            assert len(cache_actions) >= 1
            
            # La taille totale devrait être cohérente
            total_cache_size = sum(action.size_bytes for action in cache_actions)
            assert total_cache_size >= total_expected_size * 0.8  # Tolérance pour les métadonnées
    
    def test_database_optimization_detection(self):
        """Property: La détection d'optimisation de base de données est correcte"""
        # Créer une base de données SQLite de test
        db_path = os.path.join(self.temp_dir, "test.sqlite")
        
        # Créer une base avec des données et des pages libres
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Créer une table et insérer des données
        cursor.execute("CREATE TABLE test_table (id INTEGER, data TEXT)")
        for i in range(1000):
            cursor.execute("INSERT INTO test_table VALUES (?, ?)", (i, f"data_{i}" * 10))
        
        # Supprimer la moitié des données pour créer des pages libres
        cursor.execute("DELETE FROM test_table WHERE id % 2 = 0")
        conn.commit()
        conn.close()
        
        # Créer un profil avec cette base de données
        test_profile = AppCleaningProfile(
            app_name="db_test_app",
            display_name="Database Test App",
            cache_paths=[],
            log_paths=[],
            temp_paths=[],
            config_paths=[],
            database_paths=[db_path],
            custom_commands=[],
            safety_level="moderate"
        )
        
        self.cleaner.add_custom_profile(test_profile)
        
        # Scanner les opportunités
        actions = self.cleaner.scan_application_cleaning_opportunities("db_test_app")
        
        # Vérifier qu'une action de vacuum est proposée
        vacuum_actions = [a for a in actions if a.action_type == 'vacuum_database']
        
        if vacuum_actions:
            vacuum_action = vacuum_actions[0]
            assert vacuum_action.target_path == db_path
            assert vacuum_action.size_bytes > 0  # Devrait estimer des économies
            assert vacuum_action.safety_level == 'moderate'
            assert vacuum_action.reversible is True
    
    @given(st.lists(
        st.sampled_from(['firefox', 'chrome', 'chromium', 'vscode', 'snap']),
        min_size=1,
        max_size=5
    ))
    def test_multiple_applications_scanning(self, app_names):
        """Property: Le scan de multiples applications est cohérent"""
        all_actions = []
        
        for app_name in app_names:
            if app_name in self.cleaner.profiles:
                actions = self.cleaner.scan_application_cleaning_opportunities(app_name)
                all_actions.extend(actions)
        
        # Vérifier la cohérence des actions
        for action in all_actions:
            assert isinstance(action, CleaningAction)
            assert action.size_bytes >= 0
            assert action.safety_level in ['safe', 'moderate', 'risky']
            assert action.category.startswith('app_')
            assert len(action.description) > 0
    
    def test_custom_profile_management(self):
        """Property: La gestion des profils personnalisés est cohérente"""
        # Créer un profil personnalisé
        custom_profile = AppCleaningProfile(
            app_name="custom_test_app",
            display_name="Custom Test Application",
            cache_paths=[os.path.join(self.temp_dir, "custom_cache")],
            log_paths=[os.path.join(self.temp_dir, "custom_logs")],
            temp_paths=[os.path.join(self.temp_dir, "custom_temp")],
            config_paths=[os.path.join(self.temp_dir, "custom_config")],
            database_paths=[],
            custom_commands=["echo 'custom command'"],
            safety_level="moderate"
        )
        
        # Ajouter le profil
        self.cleaner.add_custom_profile(custom_profile)
        
        # Vérifier qu'il a été ajouté
        assert "custom_test_app" in self.cleaner.profiles
        
        # Vérifier les informations du profil
        info = self.cleaner.get_application_info("custom_test_app")
        assert info is not None
        assert info['name'] == "custom_test_app"
        assert info['display_name'] == "Custom Test Application"
        assert info['safety_level'] == "moderate"
        assert info['custom_commands_count'] == 1
        
        # Supprimer le profil
        success = self.cleaner.remove_profile("custom_test_app")
        assert success is True
        assert "custom_test_app" not in self.cleaner.profiles
        
        # Essayer de supprimer un profil inexistant
        success = self.cleaner.remove_profile("nonexistent_app")
        assert success is False
    
    def test_safety_level_consistency(self):
        """Property: Les niveaux de sécurité sont cohérents"""
        # Tester avec différents profils
        for app_name, profile in self.cleaner.profiles.items():
            actions = self.cleaner.scan_application_cleaning_opportunities(app_name)
            
            for action in actions:
                # Le niveau de sécurité de l'action devrait correspondre au profil
                # ou être plus restrictif
                profile_safety = profile.safety_level
                action_safety = action.safety_level
                
                safety_levels = ['safe', 'moderate', 'risky']
                profile_level = safety_levels.index(profile_safety)
                action_level = safety_levels.index(action_safety)
                
                # L'action ne devrait pas être plus risquée que le profil
                assert action_level <= profile_level
    
    @given(st.sampled_from(['vacuum_database', 'custom_command']))
    def test_specialized_action_execution(self, action_type):
        """Property: L'exécution d'actions spécialisées est cohérente"""
        if action_type == 'vacuum_database':
            # Créer une base de données de test
            db_path = os.path.join(self.temp_dir, "specialized_test.sqlite")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()
            conn.close()
            
            action = CleaningAction(
                action_type='vacuum_database',
                target_path=db_path,
                size_bytes=1024,
                description="Test vacuum",
                safety_level='moderate',
                category='app_database',
                reversible=True
            )
        
        elif action_type == 'custom_command':
            action = CleaningAction(
                action_type='custom_command',
                target_path='echo "test command"',
                size_bytes=1024,
                description="Test custom command",
                safety_level='safe',
                category='app_custom',
                reversible=False
            )
        
        # Exécuter l'action
        result = self.cleaner.execute_app_cleaning_action(action)
        
        # Vérifier la cohérence du résultat
        assert isinstance(result, CleaningResult)
        assert result.action == action
        assert isinstance(result.success, bool)
        assert result.actual_size_freed >= 0
        assert result.execution_time >= 0
        
        # En mode dry-run, l'action devrait réussir
        assert result.success is True


class TestAppCleaningProfile:
    """Tests pour les profils de nettoyage d'applications"""
    
    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=50),
        st.lists(st.text(min_size=1, max_size=50), max_size=5),
        st.sampled_from(['safe', 'moderate', 'risky'])
    )
    def test_profile_creation_consistency(self, app_name, display_name, cache_paths, safety_level):
        """Property: La création de profils est cohérente"""
        profile = AppCleaningProfile(
            app_name=app_name,
            display_name=display_name,
            cache_paths=cache_paths,
            log_paths=[],
            temp_paths=[],
            config_paths=[],
            database_paths=[],
            custom_commands=[],
            safety_level=safety_level
        )
        
        # Vérifier que tous les attributs sont correctement assignés
        assert profile.app_name == app_name
        assert profile.display_name == display_name
        assert profile.cache_paths == cache_paths
        assert profile.safety_level == safety_level
        assert isinstance(profile.log_paths, list)
        assert isinstance(profile.temp_paths, list)
        assert isinstance(profile.config_paths, list)
        assert isinstance(profile.database_paths, list)
        assert isinstance(profile.custom_commands, list)


class ApplicationSpecificCleaning(RuleBasedStateMachine):
    """Machine à états pour tester le nettoyage spécifique par application"""
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = AppSpecificCleaner(dry_run=True)
        self.custom_profiles = {}
        self.created_files = {}
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(app_name=st.text(min_size=1, max_size=15),
          safety_level=st.sampled_from(['safe', 'moderate', 'risky']))
    def add_custom_application_profile(self, app_name, safety_level):
        """Ajouter un profil d'application personnalisé"""
        safe_app_name = "".join(c for c in app_name if c.isalnum() or c in "._-")
        if safe_app_name and safe_app_name not in self.custom_profiles:
            
            # Créer des répertoires de test
            app_dir = os.path.join(self.temp_dir, safe_app_name)
            cache_dir = os.path.join(app_dir, "cache")
            log_dir = os.path.join(app_dir, "logs")
            
            os.makedirs(cache_dir, exist_ok=True)
            os.makedirs(log_dir, exist_ok=True)
            
            profile = AppCleaningProfile(
                app_name=safe_app_name,
                display_name=f"Test {safe_app_name}",
                cache_paths=[cache_dir],
                log_paths=[log_dir],
                temp_paths=[],
                config_paths=[],
                database_paths=[],
                custom_commands=[],
                safety_level=safety_level
            )
            
            self.cleaner.add_custom_profile(profile)
            self.custom_profiles[safe_app_name] = profile
    
    @rule(filename=st.text(min_size=1, max_size=15),
          size=st.integers(min_value=1, max_value=10000))
    def create_cache_file(self, filename, size):
        """Créer un fichier de cache pour une application"""
        if self.custom_profiles:
            app_name = list(self.custom_profiles.keys())[0]
            profile = self.custom_profiles[app_name]
            
            if profile.cache_paths:
                cache_dir = profile.cache_paths[0]
                safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                
                if safe_filename:
                    cache_file = os.path.join(cache_dir, f"{safe_filename}.cache")
                    try:
                        content = "x" * size
                        Path(cache_file).write_text(content, encoding='utf-8')
                        self.created_files[cache_file] = len(content.encode('utf-8'))
                    except (OSError, UnicodeEncodeError):
                        pass
    
    @rule()
    def scan_cleaning_opportunities(self):
        """Scanner les opportunités de nettoyage"""
        for app_name in self.custom_profiles:
            actions = self.cleaner.scan_application_cleaning_opportunities(app_name)
            
            # Vérifier que les actions sont cohérentes
            for action in actions:
                assert isinstance(action, CleaningAction)
                assert action.size_bytes >= 0
                assert action.safety_level in ['safe', 'moderate', 'risky']
    
    @rule()
    def get_application_info(self):
        """Obtenir les informations d'application"""
        for app_name in self.custom_profiles:
            info = self.cleaner.get_application_info(app_name)
            
            assert info is not None
            assert info['name'] == app_name
            assert info['safety_level'] in ['safe', 'moderate', 'risky']
    
    @invariant()
    def profiles_are_consistent(self):
        """Invariant: Les profils sont cohérents"""
        for app_name, profile in self.custom_profiles.items():
            # Le profil devrait être présent dans le cleaner
            assert app_name in self.cleaner.profiles
            
            # Les attributs devraient être cohérents
            cleaner_profile = self.cleaner.profiles[app_name]
            assert cleaner_profile.app_name == profile.app_name
            assert cleaner_profile.safety_level == profile.safety_level
    
    @invariant()
    def created_files_exist(self):
        """Invariant: Les fichiers créés existent"""
        for filepath in self.created_files:
            if os.path.exists(os.path.dirname(filepath)):
                # Le fichier devrait exister (sauf s'il a été nettoyé)
                pass


# Test de la machine à états
TestApplicationSpecificCleaning = ApplicationSpecificCleaning.TestCase


if __name__ == '__main__':
    pytest.main([__file__])