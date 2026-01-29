"""
Configuration management module for Debian Storage Analyzer.

This module provides comprehensive configuration management including:
- JSON-based settings persistence
- User preferences for UI, analysis, cleaning, and monitoring
- Backup and restore functionality
- Configuration validation and migration
"""

from .configuration_manager import ConfigurationManager
from .configuration_ui import ConfigurationUI
from .configuration_integration import ConfigurationIntegration

__all__ = [
    'ConfigurationManager',
    'ConfigurationUI', 
    'ConfigurationIntegration'
]