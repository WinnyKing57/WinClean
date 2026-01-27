"""
Configuration Integration for Debian Storage Analyzer.

Provides integration between configuration system and application components,
enabling seamless configuration updates and notifications.
"""

import logging
from typing import Dict, Any, Callable, List, Optional
from threading import Lock

from .configuration_manager import ConfigurationManager, Configuration


class ConfigurationIntegration:
    """
    Integrates configuration system with application components.
    
    Features:
    - Configuration change notifications
    - Component registration and callbacks
    - Thread-safe configuration updates
    - Automatic configuration propagation
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        """Initialize configuration integration."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Component callbacks
        self._callbacks: Dict[str, List[Callable[[Configuration], None]]] = {
            'ui': [],
            'analysis': [],
            'cleaning': [],
            'monitoring': [],
            'reporting': [],
            'global': []  # Called for any configuration change
        }
        
        # Thread safety
        self._lock = Lock()
        
        # Current configuration cache
        self._cached_config: Optional[Configuration] = None
        self._config_version = 0
    
    def register_callback(self, category: str, callback: Callable[[Configuration], None]):
        """
        Register a callback for configuration changes.
        
        Args:
            category: Configuration category ('ui', 'analysis', 'cleaning', 
                     'monitoring', 'reporting', or 'global')
            callback: Function to call when configuration changes
        """
        with self._lock:
            if category not in self._callbacks:
                self.logger.warning(f"Unknown configuration category: {category}")
                category = 'global'
            
            self._callbacks[category].append(callback)
            self.logger.debug(f"Registered callback for category: {category}")
    
    def unregister_callback(self, category: str, callback: Callable[[Configuration], None]):
        """Unregister a configuration callback."""
        with self._lock:
            if category in self._callbacks and callback in self._callbacks[category]:
                self._callbacks[category].remove(callback)
                self.logger.debug(f"Unregistered callback for category: {category}")
    
    def get_configuration(self) -> Configuration:
        """Get current configuration with caching."""
        with self._lock:
            current_config = self.config_manager.get_configuration()
            
            # Update cache if configuration changed
            if (self._cached_config is None or 
                current_config.last_updated != self._cached_config.last_updated):
                self._cached_config = current_config
                self._config_version += 1
            
            return self._cached_config
    
    def update_ui_preferences(self, **kwargs) -> bool:
        """Update UI preferences and notify callbacks."""
        success = self.config_manager.update_ui_preferences(**kwargs)
        if success:
            self._notify_callbacks('ui')
        return success
    
    def update_analysis_preferences(self, **kwargs) -> bool:
        """Update analysis preferences and notify callbacks."""
        success = self.config_manager.update_analysis_preferences(**kwargs)
        if success:
            self._notify_callbacks('analysis')
        return success
    
    def update_cleaning_preferences(self, **kwargs) -> bool:
        """Update cleaning preferences and notify callbacks."""
        success = self.config_manager.update_cleaning_preferences(**kwargs)
        if success:
            self._notify_callbacks('cleaning')
        return success
    
    def update_monitoring_preferences(self, **kwargs) -> bool:
        """Update monitoring preferences and notify callbacks."""
        success = self.config_manager.update_monitoring_preferences(**kwargs)
        if success:
            self._notify_callbacks('monitoring')
        return success
    
    def update_reporting_preferences(self, **kwargs) -> bool:
        """Update reporting preferences and notify callbacks."""
        success = self.config_manager.update_reporting_preferences(**kwargs)
        if success:
            self._notify_callbacks('reporting')
        return success
    
    def save_configuration(self, config: Configuration) -> bool:
        """Save configuration and notify all callbacks."""
        success = self.config_manager.save_configuration(config)
        if success:
            self._notify_callbacks('global')
        return success
    
    def create_backup(self, name: Optional[str] = None) -> str:
        """Create configuration backup."""
        return self.config_manager.create_backup(name)
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore configuration from backup and notify callbacks."""
        success = self.config_manager.restore_backup(backup_path)
        if success:
            self._notify_callbacks('global')
        return success
    
    def export_configuration(self, export_path: str) -> bool:
        """Export configuration to file."""
        return self.config_manager.export_configuration(export_path)
    
    def import_configuration(self, import_path: str) -> bool:
        """Import configuration from file and notify callbacks."""
        success = self.config_manager.import_configuration(import_path)
        if success:
            self._notify_callbacks('global')
        return success
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults and notify callbacks."""
        success = self.config_manager.reset_to_defaults()
        if success:
            self._notify_callbacks('global')
        return success
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration."""
        return self.config_manager.validate_configuration()
    
    def get_ui_preferences(self) -> Dict[str, Any]:
        """Get UI preferences as dictionary."""
        config = self.get_configuration()
        return {
            'theme': config.ui.theme,
            'sidebar_width': config.ui.sidebar_width,
            'window_width': config.ui.window_width,
            'window_height': config.ui.window_height,
            'show_tooltips': config.ui.show_tooltips,
            'animation_enabled': config.ui.animation_enabled,
            'language': config.ui.language
        }
    
    def get_analysis_preferences(self) -> Dict[str, Any]:
        """Get analysis preferences as dictionary."""
        config = self.get_configuration()
        return {
            'default_directories': config.analysis.default_directories,
            'include_hidden_files': config.analysis.include_hidden_files,
            'follow_symlinks': config.analysis.follow_symlinks,
            'max_depth': config.analysis.max_depth,
            'file_size_threshold': config.analysis.file_size_threshold,
            'enable_duplicate_detection': config.analysis.enable_duplicate_detection,
            'hash_algorithm': config.analysis.hash_algorithm
        }
    
    def get_cleaning_preferences(self) -> Dict[str, Any]:
        """Get cleaning preferences as dictionary."""
        config = self.get_configuration()
        return {
            'dry_run_by_default': config.cleaning.dry_run_by_default,
            'confirm_before_delete': config.cleaning.confirm_before_delete,
            'backup_before_clean': config.cleaning.backup_before_clean,
            'backup_retention_days': config.cleaning.backup_retention_days,
            'excluded_paths': config.cleaning.excluded_paths,
            'app_specific_cleaning': config.cleaning.app_specific_cleaning
        }
    
    def get_monitoring_preferences(self) -> Dict[str, Any]:
        """Get monitoring preferences as dictionary."""
        config = self.get_configuration()
        return {
            'enable_realtime': config.monitoring.enable_realtime,
            'update_interval': config.monitoring.update_interval,
            'enable_notifications': config.monitoring.enable_notifications,
            'notification_cooldown': config.monitoring.notification_cooldown,
            'disk_usage_threshold': config.monitoring.disk_usage_threshold,
            'cpu_usage_threshold': config.monitoring.cpu_usage_threshold,
            'memory_usage_threshold': config.monitoring.memory_usage_threshold
        }
    
    def get_reporting_preferences(self) -> Dict[str, Any]:
        """Get reporting preferences as dictionary."""
        config = self.get_configuration()
        return {
            'default_format': config.reporting.default_format,
            'include_charts': config.reporting.include_charts,
            'chart_style': config.reporting.chart_style,
            'export_directory': config.reporting.export_directory,
            'auto_save_reports': config.reporting.auto_save_reports
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled."""
        config = self.get_configuration()
        
        feature_map = {
            'tooltips': config.ui.show_tooltips,
            'animations': config.ui.animation_enabled,
            'hidden_files': config.analysis.include_hidden_files,
            'symlinks': config.analysis.follow_symlinks,
            'duplicate_detection': config.analysis.enable_duplicate_detection,
            'dry_run': config.cleaning.dry_run_by_default,
            'confirm_delete': config.cleaning.confirm_before_delete,
            'backup_before_clean': config.cleaning.backup_before_clean,
            'realtime_monitoring': config.monitoring.enable_realtime,
            'notifications': config.monitoring.enable_notifications,
            'include_charts': config.reporting.include_charts,
            'auto_save_reports': config.reporting.auto_save_reports
        }
        
        return feature_map.get(feature, False)
    
    def get_threshold(self, threshold_type: str) -> float:
        """Get monitoring threshold value."""
        config = self.get_configuration()
        
        threshold_map = {
            'disk_usage': config.monitoring.disk_usage_threshold,
            'cpu_usage': config.monitoring.cpu_usage_threshold,
            'memory_usage': config.monitoring.memory_usage_threshold
        }
        
        return threshold_map.get(threshold_type, 85.0)
    
    def get_app_cleaning_enabled(self, app: str) -> bool:
        """Check if cleaning is enabled for specific application."""
        config = self.get_configuration()
        return config.cleaning.app_specific_cleaning.get(app, True)
    
    def get_config_version(self) -> int:
        """Get current configuration version for change detection."""
        with self._lock:
            return self._config_version
    
    def _notify_callbacks(self, category: str):
        """Notify callbacks for configuration changes."""
        try:
            with self._lock:
                # Clear cache to force reload
                self._cached_config = None
                
                # Get updated configuration
                config = self.get_configuration()
                
                # Notify category-specific callbacks
                if category in self._callbacks:
                    for callback in self._callbacks[category]:
                        try:
                            callback(config)
                        except Exception as e:
                            self.logger.error(f"Error in {category} callback: {e}")
                
                # Notify global callbacks
                for callback in self._callbacks['global']:
                    try:
                        callback(config)
                    except Exception as e:
                        self.logger.error(f"Error in global callback: {e}")
                
                self.logger.debug(f"Notified callbacks for category: {category}")
                
        except Exception as e:
            self.logger.error(f"Error notifying callbacks: {e}")


class ConfigurationWatcher:
    """
    Watches for external configuration file changes.
    
    Useful for detecting configuration changes made outside the application.
    """
    
    def __init__(self, integration: ConfigurationIntegration):
        """Initialize configuration watcher."""
        self.logger = logging.getLogger(__name__)
        self.integration = integration
        self._watching = False
        self._last_modified = None
    
    def start_watching(self):
        """Start watching for configuration file changes."""
        # Implementation would use file system monitoring
        # For now, this is a placeholder
        self._watching = True
        self.logger.info("Configuration file watching started")
    
    def stop_watching(self):
        """Stop watching for configuration file changes."""
        self._watching = False
        self.logger.info("Configuration file watching stopped")
    
    def check_for_changes(self):
        """Check for configuration file changes."""
        # Implementation would check file modification time
        # and trigger reload if changed
        pass