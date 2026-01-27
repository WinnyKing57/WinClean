# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import logging


@dataclass
class CleaningAction:
    """Action de nettoyage à effectuer"""
    action_type: str  # 'delete_file', 'delete_directory', 'clear_cache', 'remove_package'
    target_path: str
    size_bytes: int
    description: str
    safety_level: str  # 'safe', 'moderate', 'risky'
    category: str  # 'cache', 'logs', 'temp', 'duplicates', 'packages'
    reversible: bool = False
    backup_path: Optional[str] = None


@dataclass
class CleaningResult:
    """Résultat d'une opération de nettoyage"""
    action: CleaningAction
    success: bool
    error_message: Optional[str] = None
    actual_size_freed: int = 0
    execution_time: float = 0.0


class IntelligentCleaner:
    """Nettoyeur intelligent avec mode dry-run et sécurité"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        self.backup_dir = os.path.expanduser("~/.cache/debian-storage-analyzer/backups")
        self.config = self._load_config()
        
        # Créer le répertoire de sauvegarde si nécessaire
        if not self.dry_run:
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Charge la configuration de nettoyage"""
        default_config = {
            'max_backup_age_days': 30,
            'max_backup_size_mb': 1000,
            'safe_directories': [
                '~/.cache/thumbnails',
                '~/.cache/mozilla',
                '~/.cache/chromium',
                '/tmp',
                '/var/tmp',
                '/var/log'
            ],
            'protected_directories': [
                '~/.ssh',
                '~/.gnupg',
                '~/Documents',
                '~/Pictures',
                '~/Videos',
                '~/Music'
            ],
            'max_file_age_days': {
                'cache': 30,
                'logs': 90,
                'temp': 7,
                'downloads': 365
            }
        }
        
        config_path = os.path.expanduser("~/.config/debian-storage-analyzer/cleaning.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
        
        return default_config
    
    def scan_for_cleaning_opportunities(self, directories: List[str] = None) -> List[CleaningAction]:
        """Scanne les opportunités de nettoyage"""
        if directories is None:
            directories = [os.path.expanduser(d) for d in self.config['safe_directories']]
        
        actions = []
        
        # Scanner les différents types de nettoyage
        actions.extend(self._scan_cache_directories(directories))
        actions.extend(self._scan_log_files(directories))
        actions.extend(self._scan_temp_files(directories))
        actions.extend(self._scan_old_downloads())
        actions.extend(self._scan_package_caches())
        
        # Trier par taille décroissante
        actions.sort(key=lambda a: a.size_bytes, reverse=True)
        
        return actions
    
    def _scan_cache_directories(self, directories: List[str]) -> List[CleaningAction]:
        """Scanne les répertoires de cache"""
        actions = []
        cache_dirs = [
            '~/.cache/thumbnails',
            '~/.cache/mozilla/firefox',
            '~/.cache/chromium',
            '~/.cache/google-chrome',
            '~/.cache/pip',
            '~/.npm/_cacache'
        ]
        
        for cache_dir in cache_dirs:
            expanded_dir = os.path.expanduser(cache_dir)
            if os.path.exists(expanded_dir):
                try:
                    total_size = self._get_directory_size(expanded_dir)
                    if total_size > 10 * 1024 * 1024:  # Plus de 10MB
                        actions.append(CleaningAction(
                            action_type='clear_cache',
                            target_path=expanded_dir,
                            size_bytes=total_size,
                            description=f"Vider le cache {os.path.basename(cache_dir)}",
                            safety_level='safe',
                            category='cache',
                            reversible=False
                        ))
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_log_files(self, directories: List[str]) -> List[CleaningAction]:
        """Scanne les fichiers de logs anciens"""
        actions = []
        log_dirs = ['/var/log', '~/.local/share/logs']
        
        cutoff_date = datetime.now() - timedelta(days=self.config['max_file_age_days']['logs'])
        
        for log_dir in log_dirs:
            expanded_dir = os.path.expanduser(log_dir)
            if os.path.exists(expanded_dir):
                try:
                    for root, dirs, files in os.walk(expanded_dir):
                        for file in files:
                            if file.endswith(('.log', '.log.1', '.log.2', '.log.old')):
                                filepath = os.path.join(root, file)
                                try:
                                    stat = os.stat(filepath)
                                    file_date = datetime.fromtimestamp(stat.st_mtime)
                                    
                                    if file_date < cutoff_date and stat.st_size > 1024:  # Plus de 1KB
                                        actions.append(CleaningAction(
                                            action_type='delete_file',
                                            target_path=filepath,
                                            size_bytes=stat.st_size,
                                            description=f"Supprimer ancien log: {file}",
                                            safety_level='moderate',
                                            category='logs',
                                            reversible=True
                                        ))
                                except (PermissionError, FileNotFoundError, OSError):
                                    continue
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_temp_files(self, directories: List[str]) -> List[CleaningAction]:
        """Scanne les fichiers temporaires"""
        actions = []
        temp_dirs = ['/tmp', '/var/tmp', '~/.tmp']
        
        cutoff_date = datetime.now() - timedelta(days=self.config['max_file_age_days']['temp'])
        
        for temp_dir in temp_dirs:
            expanded_dir = os.path.expanduser(temp_dir)
            if os.path.exists(expanded_dir):
                try:
                    for item in os.listdir(expanded_dir):
                        item_path = os.path.join(expanded_dir, item)
                        try:
                            stat = os.stat(item_path)
                            file_date = datetime.fromtimestamp(stat.st_mtime)
                            
                            if file_date < cutoff_date:
                                if os.path.isfile(item_path):
                                    actions.append(CleaningAction(
                                        action_type='delete_file',
                                        target_path=item_path,
                                        size_bytes=stat.st_size,
                                        description=f"Supprimer fichier temporaire: {item}",
                                        safety_level='safe',
                                        category='temp',
                                        reversible=False
                                    ))
                                elif os.path.isdir(item_path):
                                    dir_size = self._get_directory_size(item_path)
                                    actions.append(CleaningAction(
                                        action_type='delete_directory',
                                        target_path=item_path,
                                        size_bytes=dir_size,
                                        description=f"Supprimer dossier temporaire: {item}",
                                        safety_level='safe',
                                        category='temp',
                                        reversible=False
                                    ))
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_old_downloads(self) -> List[CleaningAction]:
        """Scanne les anciens téléchargements"""
        actions = []
        downloads_dir = os.path.expanduser("~/Downloads")
        
        if not os.path.exists(downloads_dir):
            return actions
        
        cutoff_date = datetime.now() - timedelta(days=self.config['max_file_age_days']['downloads'])
        
        try:
            for item in os.listdir(downloads_dir):
                item_path = os.path.join(downloads_dir, item)
                try:
                    stat = os.stat(item_path)
                    file_date = datetime.fromtimestamp(stat.st_mtime)
                    
                    if file_date < cutoff_date and os.path.isfile(item_path):
                        # Seulement les gros fichiers (>50MB) et certains types
                        if (stat.st_size > 50 * 1024 * 1024 and 
                            any(item.lower().endswith(ext) for ext in ['.iso', '.zip', '.tar.gz', '.deb', '.rpm'])):
                            
                            actions.append(CleaningAction(
                                action_type='delete_file',
                                target_path=item_path,
                                size_bytes=stat.st_size,
                                description=f"Supprimer ancien téléchargement: {item}",
                                safety_level='moderate',
                                category='downloads',
                                reversible=True
                            ))
                except (PermissionError, FileNotFoundError, OSError):
                    continue
        except (PermissionError, FileNotFoundError):
            pass
        
        return actions
    
    def _scan_package_caches(self) -> List[CleaningAction]:
        """Scanne les caches de packages"""
        actions = []
        
        # Cache APT
        apt_cache_dir = '/var/cache/apt/archives'
        if os.path.exists(apt_cache_dir):
            try:
                cache_size = self._get_directory_size(apt_cache_dir)
                if cache_size > 100 * 1024 * 1024:  # Plus de 100MB
                    actions.append(CleaningAction(
                        action_type='clear_cache',
                        target_path=apt_cache_dir,
                        size_bytes=cache_size,
                        description="Vider le cache APT",
                        safety_level='safe',
                        category='packages',
                        reversible=False
                    ))
            except (PermissionError, FileNotFoundError):
                pass
        
        # Cache Snap
        snap_cache_dir = '/var/lib/snapd/cache'
        if os.path.exists(snap_cache_dir):
            try:
                cache_size = self._get_directory_size(snap_cache_dir)
                if cache_size > 50 * 1024 * 1024:  # Plus de 50MB
                    actions.append(CleaningAction(
                        action_type='clear_cache',
                        target_path=snap_cache_dir,
                        size_bytes=cache_size,
                        description="Vider le cache Snap",
                        safety_level='safe',
                        category='packages',
                        reversible=False
                    ))
            except (PermissionError, FileNotFoundError):
                pass
        
        return actions
    
    def execute_cleaning_actions(self, actions: List[CleaningAction]) -> List[CleaningResult]:
        """Exécute les actions de nettoyage"""
        results = []
        
        for action in actions:
            start_time = datetime.now()
            result = self._execute_single_action(action)
            end_time = datetime.now()
            
            result.execution_time = (end_time - start_time).total_seconds()
            results.append(result)
            
            # Log du résultat
            if result.success:
                self.logger.info(f"Action réussie: {action.description} - {result.actual_size_freed} bytes libérés")
            else:
                self.logger.error(f"Action échouée: {action.description} - {result.error_message}")
        
        return results
    
    def _execute_single_action(self, action: CleaningAction) -> CleaningResult:
        """Exécute une seule action de nettoyage"""
        if self.dry_run:
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=action.size_bytes
            )
        
        try:
            # Créer une sauvegarde si nécessaire
            if action.reversible:
                backup_path = self._create_backup(action.target_path)
                action.backup_path = backup_path
            
            # Exécuter l'action
            if action.action_type == 'delete_file':
                return self._delete_file(action)
            elif action.action_type == 'delete_directory':
                return self._delete_directory(action)
            elif action.action_type == 'clear_cache':
                return self._clear_cache(action)
            else:
                return CleaningResult(
                    action=action,
                    success=False,
                    error_message=f"Type d'action non supporté: {action.action_type}"
                )
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _delete_file(self, action: CleaningAction) -> CleaningResult:
        """Supprime un fichier"""
        try:
            if os.path.exists(action.target_path):
                actual_size = os.path.getsize(action.target_path)
                os.remove(action.target_path)
                
                return CleaningResult(
                    action=action,
                    success=True,
                    actual_size_freed=actual_size
                )
            else:
                return CleaningResult(
                    action=action,
                    success=False,
                    error_message="Fichier non trouvé"
                )
        
        except (PermissionError, OSError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _delete_directory(self, action: CleaningAction) -> CleaningResult:
        """Supprime un répertoire"""
        try:
            if os.path.exists(action.target_path):
                actual_size = self._get_directory_size(action.target_path)
                shutil.rmtree(action.target_path)
                
                return CleaningResult(
                    action=action,
                    success=True,
                    actual_size_freed=actual_size
                )
            else:
                return CleaningResult(
                    action=action,
                    success=False,
                    error_message="Répertoire non trouvé"
                )
        
        except (PermissionError, OSError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _clear_cache(self, action: CleaningAction) -> CleaningResult:
        """Vide un cache"""
        try:
            if '/var/cache/apt' in action.target_path:
                # Utiliser apt-get clean
                result = subprocess.run(['sudo', 'apt-get', 'clean'], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    return CleaningResult(
                        action=action,
                        success=True,
                        actual_size_freed=action.size_bytes
                    )
                else:
                    return CleaningResult(
                        action=action,
                        success=False,
                        error_message=result.stderr
                    )
            else:
                # Suppression manuelle du contenu
                if os.path.exists(action.target_path):
                    actual_size = self._get_directory_size(action.target_path)
                    
                    for item in os.listdir(action.target_path):
                        item_path = os.path.join(action.target_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    
                    return CleaningResult(
                        action=action,
                        success=True,
                        actual_size_freed=actual_size
                    )
                else:
                    return CleaningResult(
                        action=action,
                        success=False,
                        error_message="Répertoire de cache non trouvé"
                    )
        
        except (PermissionError, OSError, subprocess.TimeoutExpired) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _create_backup(self, file_path: str) -> str:
        """Crée une sauvegarde d'un fichier"""
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_filename = f"{filename}_{timestamp}.backup"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            if os.path.isfile(file_path):
                shutil.copy2(file_path, backup_path)
            elif os.path.isdir(file_path):
                shutil.copytree(file_path, backup_path)
            
            return backup_path
        
        except (PermissionError, OSError):
            return None
    
    def _get_directory_size(self, directory: str) -> int:
        """Calcule la taille d'un répertoire"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        
        return total_size
    
    def get_cleaning_summary(self, actions: List[CleaningAction]) -> Dict:
        """Génère un résumé des actions de nettoyage"""
        summary = {
            'total_actions': len(actions),
            'total_size_to_free': sum(action.size_bytes for action in actions),
            'by_category': {},
            'by_safety_level': {},
            'reversible_actions': sum(1 for action in actions if action.reversible),
            'largest_action': None
        }
        
        # Grouper par catégorie
        for action in actions:
            if action.category not in summary['by_category']:
                summary['by_category'][action.category] = {
                    'count': 0,
                    'total_size': 0
                }
            summary['by_category'][action.category]['count'] += 1
            summary['by_category'][action.category]['total_size'] += action.size_bytes
        
        # Grouper par niveau de sécurité
        for action in actions:
            if action.safety_level not in summary['by_safety_level']:
                summary['by_safety_level'][action.safety_level] = {
                    'count': 0,
                    'total_size': 0
                }
            summary['by_safety_level'][action.safety_level]['count'] += 1
            summary['by_safety_level'][action.safety_level]['total_size'] += action.size_bytes
        
        # Plus grosse action
        if actions:
            summary['largest_action'] = max(actions, key=lambda a: a.size_bytes)
        
        return summary
    
    def restore_from_backup(self, backup_path: str, original_path: str) -> bool:
        """Restaure un fichier depuis une sauvegarde"""
        if self.dry_run:
            return True
        
        try:
            if os.path.exists(backup_path):
                if os.path.isfile(backup_path):
                    shutil.copy2(backup_path, original_path)
                elif os.path.isdir(backup_path):
                    if os.path.exists(original_path):
                        shutil.rmtree(original_path)
                    shutil.copytree(backup_path, original_path)
                
                return True
            else:
                return False
        
        except (PermissionError, OSError):
            return False
    
    def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes"""
        if not os.path.exists(self.backup_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.config['max_backup_age_days'])
        max_size = self.config['max_backup_size_mb'] * 1024 * 1024
        
        backups = []
        total_size = 0
        
        try:
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                if os.path.isfile(item_path):
                    stat = os.stat(item_path)
                    backups.append({
                        'path': item_path,
                        'mtime': datetime.fromtimestamp(stat.st_mtime),
                        'size': stat.st_size
                    })
                    total_size += stat.st_size
            
            # Supprimer les sauvegardes trop anciennes
            for backup in backups:
                if backup['mtime'] < cutoff_date:
                    try:
                        os.remove(backup['path'])
                        total_size -= backup['size']
                    except (PermissionError, OSError):
                        continue
            
            # Supprimer les plus anciennes si la taille totale dépasse la limite
            if total_size > max_size:
                remaining_backups = [b for b in backups if b['mtime'] >= cutoff_date]
                remaining_backups.sort(key=lambda b: b['mtime'])
                
                for backup in remaining_backups:
                    if total_size <= max_size:
                        break
                    try:
                        os.remove(backup['path'])
                        total_size -= backup['size']
                    except (PermissionError, OSError):
                        continue
        
        except (PermissionError, FileNotFoundError):
            pass
    
    def set_dry_run(self, dry_run: bool):
        """Active ou désactive le mode dry-run"""
        self.dry_run = dry_run
    
    def is_path_safe_to_clean(self, path: str) -> bool:
        """Vérifie si un chemin est sûr à nettoyer"""
        expanded_path = os.path.expanduser(path)
        
        # Vérifier les répertoires protégés
        for protected in self.config['protected_directories']:
            protected_expanded = os.path.expanduser(protected)
            if expanded_path.startswith(protected_expanded):
                return False
        
        # Vérifier les répertoires sûrs
        for safe in self.config['safe_directories']:
            safe_expanded = os.path.expanduser(safe)
            if expanded_path.startswith(safe_expanded):
                return True
        
        return False