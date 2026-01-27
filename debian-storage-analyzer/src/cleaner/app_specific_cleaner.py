# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import json
import sqlite3
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import glob

from .intelligent_cleaner import CleaningAction, CleaningResult


@dataclass
class AppCleaningProfile:
    """Profil de nettoyage pour une application"""
    app_name: str
    display_name: str
    cache_paths: List[str]
    log_paths: List[str]
    temp_paths: List[str]
    config_paths: List[str]  # Chemins de configuration (à ne pas supprimer par défaut)
    database_paths: List[str]  # Bases de données (nettoyage spécialisé)
    custom_commands: List[str]  # Commandes personnalisées de nettoyage
    safety_level: str = 'moderate'


class AppSpecificCleaner:
    """Nettoyeur spécifique par application"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.profiles = self._load_cleaning_profiles()
    
    def _load_cleaning_profiles(self) -> Dict[str, AppCleaningProfile]:
        """Charge les profils de nettoyage des applications"""
        profiles = {}
        
        # Firefox
        profiles['firefox'] = AppCleaningProfile(
            app_name='firefox',
            display_name='Mozilla Firefox',
            cache_paths=[
                '~/.cache/mozilla/firefox/*/cache2',
                '~/.mozilla/firefox/*/cache2',
                '~/.mozilla/firefox/*/startupCache',
                '~/.mozilla/firefox/*/thumbnails'
            ],
            log_paths=[
                '~/.mozilla/firefox/*/crashes',
                '~/.mozilla/firefox/*/minidumps'
            ],
            temp_paths=[
                '~/.mozilla/firefox/*/storage/temporary',
                '~/.mozilla/firefox/*/storage/default/*/cache'
            ],
            config_paths=[
                '~/.mozilla/firefox/*/prefs.js',
                '~/.mozilla/firefox/*/user.js'
            ],
            database_paths=[
                '~/.mozilla/firefox/*/places.sqlite',
                '~/.mozilla/firefox/*/cookies.sqlite',
                '~/.mozilla/firefox/*/formhistory.sqlite'
            ],
            custom_commands=[],
            safety_level='safe'
        )
        
        # Chrome/Chromium
        profiles['chrome'] = AppCleaningProfile(
            app_name='chrome',
            display_name='Google Chrome',
            cache_paths=[
                '~/.cache/google-chrome/Default/Cache',
                '~/.cache/google-chrome/Default/Code Cache',
                '~/.cache/google-chrome/Default/GPUCache',
                '~/.config/google-chrome/Default/Service Worker/CacheStorage'
            ],
            log_paths=[
                '~/.config/google-chrome/crash_dumps',
                '~/.config/google-chrome/Default/LOG'
            ],
            temp_paths=[
                '~/.config/google-chrome/Default/Storage/ext/*/def/GPUCache'
            ],
            config_paths=[
                '~/.config/google-chrome/Default/Preferences',
                '~/.config/google-chrome/Default/Bookmarks'
            ],
            database_paths=[
                '~/.config/google-chrome/Default/History',
                '~/.config/google-chrome/Default/Cookies',
                '~/.config/google-chrome/Default/Web Data'
            ],
            custom_commands=[],
            safety_level='safe'
        )
        
        profiles['chromium'] = AppCleaningProfile(
            app_name='chromium',
            display_name='Chromium',
            cache_paths=[
                '~/.cache/chromium/Default/Cache',
                '~/.cache/chromium/Default/Code Cache',
                '~/.cache/chromium/Default/GPUCache'
            ],
            log_paths=[
                '~/.config/chromium/crash_dumps'
            ],
            temp_paths=[],
            config_paths=[
                '~/.config/chromium/Default/Preferences'
            ],
            database_paths=[
                '~/.config/chromium/Default/History',
                '~/.config/chromium/Default/Cookies'
            ],
            custom_commands=[],
            safety_level='safe'
        )
        
        # VSCode
        profiles['vscode'] = AppCleaningProfile(
            app_name='vscode',
            display_name='Visual Studio Code',
            cache_paths=[
                '~/.cache/vscode-cpptools',
                '~/.vscode/extensions/*/node_modules',
                '~/.config/Code/logs',
                '~/.config/Code/CachedData'
            ],
            log_paths=[
                '~/.config/Code/logs'
            ],
            temp_paths=[
                '~/.vscode/extensions/*/out',
                '~/.vscode/extensions/*/dist'
            ],
            config_paths=[
                '~/.config/Code/User/settings.json',
                '~/.config/Code/User/keybindings.json'
            ],
            database_paths=[],
            custom_commands=[],
            safety_level='moderate'
        )
        
        # Snap applications
        profiles['snap'] = AppCleaningProfile(
            app_name='snap',
            display_name='Snap Applications',
            cache_paths=[
                '~/snap/*/common/.cache',
                '/var/lib/snapd/cache'
            ],
            log_paths=[
                '/var/log/snap*',
                '~/snap/*/common/.local/share/logs'
            ],
            temp_paths=[
                '~/snap/*/common/tmp',
                '/tmp/snap.*'
            ],
            config_paths=[],
            database_paths=[],
            custom_commands=['sudo snap refresh --list'],
            safety_level='safe'
        )
        
        # Flatpak applications
        profiles['flatpak'] = AppCleaningProfile(
            app_name='flatpak',
            display_name='Flatpak Applications',
            cache_paths=[
                '~/.var/app/*/cache',
                '~/.var/app/*/data/cache'
            ],
            log_paths=[
                '~/.var/app/*/data/logs'
            ],
            temp_paths=[
                '~/.var/app/*/tmp'
            ],
            config_paths=[
                '~/.var/app/*/config'
            ],
            database_paths=[],
            custom_commands=['flatpak uninstall --unused'],
            safety_level='safe'
        )
        
        # Python pip
        profiles['pip'] = AppCleaningProfile(
            app_name='pip',
            display_name='Python pip',
            cache_paths=[
                '~/.cache/pip',
                '~/.cache/pipenv'
            ],
            log_paths=[
                '~/.pip/pip.log'
            ],
            temp_paths=[
                '/tmp/pip-*'
            ],
            config_paths=[
                '~/.pip/pip.conf'
            ],
            database_paths=[],
            custom_commands=['pip cache purge'],
            safety_level='safe'
        )
        
        # Node.js npm
        profiles['npm'] = AppCleaningProfile(
            app_name='npm',
            display_name='Node.js npm',
            cache_paths=[
                '~/.npm/_cacache',
                '~/.npm/_logs'
            ],
            log_paths=[
                '~/.npm/_logs'
            ],
            temp_paths=[
                '/tmp/npm-*'
            ],
            config_paths=[
                '~/.npmrc'
            ],
            database_paths=[],
            custom_commands=['npm cache clean --force'],
            safety_level='safe'
        )
        
        # Docker
        profiles['docker'] = AppCleaningProfile(
            app_name='docker',
            display_name='Docker',
            cache_paths=[
                '/var/lib/docker/tmp',
                '~/.docker/buildx/cache'
            ],
            log_paths=[
                '/var/lib/docker/containers/*/logs',
                '/var/log/docker.log'
            ],
            temp_paths=[
                '/var/lib/docker/tmp'
            ],
            config_paths=[
                '~/.docker/config.json'
            ],
            database_paths=[],
            custom_commands=[
                'docker system prune -f',
                'docker image prune -f',
                'docker container prune -f'
            ],
            safety_level='moderate'
        )
        
        return profiles
    
    def get_available_applications(self) -> List[str]:
        """Retourne la liste des applications disponibles pour le nettoyage"""
        available = []
        
        for app_name, profile in self.profiles.items():
            if self._is_application_installed(profile):
                available.append(app_name)
        
        return available
    
    def _is_application_installed(self, profile: AppCleaningProfile) -> bool:
        """Vérifie si une application est installée"""
        # Vérifier les chemins de configuration
        for config_path in profile.config_paths:
            expanded_path = os.path.expanduser(config_path)
            if os.path.exists(expanded_path):
                return True
        
        # Vérifier les chemins de cache
        for cache_path in profile.cache_paths:
            expanded_path = os.path.expanduser(cache_path)
            # Utiliser glob pour les patterns avec *
            if '*' in expanded_path:
                if glob.glob(expanded_path):
                    return True
            elif os.path.exists(expanded_path):
                return True
        
        # Vérifier si l'exécutable existe
        try:
            result = subprocess.run(['which', profile.app_name], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    
    def scan_application_cleaning_opportunities(self, app_name: str) -> List[CleaningAction]:
        """Scanne les opportunités de nettoyage pour une application"""
        if app_name not in self.profiles:
            return []
        
        profile = self.profiles[app_name]
        actions = []
        
        # Scanner les caches
        actions.extend(self._scan_app_caches(profile))
        
        # Scanner les logs
        actions.extend(self._scan_app_logs(profile))
        
        # Scanner les fichiers temporaires
        actions.extend(self._scan_app_temp_files(profile))
        
        # Scanner les bases de données (nettoyage spécialisé)
        actions.extend(self._scan_app_databases(profile))
        
        # Ajouter les commandes personnalisées
        actions.extend(self._get_custom_commands(profile))
        
        return actions
    
    def _scan_app_caches(self, profile: AppCleaningProfile) -> List[CleaningAction]:
        """Scanne les caches d'une application"""
        actions = []
        
        for cache_path in profile.cache_paths:
            expanded_path = os.path.expanduser(cache_path)
            
            # Gérer les patterns avec *
            if '*' in expanded_path:
                matching_paths = glob.glob(expanded_path)
                for path in matching_paths:
                    if os.path.exists(path):
                        size = self._get_path_size(path)
                        if size > 1024 * 1024:  # Plus de 1MB
                            actions.append(CleaningAction(
                                action_type='clear_cache',
                                target_path=path,
                                size_bytes=size,
                                description=f"Vider le cache {profile.display_name}: {os.path.basename(path)}",
                                safety_level=profile.safety_level,
                                category='app_cache',
                                reversible=False
                            ))
            else:
                if os.path.exists(expanded_path):
                    size = self._get_path_size(expanded_path)
                    if size > 1024 * 1024:  # Plus de 1MB
                        actions.append(CleaningAction(
                            action_type='clear_cache',
                            target_path=expanded_path,
                            size_bytes=size,
                            description=f"Vider le cache {profile.display_name}",
                            safety_level=profile.safety_level,
                            category='app_cache',
                            reversible=False
                        ))
        
        return actions
    
    def _scan_app_logs(self, profile: AppCleaningProfile) -> List[CleaningAction]:
        """Scanne les logs d'une application"""
        actions = []
        cutoff_date = datetime.now() - timedelta(days=30)  # Logs de plus de 30 jours
        
        for log_path in profile.log_paths:
            expanded_path = os.path.expanduser(log_path)
            
            if '*' in expanded_path:
                matching_paths = glob.glob(expanded_path)
                for path in matching_paths:
                    if os.path.isfile(path):
                        try:
                            stat = os.stat(path)
                            file_date = datetime.fromtimestamp(stat.st_mtime)
                            
                            if file_date < cutoff_date and stat.st_size > 1024:
                                actions.append(CleaningAction(
                                    action_type='delete_file',
                                    target_path=path,
                                    size_bytes=stat.st_size,
                                    description=f"Supprimer ancien log {profile.display_name}: {os.path.basename(path)}",
                                    safety_level=profile.safety_level,
                                    category='app_logs',
                                    reversible=True
                                ))
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            else:
                if os.path.isfile(expanded_path):
                    try:
                        stat = os.stat(expanded_path)
                        file_date = datetime.fromtimestamp(stat.st_mtime)
                        
                        if file_date < cutoff_date and stat.st_size > 1024:
                            actions.append(CleaningAction(
                                action_type='delete_file',
                                target_path=expanded_path,
                                size_bytes=stat.st_size,
                                description=f"Supprimer ancien log {profile.display_name}",
                                safety_level=profile.safety_level,
                                category='app_logs',
                                reversible=True
                            ))
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
                elif os.path.isdir(expanded_path):
                    # Scanner le répertoire de logs
                    try:
                        for item in os.listdir(expanded_path):
                            item_path = os.path.join(expanded_path, item)
                            if os.path.isfile(item_path):
                                stat = os.stat(item_path)
                                file_date = datetime.fromtimestamp(stat.st_mtime)
                                
                                if file_date < cutoff_date and stat.st_size > 1024:
                                    actions.append(CleaningAction(
                                        action_type='delete_file',
                                        target_path=item_path,
                                        size_bytes=stat.st_size,
                                        description=f"Supprimer ancien log {profile.display_name}: {item}",
                                        safety_level=profile.safety_level,
                                        category='app_logs',
                                        reversible=True
                                    ))
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        
        return actions
    
    def _scan_app_temp_files(self, profile: AppCleaningProfile) -> List[CleaningAction]:
        """Scanne les fichiers temporaires d'une application"""
        actions = []
        
        for temp_path in profile.temp_paths:
            expanded_path = os.path.expanduser(temp_path)
            
            if '*' in expanded_path:
                matching_paths = glob.glob(expanded_path)
                for path in matching_paths:
                    if os.path.exists(path):
                        size = self._get_path_size(path)
                        if size > 0:
                            action_type = 'delete_directory' if os.path.isdir(path) else 'delete_file'
                            actions.append(CleaningAction(
                                action_type=action_type,
                                target_path=path,
                                size_bytes=size,
                                description=f"Supprimer fichiers temporaires {profile.display_name}: {os.path.basename(path)}",
                                safety_level=profile.safety_level,
                                category='app_temp',
                                reversible=False
                            ))
            else:
                if os.path.exists(expanded_path):
                    size = self._get_path_size(expanded_path)
                    if size > 0:
                        action_type = 'delete_directory' if os.path.isdir(expanded_path) else 'delete_file'
                        actions.append(CleaningAction(
                            action_type=action_type,
                            target_path=expanded_path,
                            size_bytes=size,
                            description=f"Supprimer fichiers temporaires {profile.display_name}",
                            safety_level=profile.safety_level,
                            category='app_temp',
                            reversible=False
                        ))
        
        return actions
    
    def _scan_app_databases(self, profile: AppCleaningProfile) -> List[CleaningAction]:
        """Scanne les bases de données d'une application pour nettoyage spécialisé"""
        actions = []
        
        for db_path in profile.database_paths:
            expanded_path = os.path.expanduser(db_path)
            
            if '*' in expanded_path:
                matching_paths = glob.glob(expanded_path)
                for path in matching_paths:
                    if os.path.isfile(path) and path.endswith('.sqlite'):
                        # Nettoyage spécialisé SQLite
                        vacuum_size = self._estimate_sqlite_vacuum_savings(path)
                        if vacuum_size > 1024 * 1024:  # Plus de 1MB à récupérer
                            actions.append(CleaningAction(
                                action_type='vacuum_database',
                                target_path=path,
                                size_bytes=vacuum_size,
                                description=f"Optimiser base de données {profile.display_name}: {os.path.basename(path)}",
                                safety_level='moderate',
                                category='app_database',
                                reversible=True
                            ))
            else:
                if os.path.isfile(expanded_path) and expanded_path.endswith('.sqlite'):
                    vacuum_size = self._estimate_sqlite_vacuum_savings(expanded_path)
                    if vacuum_size > 1024 * 1024:
                        actions.append(CleaningAction(
                            action_type='vacuum_database',
                            target_path=expanded_path,
                            size_bytes=vacuum_size,
                            description=f"Optimiser base de données {profile.display_name}",
                            safety_level='moderate',
                            category='app_database',
                            reversible=True
                        ))
        
        return actions
    
    def _get_custom_commands(self, profile: AppCleaningProfile) -> List[CleaningAction]:
        """Génère les actions pour les commandes personnalisées"""
        actions = []
        
        for command in profile.custom_commands:
            # Estimer la taille potentielle (difficile à calculer précisément)
            estimated_size = 10 * 1024 * 1024  # 10MB par défaut
            
            actions.append(CleaningAction(
                action_type='custom_command',
                target_path=command,
                size_bytes=estimated_size,
                description=f"Exécuter commande de nettoyage {profile.display_name}: {command}",
                safety_level=profile.safety_level,
                category='app_custom',
                reversible=False
            ))
        
        return actions
    
    def _get_path_size(self, path: str) -> int:
        """Calcule la taille d'un fichier ou répertoire"""
        if os.path.isfile(path):
            try:
                return os.path.getsize(path)
            except (PermissionError, FileNotFoundError, OSError):
                return 0
        elif os.path.isdir(path):
            total_size = 0
            try:
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except (PermissionError, FileNotFoundError):
                pass
            return total_size
        else:
            return 0
    
    def _estimate_sqlite_vacuum_savings(self, db_path: str) -> int:
        """Estime les économies d'espace d'un VACUUM SQLite"""
        try:
            # Calculer la taille actuelle
            current_size = os.path.getsize(db_path)
            
            # Se connecter à la base pour obtenir des statistiques
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtenir le nombre de pages libres
            cursor.execute("PRAGMA freelist_count")
            free_pages = cursor.fetchone()[0]
            
            # Obtenir la taille de page
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            conn.close()
            
            # Estimer les économies (pages libres * taille de page)
            estimated_savings = free_pages * page_size
            
            # Limiter à 50% de la taille actuelle maximum
            return min(estimated_savings, current_size // 2)
        
        except (sqlite3.Error, PermissionError, FileNotFoundError, OSError):
            return 0
    
    def execute_app_cleaning_action(self, action: CleaningAction) -> CleaningResult:
        """Exécute une action de nettoyage spécifique à une application"""
        if self.dry_run:
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=action.size_bytes
            )
        
        try:
            if action.action_type == 'vacuum_database':
                return self._vacuum_sqlite_database(action)
            elif action.action_type == 'custom_command':
                return self._execute_custom_command(action)
            else:
                # Utiliser les méthodes standard de nettoyage
                from .intelligent_cleaner import IntelligentCleaner
                cleaner = IntelligentCleaner(dry_run=False)
                return cleaner._execute_single_action(action)
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _vacuum_sqlite_database(self, action: CleaningAction) -> CleaningResult:
        """Optimise une base de données SQLite"""
        try:
            # Taille avant
            size_before = os.path.getsize(action.target_path)
            
            # Créer une sauvegarde
            backup_path = f"{action.target_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(action.target_path, backup_path)
            
            # Exécuter VACUUM
            conn = sqlite3.connect(action.target_path)
            conn.execute("VACUUM")
            conn.close()
            
            # Taille après
            size_after = os.path.getsize(action.target_path)
            actual_savings = size_before - size_after
            
            # Supprimer la sauvegarde si tout s'est bien passé
            os.remove(backup_path)
            
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=actual_savings
            )
        
        except (sqlite3.Error, PermissionError, FileNotFoundError, OSError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _execute_custom_command(self, action: CleaningAction) -> CleaningResult:
        """Exécute une commande personnalisée"""
        try:
            command_parts = action.target_path.split()
            result = subprocess.run(command_parts, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return CleaningResult(
                    action=action,
                    success=True,
                    actual_size_freed=action.size_bytes  # Estimation
                )
            else:
                return CleaningResult(
                    action=action,
                    success=False,
                    error_message=result.stderr
                )
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def get_application_info(self, app_name: str) -> Optional[Dict]:
        """Retourne les informations sur une application"""
        if app_name not in self.profiles:
            return None
        
        profile = self.profiles[app_name]
        
        return {
            'name': profile.app_name,
            'display_name': profile.display_name,
            'installed': self._is_application_installed(profile),
            'safety_level': profile.safety_level,
            'cache_paths_count': len(profile.cache_paths),
            'log_paths_count': len(profile.log_paths),
            'temp_paths_count': len(profile.temp_paths),
            'database_paths_count': len(profile.database_paths),
            'custom_commands_count': len(profile.custom_commands)
        }
    
    def add_custom_profile(self, profile: AppCleaningProfile):
        """Ajoute un profil de nettoyage personnalisé"""
        self.profiles[profile.app_name] = profile
    
    def remove_profile(self, app_name: str) -> bool:
        """Supprime un profil de nettoyage"""
        if app_name in self.profiles:
            del self.profiles[app_name]
            return True
        return False