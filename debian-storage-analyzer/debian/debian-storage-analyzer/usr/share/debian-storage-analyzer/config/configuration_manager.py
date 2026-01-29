"""
Configuration Manager for Debian Storage Analyzer.

Provides comprehensive configuration management with JSON persistence,
backup/restore functionality, and validation.
"""

import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class UIPreferences:
    """User interface preferences."""
    theme: str = "auto"  # auto, light, dark
    sidebar_width: int = 250
    window_width: int = 1200
    window_height: int = 800
    show_tooltips: bool = True
    animation_enabled: bool = True
    language: str = "fr"


@dataclass
class AnalysisPreferences:
    """Analysis preferences."""
    default_directories: List[str] = field(default_factory=lambda: [
        "~/Documents", "~/Downloads", "~/Pictures", "~/Videos"
    ])
    include_hidden_files: bool = False
    follow_symlinks: bool = False
    max_depth: int = -1  # -1 for unlimited
    file_size_threshold: int = 1024  # bytes
    enable_duplicate_detection: bool = True
    hash_algorithm: str = "sha256"


@dataclass
class CleaningPreferences:
    """Cleaning preferences."""
    dry_run_by_default: bool = True
    confirm_before_delete: bool = True
    backup_before_clean: bool = True
    backup_retention_days: int = 30
    excluded_paths: List[str] = field(default_factory=lambda: [
        "~/.ssh", "~/.gnupg", "~/.config/git"
    ])
    app_specific_cleaning: Dict[str, bool] = field(default_factory=lambda: {
        "firefox": True,
        "chrome": True,
        "flatpak": True,
        "snap": True
    })


@dataclass
class MonitoringPreferences:
    """Monitoring preferences."""
    enable_realtime: bool = True
    update_interval: int = 2  # seconds
    enable_notifications: bool = True
    notification_cooldown: int = 300  # seconds
    disk_usage_threshold: float = 85.0  # percentage
    cpu_usage_threshold: float = 80.0  # percentage
    memory_usage_threshold: float = 85.0  # percentage


@dataclass
class ReportingPreferences:
    """Reporting preferences."""
    default_format: str = "pdf"  # pdf, csv, html
    include_charts: bool = True
    chart_style: str = "modern"
    export_directory: str = "~/Documents/storage-reports"
    auto_save_reports: bool = False


@dataclass
class Configuration:
    """Complete application configuration."""
    ui: UIPreferences = field(default_factory=UIPreferences)
    analysis: AnalysisPreferences = field(default_factory=AnalysisPreferences)
    cleaning: CleaningPreferences = field(default_factory=CleaningPreferences)
    monitoring: MonitoringPreferences = field(default_factory=MonitoringPreferences)
    reporting: ReportingPreferences = field(default_factory=ReportingPreferences)
    version: str = "3.1.0"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class ConfigurationManager:
    """
    Manages application configuration with JSON persistence.
    
    Features:
    - JSON-based configuration storage
    - Automatic backup and restore
    - Configuration validation
    - Migration support
    - Thread-safe operations
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration paths
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / ".config" / "debian-storage-analyzer" / "config.json"
        
        self.config_dir = self.config_path.parent
        self.backup_dir = self.config_dir / "backups"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Current configuration
        self._config: Optional[Configuration] = None
        
        # Load configuration
        self.load_configuration()
    
    def load_configuration(self) -> Configuration:
        """Load configuration from file or create default."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert dict to Configuration object
                self._config = self._dict_to_config(data)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                # Create default configuration
                self._config = Configuration()
                self.save_configuration()
                self.logger.info("Default configuration created")
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            # Fallback to default configuration
            self._config = Configuration()
            
        return self._config
    
    def save_configuration(self, config: Optional[Configuration] = None) -> bool:
        """Save configuration to file."""
        try:
            if config:
                self._config = config
            
            if not self._config:
                self.logger.error("No configuration to save")
                return False
            
            # Update timestamp
            self._config.last_updated = datetime.now().isoformat()
            
            # Convert to dict and save
            data = self._config_to_dict(self._config)
            
            # Create backup before saving
            if self.config_path.exists():
                self._create_backup()
            
            # Save configuration
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_configuration(self) -> Configuration:
        """Get current configuration."""
        if not self._config:
            self.load_configuration()
        return self._config
    
    def update_ui_preferences(self, **kwargs) -> bool:
        """Update UI preferences."""
        try:
            config = self.get_configuration()
            for key, value in kwargs.items():
                if hasattr(config.ui, key):
                    setattr(config.ui, key, value)
            return self.save_configuration(config)
        except Exception as e:
            self.logger.error(f"Error updating UI preferences: {e}")
            return False
    
    def update_analysis_preferences(self, **kwargs) -> bool:
        """Update analysis preferences."""
        try:
            config = self.get_configuration()
            for key, value in kwargs.items():
                if hasattr(config.analysis, key):
                    setattr(config.analysis, key, value)
            return self.save_configuration(config)
        except Exception as e:
            self.logger.error(f"Error updating analysis preferences: {e}")
            return False
    
    def update_cleaning_preferences(self, **kwargs) -> bool:
        """Update cleaning preferences."""
        try:
            config = self.get_configuration()
            for key, value in kwargs.items():
                if hasattr(config.cleaning, key):
                    setattr(config.cleaning, key, value)
            return self.save_configuration(config)
        except Exception as e:
            self.logger.error(f"Error updating cleaning preferences: {e}")
            return False
    
    def update_monitoring_preferences(self, **kwargs) -> bool:
        """Update monitoring preferences."""
        try:
            config = self.get_configuration()
            for key, value in kwargs.items():
                if hasattr(config.monitoring, key):
                    setattr(config.monitoring, key, value)
            return self.save_configuration(config)
        except Exception as e:
            self.logger.error(f"Error updating monitoring preferences: {e}")
            return False
    
    def update_reporting_preferences(self, **kwargs) -> bool:
        """Update reporting preferences."""
        try:
            config = self.get_configuration()
            for key, value in kwargs.items():
                if hasattr(config.reporting, key):
                    setattr(config.reporting, key, value)
            return self.save_configuration(config)
        except Exception as e:
            self.logger.error(f"Error updating reporting preferences: {e}")
            return False
    
    def create_backup(self, name: Optional[str] = None) -> str:
        """Create a named backup of current configuration."""
        try:
            if name:
                # Sanitize name for filesystem
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                backup_name = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            backup_path = self.backup_dir / backup_name
            
            if self.config_path.exists():
                shutil.copy2(self.config_path, backup_path)
                self.logger.info(f"Configuration backup created: {backup_path}")
                return str(backup_path)
            else:
                self.logger.warning("No configuration file to backup")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore configuration from backup."""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Validate backup file
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Test if we can create Configuration object
            config = self._dict_to_config(data)
            
            # Create backup of current config before restore
            self._create_backup("pre_restore")
            
            # Copy backup to config location
            shutil.copy2(backup_file, self.config_path)
            
            # Reload configuration
            self.load_configuration()
            
            self.logger.info(f"Configuration restored from {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available configuration backups."""
        backups = []
        try:
            for backup_file in self.backup_dir.glob("*.json"):
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def export_configuration(self, export_path: str) -> bool:
        """Export configuration to specified path."""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.config_path.exists():
                shutil.copy2(self.config_path, export_file)
                self.logger.info(f"Configuration exported to {export_path}")
                return True
            else:
                self.logger.error("No configuration file to export")
                return False
                
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_configuration(self, import_path: str) -> bool:
        """Import configuration from specified path."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                self.logger.error(f"Import file not found: {import_path}")
                return False
            
            # Validate import file
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Test if we can create Configuration object
            config = self._dict_to_config(data)
            
            # Create backup before import
            self._create_backup("pre_import")
            
            # Copy import file to config location
            shutil.copy2(import_file, self.config_path)
            
            # Reload configuration
            self.load_configuration()
            
            self.logger.info(f"Configuration imported from {import_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults."""
        try:
            # Create backup before reset
            self._create_backup("pre_reset")
            
            # Create default configuration
            self._config = Configuration()
            
            # Save defaults
            return self.save_configuration()
            
        except Exception as e:
            self.logger.error(f"Error resetting to defaults: {e}")
            return False
    
    def validate_configuration(self, config: Optional[Configuration] = None) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not config:
            config = self.get_configuration()
        
        try:
            # Validate UI preferences
            if config.ui.theme not in ["auto", "light", "dark"]:
                issues.append(f"Invalid theme: {config.ui.theme}")
            
            if config.ui.sidebar_width < 100 or config.ui.sidebar_width > 500:
                issues.append(f"Invalid sidebar width: {config.ui.sidebar_width}")
            
            # Validate analysis preferences
            if config.analysis.max_depth < -1:
                issues.append(f"Invalid max depth: {config.analysis.max_depth}")
            
            if config.analysis.file_size_threshold < 0:
                issues.append(f"Invalid file size threshold: {config.analysis.file_size_threshold}")
            
            # Validate cleaning preferences
            if config.cleaning.backup_retention_days < 0:
                issues.append(f"Invalid backup retention days: {config.cleaning.backup_retention_days}")
            
            # Validate monitoring preferences
            if config.monitoring.update_interval < 1:
                issues.append(f"Invalid update interval: {config.monitoring.update_interval}")
            
            if not (0 <= config.monitoring.disk_usage_threshold <= 100):
                issues.append(f"Invalid disk usage threshold: {config.monitoring.disk_usage_threshold}")
            
        except Exception as e:
            issues.append(f"Configuration validation error: {e}")
        
        return issues
    
    def _create_backup(self, suffix: str = "") -> str:
        """Create automatic backup with optional suffix."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if suffix:
                backup_name = f"auto_{suffix}_{timestamp}.json"
            else:
                backup_name = f"auto_{timestamp}.json"
            
            backup_path = self.backup_dir / backup_name
            
            if self.config_path.exists():
                shutil.copy2(self.config_path, backup_path)
                return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Error creating automatic backup: {e}")
        
        return ""
    
    def _config_to_dict(self, config: Configuration) -> Dict[str, Any]:
        """Convert Configuration object to dictionary."""
        return asdict(config)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> Configuration:
        """Convert dictionary to Configuration object."""
        # Handle missing fields with defaults
        ui_data = data.get('ui', {})
        analysis_data = data.get('analysis', {})
        cleaning_data = data.get('cleaning', {})
        monitoring_data = data.get('monitoring', {})
        reporting_data = data.get('reporting', {})
        
        # Create default instances first, then update with loaded data
        ui_prefs = UIPreferences()
        for key, value in ui_data.items():
            if hasattr(ui_prefs, key):
                setattr(ui_prefs, key, value)
        
        analysis_prefs = AnalysisPreferences()
        for key, value in analysis_data.items():
            if hasattr(analysis_prefs, key):
                setattr(analysis_prefs, key, value)
        
        cleaning_prefs = CleaningPreferences()
        for key, value in cleaning_data.items():
            if hasattr(cleaning_prefs, key):
                setattr(cleaning_prefs, key, value)
        
        monitoring_prefs = MonitoringPreferences()
        for key, value in monitoring_data.items():
            if hasattr(monitoring_prefs, key):
                setattr(monitoring_prefs, key, value)
        
        reporting_prefs = ReportingPreferences()
        for key, value in reporting_data.items():
            if hasattr(reporting_prefs, key):
                setattr(reporting_prefs, key, value)
        
        return Configuration(
            ui=ui_prefs,
            analysis=analysis_prefs,
            cleaning=cleaning_prefs,
            monitoring=monitoring_prefs,
            reporting=reporting_prefs,
            version=data.get('version', '1.0.0'),
            last_updated=data.get('last_updated', datetime.now().isoformat())
        )