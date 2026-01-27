"""
Tests for configuration integration functionality.

Tests the integration between configuration system and application components.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.configuration_manager import ConfigurationManager, Configuration
from config.configuration_integration import ConfigurationIntegration


class ConfigurationIntegrationTests(unittest.TestCase):
    """Tests for configuration integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.manager = ConfigurationManager(self.config_path)
        self.integration = ConfigurationIntegration(self.manager)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_callback_registration(self):
        """Test callback registration and notification."""
        ui_callback = Mock()
        global_callback = Mock()
        
        # Register callbacks
        self.integration.register_callback('ui', ui_callback)
        self.integration.register_callback('global', global_callback)
        
        # Update UI preferences
        success = self.integration.update_ui_preferences(theme='dark')
        self.assertTrue(success)
        
        # Verify callbacks were called
        ui_callback.assert_called_once()
        global_callback.assert_called_once()
        
        # Verify callback received correct configuration
        called_config = ui_callback.call_args[0][0]
        self.assertEqual(called_config.ui.theme, 'dark')
    
    def test_callback_unregistration(self):
        """Test callback unregistration."""
        callback = Mock()
        
        # Register and then unregister callback
        self.integration.register_callback('ui', callback)
        self.integration.unregister_callback('ui', callback)
        
        # Update preferences
        self.integration.update_ui_preferences(theme='light')
        
        # Callback should not be called
        callback.assert_not_called()
    
    def test_preference_getters(self):
        """Test preference getter methods."""
        # Update some preferences
        self.integration.update_ui_preferences(theme='dark', sidebar_width=300)
        self.integration.update_analysis_preferences(include_hidden_files=True)
        self.integration.update_cleaning_preferences(dry_run_by_default=False)
        self.integration.update_monitoring_preferences(update_interval=5)
        self.integration.update_reporting_preferences(default_format='csv')
        
        # Test getters
        ui_prefs = self.integration.get_ui_preferences()
        self.assertEqual(ui_prefs['theme'], 'dark')
        self.assertEqual(ui_prefs['sidebar_width'], 300)
        
        analysis_prefs = self.integration.get_analysis_preferences()
        self.assertTrue(analysis_prefs['include_hidden_files'])
        
        cleaning_prefs = self.integration.get_cleaning_preferences()
        self.assertFalse(cleaning_prefs['dry_run_by_default'])
        
        monitoring_prefs = self.integration.get_monitoring_preferences()
        self.assertEqual(monitoring_prefs['update_interval'], 5)
        
        reporting_prefs = self.integration.get_reporting_preferences()
        self.assertEqual(reporting_prefs['default_format'], 'csv')
    
    def test_feature_checks(self):
        """Test feature enabled checks."""
        # Test default values
        self.assertTrue(self.integration.is_feature_enabled('tooltips'))
        self.assertTrue(self.integration.is_feature_enabled('animations'))
        self.assertTrue(self.integration.is_feature_enabled('dry_run'))
        
        # Update preferences
        self.integration.update_ui_preferences(show_tooltips=False)
        self.integration.update_cleaning_preferences(dry_run_by_default=False)
        
        # Test updated values
        self.assertFalse(self.integration.is_feature_enabled('tooltips'))
        self.assertFalse(self.integration.is_feature_enabled('dry_run'))
    
    def test_threshold_getters(self):
        """Test threshold getter methods."""
        # Test default thresholds
        self.assertEqual(self.integration.get_threshold('disk_usage'), 85.0)
        self.assertEqual(self.integration.get_threshold('cpu_usage'), 80.0)
        self.assertEqual(self.integration.get_threshold('memory_usage'), 85.0)
        
        # Update thresholds
        self.integration.update_monitoring_preferences(
            disk_usage_threshold=90.0,
            cpu_usage_threshold=75.0
        )
        
        # Test updated thresholds
        self.assertEqual(self.integration.get_threshold('disk_usage'), 90.0)
        self.assertEqual(self.integration.get_threshold('cpu_usage'), 75.0)
        
        # Test unknown threshold
        self.assertEqual(self.integration.get_threshold('unknown'), 85.0)
    
    def test_app_cleaning_checks(self):
        """Test application cleaning enabled checks."""
        # Test default values
        self.assertTrue(self.integration.get_app_cleaning_enabled('firefox'))
        self.assertTrue(self.integration.get_app_cleaning_enabled('chrome'))
        
        # Update app cleaning preferences
        self.integration.update_cleaning_preferences(
            app_specific_cleaning={'firefox': False, 'chrome': True}
        )
        
        # Test updated values
        self.assertFalse(self.integration.get_app_cleaning_enabled('firefox'))
        self.assertTrue(self.integration.get_app_cleaning_enabled('chrome'))
        
        # Test unknown app (should default to True)
        self.assertTrue(self.integration.get_app_cleaning_enabled('unknown_app'))
    
    def test_configuration_caching(self):
        """Test configuration caching mechanism."""
        # Get initial configuration
        config1 = self.integration.get_configuration()
        version1 = self.integration.get_config_version()
        
        # Get configuration again (should be cached)
        config2 = self.integration.get_configuration()
        version2 = self.integration.get_config_version()
        
        # Should be same instance and version
        self.assertIs(config1, config2)
        self.assertEqual(version1, version2)
        
        # Update configuration
        self.integration.update_ui_preferences(theme='dark')
        
        # Get configuration again (should be new)
        config3 = self.integration.get_configuration()
        version3 = self.integration.get_config_version()
        
        # Should be different version
        self.assertGreater(version3, version2)
        self.assertEqual(config3.ui.theme, 'dark')
    
    def test_backup_restore_integration(self):
        """Test backup and restore through integration."""
        # Update configuration
        self.integration.update_ui_preferences(theme='dark', sidebar_width=350)
        
        # Create backup
        backup_path = self.integration.create_backup("integration_test")
        self.assertTrue(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Modify configuration
        self.integration.update_ui_preferences(theme='light', sidebar_width=200)
        
        # Set up callback to track restore notification
        callback = Mock()
        self.integration.register_callback('global', callback)
        
        # Restore backup
        success = self.integration.restore_backup(backup_path)
        self.assertTrue(success)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify configuration was restored
        config = self.integration.get_configuration()
        self.assertEqual(config.ui.theme, 'dark')
        self.assertEqual(config.ui.sidebar_width, 350)
    
    def test_import_export_integration(self):
        """Test import and export through integration."""
        # Update configuration
        self.integration.update_ui_preferences(theme='dark')
        self.integration.update_analysis_preferences(include_hidden_files=True)
        
        # Export configuration
        export_path = os.path.join(self.temp_dir, "export_test.json")
        success = self.integration.export_configuration(export_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_path))
        
        # Reset configuration
        success = self.integration.reset_to_defaults()
        self.assertTrue(success)
        
        # Verify reset
        config = self.integration.get_configuration()
        self.assertEqual(config.ui.theme, 'auto')  # Default
        self.assertFalse(config.analysis.include_hidden_files)  # Default
        
        # Set up callback to track import notification
        callback = Mock()
        self.integration.register_callback('global', callback)
        
        # Import configuration
        success = self.integration.import_configuration(export_path)
        self.assertTrue(success)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify configuration was imported
        config = self.integration.get_configuration()
        self.assertEqual(config.ui.theme, 'dark')
        self.assertTrue(config.analysis.include_hidden_files)
    
    def test_validation_integration(self):
        """Test configuration validation through integration."""
        # Valid configuration should have no issues
        issues = self.integration.validate_configuration()
        self.assertEqual(len(issues), 0)
        
        # Create invalid configuration
        config = self.integration.get_configuration()
        config.ui.theme = "invalid_theme"
        config.ui.sidebar_width = 50  # Too small
        
        # Validate invalid configuration
        issues = self.integration.validate_configuration()
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Invalid theme" in issue for issue in issues))
        self.assertTrue(any("Invalid sidebar width" in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()