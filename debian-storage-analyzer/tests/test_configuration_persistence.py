"""
Property-based tests for configuration persistence.

Tests the configuration system's ability to save, load, and maintain
configuration data correctly across application restarts.
"""

import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.configuration_manager import (
    ConfigurationManager, Configuration, UIPreferences, 
    AnalysisPreferences, CleaningPreferences, MonitoringPreferences, 
    ReportingPreferences
)


class ConfigurationPersistenceTests(unittest.TestCase):
    """Property-based tests for configuration persistence."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.manager = ConfigurationManager(self.config_path)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @given(
        theme=st.sampled_from(['auto', 'light', 'dark']),
        sidebar_width=st.integers(min_value=100, max_value=500),
        window_width=st.integers(min_value=800, max_value=2000),
        window_height=st.integers(min_value=600, max_value=1500),
        show_tooltips=st.booleans(),
        animation_enabled=st.booleans(),
        language=st.sampled_from(['fr', 'en', 'es', 'de'])
    )
    @settings(max_examples=50)
    def test_ui_preferences_persistence(self, theme, sidebar_width, window_width, 
                                       window_height, show_tooltips, animation_enabled, language):
        """
        Property 22: Configuration Persistence
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Test that UI preferences are correctly saved and restored.
        """
        # Create configuration with UI preferences
        config = Configuration()
        config.ui = UIPreferences(
            theme=theme,
            sidebar_width=sidebar_width,
            window_width=window_width,
            window_height=window_height,
            show_tooltips=show_tooltips,
            animation_enabled=animation_enabled,
            language=language
        )
        
        # Save configuration
        success = self.manager.save_configuration(config)
        self.assertTrue(success, "Configuration should be saved successfully")
        
        # Create new manager instance to simulate application restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify UI preferences are preserved
        self.assertEqual(loaded_config.ui.theme, theme)
        self.assertEqual(loaded_config.ui.sidebar_width, sidebar_width)
        self.assertEqual(loaded_config.ui.window_width, window_width)
        self.assertEqual(loaded_config.ui.window_height, window_height)
        self.assertEqual(loaded_config.ui.show_tooltips, show_tooltips)
        self.assertEqual(loaded_config.ui.animation_enabled, animation_enabled)
        self.assertEqual(loaded_config.ui.language, language)
    
    @given(
        default_directories=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
        include_hidden_files=st.booleans(),
        follow_symlinks=st.booleans(),
        max_depth=st.integers(min_value=-1, max_value=20),
        file_size_threshold=st.integers(min_value=0, max_value=1000000),
        enable_duplicate_detection=st.booleans(),
        hash_algorithm=st.sampled_from(['md5', 'sha1', 'sha256'])
    )
    @settings(max_examples=50)
    def test_analysis_preferences_persistence(self, default_directories, include_hidden_files,
                                            follow_symlinks, max_depth, file_size_threshold,
                                            enable_duplicate_detection, hash_algorithm):
        """
        Property 22: Configuration Persistence
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Test that analysis preferences are correctly saved and restored.
        """
        # Filter out problematic directory names
        safe_directories = [d for d in default_directories if d.strip() and not d.startswith('.')]
        assume(len(safe_directories) > 0)
        
        # Create configuration with analysis preferences
        config = Configuration()
        config.analysis = AnalysisPreferences(
            default_directories=safe_directories,
            include_hidden_files=include_hidden_files,
            follow_symlinks=follow_symlinks,
            max_depth=max_depth,
            file_size_threshold=file_size_threshold,
            enable_duplicate_detection=enable_duplicate_detection,
            hash_algorithm=hash_algorithm
        )
        
        # Save configuration
        success = self.manager.save_configuration(config)
        self.assertTrue(success, "Configuration should be saved successfully")
        
        # Create new manager instance to simulate application restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify analysis preferences are preserved
        self.assertEqual(loaded_config.analysis.default_directories, safe_directories)
        self.assertEqual(loaded_config.analysis.include_hidden_files, include_hidden_files)
        self.assertEqual(loaded_config.analysis.follow_symlinks, follow_symlinks)
        self.assertEqual(loaded_config.analysis.max_depth, max_depth)
        self.assertEqual(loaded_config.analysis.file_size_threshold, file_size_threshold)
        self.assertEqual(loaded_config.analysis.enable_duplicate_detection, enable_duplicate_detection)
        self.assertEqual(loaded_config.analysis.hash_algorithm, hash_algorithm)
    
    @given(
        dry_run_by_default=st.booleans(),
        confirm_before_delete=st.booleans(),
        backup_before_clean=st.booleans(),
        backup_retention_days=st.integers(min_value=1, max_value=365),
        excluded_paths=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10),
        app_cleaning=st.dictionaries(
            st.sampled_from(['firefox', 'chrome', 'flatpak', 'snap']),
            st.booleans(),
            min_size=1,
            max_size=4
        )
    )
    @settings(max_examples=50)
    def test_cleaning_preferences_persistence(self, dry_run_by_default, confirm_before_delete,
                                            backup_before_clean, backup_retention_days,
                                            excluded_paths, app_cleaning):
        """
        Property 22: Configuration Persistence
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Test that cleaning preferences are correctly saved and restored.
        """
        # Filter out problematic paths
        safe_paths = [p for p in excluded_paths if p.strip() and not p.startswith('.')]
        
        # Create configuration with cleaning preferences
        config = Configuration()
        config.cleaning = CleaningPreferences(
            dry_run_by_default=dry_run_by_default,
            confirm_before_delete=confirm_before_delete,
            backup_before_clean=backup_before_clean,
            backup_retention_days=backup_retention_days,
            excluded_paths=safe_paths,
            app_specific_cleaning=app_cleaning
        )
        
        # Save configuration
        success = self.manager.save_configuration(config)
        self.assertTrue(success, "Configuration should be saved successfully")
        
        # Create new manager instance to simulate application restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify cleaning preferences are preserved
        self.assertEqual(loaded_config.cleaning.dry_run_by_default, dry_run_by_default)
        self.assertEqual(loaded_config.cleaning.confirm_before_delete, confirm_before_delete)
        self.assertEqual(loaded_config.cleaning.backup_before_clean, backup_before_clean)
        self.assertEqual(loaded_config.cleaning.backup_retention_days, backup_retention_days)
        self.assertEqual(loaded_config.cleaning.excluded_paths, safe_paths)
        self.assertEqual(loaded_config.cleaning.app_specific_cleaning, app_cleaning)
    
    @given(
        enable_realtime=st.booleans(),
        update_interval=st.integers(min_value=1, max_value=60),
        enable_notifications=st.booleans(),
        notification_cooldown=st.integers(min_value=60, max_value=3600),
        disk_threshold=st.floats(min_value=50.0, max_value=99.0),
        cpu_threshold=st.floats(min_value=50.0, max_value=99.0),
        memory_threshold=st.floats(min_value=50.0, max_value=99.0)
    )
    @settings(max_examples=50)
    def test_monitoring_preferences_persistence(self, enable_realtime, update_interval,
                                              enable_notifications, notification_cooldown,
                                              disk_threshold, cpu_threshold, memory_threshold):
        """
        Property 22: Configuration Persistence
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Test that monitoring preferences are correctly saved and restored.
        """
        # Create configuration with monitoring preferences
        config = Configuration()
        config.monitoring = MonitoringPreferences(
            enable_realtime=enable_realtime,
            update_interval=update_interval,
            enable_notifications=enable_notifications,
            notification_cooldown=notification_cooldown,
            disk_usage_threshold=disk_threshold,
            cpu_usage_threshold=cpu_threshold,
            memory_usage_threshold=memory_threshold
        )
        
        # Save configuration
        success = self.manager.save_configuration(config)
        self.assertTrue(success, "Configuration should be saved successfully")
        
        # Create new manager instance to simulate application restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify monitoring preferences are preserved
        self.assertEqual(loaded_config.monitoring.enable_realtime, enable_realtime)
        self.assertEqual(loaded_config.monitoring.update_interval, update_interval)
        self.assertEqual(loaded_config.monitoring.enable_notifications, enable_notifications)
        self.assertEqual(loaded_config.monitoring.notification_cooldown, notification_cooldown)
        self.assertAlmostEqual(loaded_config.monitoring.disk_usage_threshold, disk_threshold, places=2)
        self.assertAlmostEqual(loaded_config.monitoring.cpu_usage_threshold, cpu_threshold, places=2)
        self.assertAlmostEqual(loaded_config.monitoring.memory_usage_threshold, memory_threshold, places=2)
    
    @given(
        default_format=st.sampled_from(['pdf', 'csv', 'html']),
        include_charts=st.booleans(),
        chart_style=st.sampled_from(['modern', 'classic', 'minimal']),
        export_directory=st.text(min_size=1, max_size=100),
        auto_save_reports=st.booleans()
    )
    @settings(max_examples=50)
    def test_reporting_preferences_persistence(self, default_format, include_charts,
                                             chart_style, export_directory, auto_save_reports):
        """
        Property 22: Configuration Persistence
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Test that reporting preferences are correctly saved and restored.
        """
        # Filter out problematic directory names
        safe_directory = export_directory.strip()
        assume(safe_directory and not safe_directory.startswith('.'))
        
        # Create configuration with reporting preferences
        config = Configuration()
        config.reporting = ReportingPreferences(
            default_format=default_format,
            include_charts=include_charts,
            chart_style=chart_style,
            export_directory=safe_directory,
            auto_save_reports=auto_save_reports
        )
        
        # Save configuration
        success = self.manager.save_configuration(config)
        self.assertTrue(success, "Configuration should be saved successfully")
        
        # Create new manager instance to simulate application restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify reporting preferences are preserved
        self.assertEqual(loaded_config.reporting.default_format, default_format)
        self.assertEqual(loaded_config.reporting.include_charts, include_charts)
        self.assertEqual(loaded_config.reporting.chart_style, chart_style)
        self.assertEqual(loaded_config.reporting.export_directory, safe_directory)
        self.assertEqual(loaded_config.reporting.auto_save_reports, auto_save_reports)
    
    def test_configuration_file_format(self):
        """Test that configuration file is valid JSON."""
        # Create and save a configuration
        config = Configuration()
        success = self.manager.save_configuration(config)
        self.assertTrue(success)
        
        # Verify file exists and is valid JSON
        self.assertTrue(os.path.exists(self.config_path))
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify basic structure
        self.assertIsInstance(data, dict)
        self.assertIn('ui', data)
        self.assertIn('analysis', data)
        self.assertIn('cleaning', data)
        self.assertIn('monitoring', data)
        self.assertIn('reporting', data)
        self.assertIn('version', data)
        self.assertIn('last_updated', data)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        config = Configuration()
        
        # Valid configuration should have no issues
        issues = self.manager.validate_configuration(config)
        self.assertEqual(len(issues), 0, f"Valid configuration should have no issues: {issues}")
        
        # Invalid theme should be detected
        config.ui.theme = "invalid_theme"
        issues = self.manager.validate_configuration(config)
        self.assertGreater(len(issues), 0, "Invalid theme should be detected")
        
        # Invalid sidebar width should be detected
        config.ui.theme = "auto"  # Reset to valid
        config.ui.sidebar_width = 50  # Too small
        issues = self.manager.validate_configuration(config)
        self.assertGreater(len(issues), 0, "Invalid sidebar width should be detected")
    
    def test_partial_configuration_loading(self):
        """Test loading configuration with missing fields."""
        # Create partial configuration file
        partial_config = {
            'ui': {'theme': 'dark'},
            'version': '1.0.0'
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(partial_config, f)
        
        # Load configuration - should fill in defaults
        new_manager = ConfigurationManager(self.config_path)
        config = new_manager.get_configuration()
        
        # Verify loaded values
        self.assertEqual(config.ui.theme, 'dark')
        self.assertEqual(config.ui.sidebar_width, 250)  # Default value
        self.assertTrue(config.analysis.enable_duplicate_detection)  # Default value
    
    def test_configuration_update_methods(self):
        """Test individual preference update methods."""
        # Test UI preferences update
        success = self.manager.update_ui_preferences(theme='dark', sidebar_width=300)
        self.assertTrue(success)
        
        config = self.manager.get_configuration()
        self.assertEqual(config.ui.theme, 'dark')
        self.assertEqual(config.ui.sidebar_width, 300)
        
        # Test analysis preferences update
        success = self.manager.update_analysis_preferences(include_hidden_files=True, max_depth=5)
        self.assertTrue(success)
        
        config = self.manager.get_configuration()
        self.assertTrue(config.analysis.include_hidden_files)
        self.assertEqual(config.analysis.max_depth, 5)
        
        # Test cleaning preferences update
        success = self.manager.update_cleaning_preferences(dry_run_by_default=False)
        self.assertTrue(success)
        
        config = self.manager.get_configuration()
        self.assertFalse(config.cleaning.dry_run_by_default)
        
        # Test monitoring preferences update
        success = self.manager.update_monitoring_preferences(update_interval=5)
        self.assertTrue(success)
        
        config = self.manager.get_configuration()
        self.assertEqual(config.monitoring.update_interval, 5)
        
        # Test reporting preferences update
        success = self.manager.update_reporting_preferences(default_format='csv')
        self.assertTrue(success)
        
        config = self.manager.get_configuration()
        self.assertEqual(config.reporting.default_format, 'csv')


class ConfigurationStateMachine(RuleBasedStateMachine):
    """Stateful testing for configuration persistence."""
    
    configurations = Bundle('configurations')
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "state_test_config.json")
        self.manager = ConfigurationManager(self.config_path)
        self.saved_configs = []
    
    def teardown(self):
        """Clean up after state machine tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @initialize()
    def initialize_config(self):
        """Initialize with default configuration."""
        config = Configuration()
        self.manager.save_configuration(config)
        # Don't return anything for initialize rule
    
    @rule(target=configurations, 
          theme=st.sampled_from(['auto', 'light', 'dark']),
          sidebar_width=st.integers(min_value=100, max_value=500))
    def update_ui_preferences(self, theme, sidebar_width):
        """Update UI preferences."""
        success = self.manager.update_ui_preferences(theme=theme, sidebar_width=sidebar_width)
        assert success, "UI preferences update should succeed"
        
        config = self.manager.get_configuration()
        assert config.ui.theme == theme
        assert config.ui.sidebar_width == sidebar_width
        
        return config
    
    @rule(target=configurations)
    def get_current_configuration(self):
        """Get current configuration for the bundle."""
        return self.manager.get_configuration()
    
    @rule(target=configurations,
          include_hidden=st.booleans(),
          max_depth=st.integers(min_value=-1, max_value=10))
    def update_analysis_preferences(self, include_hidden, max_depth):
        """Update analysis preferences."""
        success = self.manager.update_analysis_preferences(
            include_hidden_files=include_hidden,
            max_depth=max_depth
        )
        assert success, "Analysis preferences update should succeed"
        
        config = self.manager.get_configuration()
        assert config.analysis.include_hidden_files == include_hidden
        assert config.analysis.max_depth == max_depth
        
        return config
    
    @rule(config=configurations)
    def save_and_reload_configuration(self, config):
        """Save configuration and reload from disk."""
        # Save current configuration
        success = self.manager.save_configuration(config)
        assert success, "Configuration save should succeed"
        
        # Create new manager to simulate restart
        new_manager = ConfigurationManager(self.config_path)
        loaded_config = new_manager.get_configuration()
        
        # Verify configuration matches
        assert loaded_config.ui.theme == config.ui.theme
        assert loaded_config.ui.sidebar_width == config.ui.sidebar_width
        assert loaded_config.analysis.include_hidden_files == config.analysis.include_hidden_files
        assert loaded_config.analysis.max_depth == config.analysis.max_depth
    
    @invariant()
    def configuration_file_is_valid_json(self):
        """Configuration file should always be valid JSON."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)  # Should not raise exception
            assert isinstance(data, dict)
    
    @invariant()
    def configuration_has_required_fields(self):
        """Configuration should always have required fields."""
        config = self.manager.get_configuration()
        assert hasattr(config, 'ui')
        assert hasattr(config, 'analysis')
        assert hasattr(config, 'cleaning')
        assert hasattr(config, 'monitoring')
        assert hasattr(config, 'reporting')
        assert hasattr(config, 'version')
        assert hasattr(config, 'last_updated')


# Test case for state machine
TestConfigurationStateMachine = ConfigurationStateMachine.TestCase


if __name__ == '__main__':
    unittest.main()