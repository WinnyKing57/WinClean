# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import glob
import logging

from .intelligent_cleaner import CleaningAction, CleaningResult


class SystemExtensionsCleaner:
    """Nettoyeur d'extensions système (Snap, thumbnails, trash, etc.)"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
    
    def scan_system_extensions(self) -> List[CleaningAction]:
        """Scanne toutes les extensions système pour le nettoyage"""
        actions = []
        
        # Scanner les différents composants système
        actions.extend(self._scan_snap_system())
        actions.extend(self._scan_thumbnails())
        actions.extend(self._scan_trash())
        actions.extend(self._scan_journal_logs())
        actions.extend(self._scan_old_kernels())
        actions.extend(self._scan_package_residuals())
        actions.extend(self._scan_broken_symlinks())
        actions.extend(self._scan_old_config_backups())
        
        return actions
    
    def _scan_snap_system(self) -> List[CleaningAction]:
        """Scanne le système Snap pour le nettoyage"""
        actions = []
        
        try:
            # Vérifier si Snap est installé
            result = subprocess.run(['which', 'snap'], capture_output=True, timeout=5)
            if result.returncode != 0:
                return actions
            
            # Scanner les anciennes versions de snaps
            actions.extend(self._scan_old_snap_versions())
            
            # Scanner le cache Snap
            actions.extend(self._scan_snap_cache())
            
            # Scanner les snaps désactivés
            actions.extend(self._scan_disabled_snaps())
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return actions
    
    def _scan_old_snap_versions(self) -> List[CleaningAction]:
        """Scanne les anciennes versions de snaps"""
        actions = []
        
        try:
            # Lister les snaps installés
            result = subprocess.run(['snap', 'list', '--all'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return actions
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            snap_versions = {}
            
            # Grouper par nom de snap
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0]
                        version = parts[1]
                        rev = parts[2]
                        status = parts[3] if len(parts) > 3 else ""
                        
                        if name not in snap_versions:
                            snap_versions[name] = []
                        
                        snap_versions[name].append({
                            'version': version,
                            'revision': rev,
                            'disabled': 'disabled' in status
                        })
            
            # Identifier les anciennes versions
            for snap_name, versions in snap_versions.items():
                if len(versions) > 1:
                    # Trier par révision (plus récente en premier)
                    versions.sort(key=lambda x: int(x['revision']), reverse=True)
                    
                    # Les versions après la première sont anciennes
                    for old_version in versions[1:]:
                        if old_version['disabled']:
                            # Estimer la taille (difficile à obtenir précisément)
                            estimated_size = 100 * 1024 * 1024  # 100MB par défaut
                            
                            actions.append(CleaningAction(
                                action_type='remove_snap_version',
                                target_path=f"{snap_name}:{old_version['revision']}",
                                size_bytes=estimated_size,
                                description=f"Supprimer ancienne version de {snap_name} (rev {old_version['revision']})",
                                safety_level='safe',
                                category='snap_versions',
                                reversible=False
                            ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        
        return actions
    
    def _scan_snap_cache(self) -> List[CleaningAction]:
        """Scanne le cache Snap"""
        actions = []
        
        snap_cache_dirs = [
            '/var/lib/snapd/cache',
            '/var/cache/snapd'
        ]
        
        for cache_dir in snap_cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    cache_size = self._get_directory_size(cache_dir)
                    if cache_size > 10 * 1024 * 1024:  # Plus de 10MB
                        actions.append(CleaningAction(
                            action_type='clear_cache',
                            target_path=cache_dir,
                            size_bytes=cache_size,
                            description=f"Vider le cache Snap: {cache_dir}",
                            safety_level='safe',
                            category='snap_cache',
                            reversible=False
                        ))
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_disabled_snaps(self) -> List[CleaningAction]:
        """Scanne les snaps désactivés"""
        actions = []
        
        try:
            result = subprocess.run(['snap', 'list', '--all'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return actions
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip() and 'disabled' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        revision = parts[2]
                        
                        # Estimer la taille
                        estimated_size = 50 * 1024 * 1024  # 50MB par défaut
                        
                        actions.append(CleaningAction(
                            action_type='remove_disabled_snap',
                            target_path=f"{name}:{revision}",
                            size_bytes=estimated_size,
                            description=f"Supprimer snap désactivé: {name}",
                            safety_level='moderate',
                            category='disabled_snaps',
                            reversible=False
                        ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        
        return actions
    
    def _scan_thumbnails(self) -> List[CleaningAction]:
        """Scanne les miniatures (thumbnails)"""
        actions = []
        
        thumbnail_dirs = [
            '~/.cache/thumbnails',
            '~/.thumbnails'
        ]
        
        cutoff_date = datetime.now() - timedelta(days=90)  # Miniatures de plus de 90 jours
        
        for thumb_dir in thumbnail_dirs:
            expanded_dir = os.path.expanduser(thumb_dir)
            if os.path.exists(expanded_dir):
                try:
                    total_size = 0
                    old_files_count = 0
                    
                    for root, dirs, files in os.walk(expanded_dir):
                        for file in files:
                            filepath = os.path.join(root, file)
                            try:
                                stat = os.stat(filepath)
                                file_date = datetime.fromtimestamp(stat.st_atime)  # Dernière lecture
                                
                                if file_date < cutoff_date:
                                    total_size += stat.st_size
                                    old_files_count += 1
                            except (PermissionError, FileNotFoundError, OSError):
                                continue
                    
                    if total_size > 10 * 1024 * 1024:  # Plus de 10MB
                        actions.append(CleaningAction(
                            action_type='clean_old_thumbnails',
                            target_path=expanded_dir,
                            size_bytes=total_size,
                            description=f"Supprimer anciennes miniatures ({old_files_count} fichiers)",
                            safety_level='safe',
                            category='thumbnails',
                            reversible=False
                        ))
                
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_trash(self) -> List[CleaningAction]:
        """Scanne la corbeille"""
        actions = []
        
        trash_dirs = [
            '~/.local/share/Trash',
            '~/.Trash'
        ]
        
        cutoff_date = datetime.now() - timedelta(days=30)  # Corbeille de plus de 30 jours
        
        for trash_dir in trash_dirs:
            expanded_dir = os.path.expanduser(trash_dir)
            if os.path.exists(expanded_dir):
                try:
                    files_dir = os.path.join(expanded_dir, 'files')
                    info_dir = os.path.join(expanded_dir, 'info')
                    
                    if os.path.exists(files_dir):
                        total_size = 0
                        old_items_count = 0
                        
                        for item in os.listdir(files_dir):
                            item_path = os.path.join(files_dir, item)
                            info_path = os.path.join(info_dir, f"{item}.trashinfo")
                            
                            try:
                                # Lire la date de suppression depuis le fichier .trashinfo
                                deletion_date = None
                                if os.path.exists(info_path):
                                    with open(info_path, 'r') as f:
                                        for line in f:
                                            if line.startswith('DeletionDate='):
                                                date_str = line.split('=', 1)[1].strip()
                                                deletion_date = datetime.fromisoformat(date_str.replace('T', ' '))
                                                break
                                
                                if deletion_date and deletion_date < cutoff_date:
                                    item_size = self._get_path_size(item_path)
                                    total_size += item_size
                                    old_items_count += 1
                            
                            except (PermissionError, FileNotFoundError, OSError, ValueError):
                                continue
                        
                        if total_size > 0:
                            actions.append(CleaningAction(
                                action_type='empty_old_trash',
                                target_path=expanded_dir,
                                size_bytes=total_size,
                                description=f"Vider anciens éléments de la corbeille ({old_items_count} éléments)",
                                safety_level='moderate',
                                category='trash',
                                reversible=False
                            ))
                
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def _scan_journal_logs(self) -> List[CleaningAction]:
        """Scanne les logs systemd journal"""
        actions = []
        
        try:
            # Vérifier la taille du journal
            result = subprocess.run(['journalctl', '--disk-usage'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parser la sortie pour obtenir la taille
                output = result.stdout.strip()
                if 'Archived and active journals take up' in output:
                    # Extraire la taille (format: "X.XG" ou "X.XM")
                    size_str = output.split('take up')[1].split('on disk')[0].strip()
                    
                    try:
                        if size_str.endswith('G'):
                            size_gb = float(size_str[:-1])
                            size_bytes = int(size_gb * 1024 * 1024 * 1024)
                        elif size_str.endswith('M'):
                            size_mb = float(size_str[:-1])
                            size_bytes = int(size_mb * 1024 * 1024)
                        else:
                            size_bytes = 0
                        
                        if size_bytes > 500 * 1024 * 1024:  # Plus de 500MB
                            actions.append(CleaningAction(
                                action_type='clean_journal_logs',
                                target_path='/var/log/journal',
                                size_bytes=size_bytes // 2,  # Estimation de ce qui sera nettoyé
                                description=f"Nettoyer les logs systemd journal (taille actuelle: {size_str})",
                                safety_level='safe',
                                category='journal_logs',
                                reversible=False
                            ))
                    
                    except ValueError:
                        pass
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return actions
    
    def _scan_old_kernels(self) -> List[CleaningAction]:
        """Scanne les anciens noyaux Linux"""
        actions = []
        
        try:
            # Obtenir le noyau actuel
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return actions
            
            current_kernel = result.stdout.strip()
            
            # Lister les noyaux installés
            result = subprocess.run(['dpkg', '--list'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return actions
            
            installed_kernels = []
            for line in result.stdout.split('\n'):
                if 'linux-image-' in line and line.startswith('ii'):
                    parts = line.split()
                    if len(parts) >= 2:
                        package_name = parts[1]
                        if 'linux-image-' in package_name:
                            kernel_version = package_name.replace('linux-image-', '')
                            if kernel_version != current_kernel and not kernel_version.endswith('-generic'):
                                installed_kernels.append(package_name)
            
            # Créer des actions pour supprimer les anciens noyaux
            for kernel_package in installed_kernels:
                # Estimer la taille (environ 200MB par noyau)
                estimated_size = 200 * 1024 * 1024
                
                actions.append(CleaningAction(
                    action_type='remove_old_kernel',
                    target_path=kernel_package,
                    size_bytes=estimated_size,
                    description=f"Supprimer ancien noyau: {kernel_package}",
                    safety_level='moderate',
                    category='old_kernels',
                    reversible=False
                ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return actions
    
    def _scan_package_residuals(self) -> List[CleaningAction]:
        """Scanne les résidus de packages désinstallés"""
        actions = []
        
        try:
            # Lister les packages avec des résidus de configuration
            result = subprocess.run(['dpkg', '--list'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return actions
            
            residual_packages = []
            for line in result.stdout.split('\n'):
                if line.startswith('rc'):  # rc = removed but config files remain
                    parts = line.split()
                    if len(parts) >= 2:
                        package_name = parts[1]
                        residual_packages.append(package_name)
            
            if residual_packages:
                # Estimer la taille totale (difficile à calculer précisément)
                estimated_size = len(residual_packages) * 1024 * 1024  # 1MB par package
                
                actions.append(CleaningAction(
                    action_type='purge_package_residuals',
                    target_path=','.join(residual_packages),
                    size_bytes=estimated_size,
                    description=f"Purger résidus de configuration ({len(residual_packages)} packages)",
                    safety_level='moderate',
                    category='package_residuals',
                    reversible=False
                ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return actions
    
    def _scan_broken_symlinks(self) -> List[CleaningAction]:
        """Scanne les liens symboliques cassés"""
        actions = []
        
        search_dirs = [
            '/usr/bin',
            '/usr/local/bin',
            '/opt',
            os.path.expanduser('~/bin'),
            os.path.expanduser('~/.local/bin')
        ]
        
        broken_links = []
        total_size = 0
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                try:
                    for root, dirs, files in os.walk(search_dir):
                        for file in files:
                            filepath = os.path.join(root, file)
                            
                            if os.path.islink(filepath):
                                try:
                                    # Vérifier si le lien est cassé
                                    os.stat(filepath)
                                except (FileNotFoundError, OSError):
                                    # Lien cassé
                                    broken_links.append(filepath)
                                    total_size += 1024  # Taille symbolique
                
                except (PermissionError, FileNotFoundError):
                    continue
        
        if broken_links:
            actions.append(CleaningAction(
                action_type='remove_broken_symlinks',
                target_path=','.join(broken_links),
                size_bytes=total_size,
                description=f"Supprimer liens symboliques cassés ({len(broken_links)} liens)",
                safety_level='safe',
                category='broken_symlinks',
                reversible=True
            ))
        
        return actions
    
    def _scan_old_config_backups(self) -> List[CleaningAction]:
        """Scanne les anciennes sauvegardes de configuration"""
        actions = []
        
        config_dirs = [
            '/etc',
            os.path.expanduser('~/.config')
        ]
        
        cutoff_date = datetime.now() - timedelta(days=180)  # Plus de 6 mois
        backup_patterns = ['*.bak', '*.backup', '*.old', '*.orig', '*~']
        
        for config_dir in config_dirs:
            if os.path.exists(config_dir):
                try:
                    old_backups = []
                    total_size = 0
                    
                    for root, dirs, files in os.walk(config_dir):
                        for file in files:
                            # Vérifier si le fichier correspond à un pattern de sauvegarde
                            is_backup = any(file.endswith(pattern[1:]) or file.endswith(pattern) 
                                          for pattern in backup_patterns)
                            
                            if is_backup:
                                filepath = os.path.join(root, file)
                                try:
                                    stat = os.stat(filepath)
                                    file_date = datetime.fromtimestamp(stat.st_mtime)
                                    
                                    if file_date < cutoff_date:
                                        old_backups.append(filepath)
                                        total_size += stat.st_size
                                
                                except (PermissionError, FileNotFoundError, OSError):
                                    continue
                    
                    if old_backups and total_size > 1024 * 1024:  # Plus de 1MB
                        actions.append(CleaningAction(
                            action_type='remove_old_config_backups',
                            target_path=','.join(old_backups),
                            size_bytes=total_size,
                            description=f"Supprimer anciennes sauvegardes de config ({len(old_backups)} fichiers)",
                            safety_level='moderate',
                            category='config_backups',
                            reversible=True
                        ))
                
                except (PermissionError, FileNotFoundError):
                    continue
        
        return actions
    
    def execute_system_cleaning_action(self, action: CleaningAction) -> CleaningResult:
        """Exécute une action de nettoyage système"""
        if self.dry_run:
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=action.size_bytes
            )
        
        try:
            if action.action_type == 'remove_snap_version':
                return self._remove_snap_version(action)
            elif action.action_type == 'remove_disabled_snap':
                return self._remove_disabled_snap(action)
            elif action.action_type == 'clean_old_thumbnails':
                return self._clean_old_thumbnails(action)
            elif action.action_type == 'empty_old_trash':
                return self._empty_old_trash(action)
            elif action.action_type == 'clean_journal_logs':
                return self._clean_journal_logs(action)
            elif action.action_type == 'remove_old_kernel':
                return self._remove_old_kernel(action)
            elif action.action_type == 'purge_package_residuals':
                return self._purge_package_residuals(action)
            elif action.action_type == 'remove_broken_symlinks':
                return self._remove_broken_symlinks(action)
            elif action.action_type == 'remove_old_config_backups':
                return self._remove_old_config_backups(action)
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
    
    def _remove_snap_version(self, action: CleaningAction) -> CleaningResult:
        """Supprime une ancienne version de snap"""
        try:
            snap_info = action.target_path  # Format: "name:revision"
            
            result = subprocess.run(['sudo', 'snap', 'remove', snap_info], 
                                  capture_output=True, text=True, timeout=300)
            
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
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _remove_disabled_snap(self, action: CleaningAction) -> CleaningResult:
        """Supprime un snap désactivé"""
        return self._remove_snap_version(action)  # Même logique
    
    def _clean_old_thumbnails(self, action: CleaningAction) -> CleaningResult:
        """Nettoie les anciennes miniatures"""
        try:
            cutoff_date = datetime.now() - timedelta(days=90)
            actual_size_freed = 0
            
            for root, dirs, files in os.walk(action.target_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        stat = os.stat(filepath)
                        file_date = datetime.fromtimestamp(stat.st_atime)
                        
                        if file_date < cutoff_date:
                            actual_size_freed += stat.st_size
                            os.remove(filepath)
                    
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
            
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=actual_size_freed
            )
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _empty_old_trash(self, action: CleaningAction) -> CleaningResult:
        """Vide les anciens éléments de la corbeille"""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            actual_size_freed = 0
            
            files_dir = os.path.join(action.target_path, 'files')
            info_dir = os.path.join(action.target_path, 'info')
            
            if os.path.exists(files_dir) and os.path.exists(info_dir):
                for item in os.listdir(files_dir):
                    item_path = os.path.join(files_dir, item)
                    info_path = os.path.join(info_dir, f"{item}.trashinfo")
                    
                    try:
                        # Lire la date de suppression
                        deletion_date = None
                        if os.path.exists(info_path):
                            with open(info_path, 'r') as f:
                                for line in f:
                                    if line.startswith('DeletionDate='):
                                        date_str = line.split('=', 1)[1].strip()
                                        deletion_date = datetime.fromisoformat(date_str.replace('T', ' '))
                                        break
                        
                        if deletion_date and deletion_date < cutoff_date:
                            item_size = self._get_path_size(item_path)
                            actual_size_freed += item_size
                            
                            # Supprimer le fichier et son info
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                            
                            if os.path.exists(info_path):
                                os.remove(info_path)
                    
                    except (PermissionError, FileNotFoundError, OSError, ValueError):
                        continue
            
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=actual_size_freed
            )
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _clean_journal_logs(self, action: CleaningAction) -> CleaningResult:
        """Nettoie les logs systemd journal"""
        try:
            # Nettoyer les logs de plus de 30 jours
            result = subprocess.run(['sudo', 'journalctl', '--vacuum-time=30d'], 
                                  capture_output=True, text=True, timeout=300)
            
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
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _remove_old_kernel(self, action: CleaningAction) -> CleaningResult:
        """Supprime un ancien noyau"""
        try:
            package_name = action.target_path
            
            result = subprocess.run(['sudo', 'apt-get', 'remove', '--purge', '-y', package_name], 
                                  capture_output=True, text=True, timeout=300)
            
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
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _purge_package_residuals(self, action: CleaningAction) -> CleaningResult:
        """Purge les résidus de packages"""
        try:
            packages = action.target_path.split(',')
            
            result = subprocess.run(['sudo', 'dpkg', '--purge'] + packages, 
                                  capture_output=True, text=True, timeout=300)
            
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
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _remove_broken_symlinks(self, action: CleaningAction) -> CleaningResult:
        """Supprime les liens symboliques cassés"""
        try:
            symlinks = action.target_path.split(',')
            actual_size_freed = 0
            
            for symlink in symlinks:
                try:
                    if os.path.islink(symlink):
                        os.remove(symlink)
                        actual_size_freed += 1024  # Taille symbolique
                except (PermissionError, FileNotFoundError, OSError):
                    continue
            
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=actual_size_freed
            )
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
    def _remove_old_config_backups(self, action: CleaningAction) -> CleaningResult:
        """Supprime les anciennes sauvegardes de configuration"""
        try:
            backup_files = action.target_path.split(',')
            actual_size_freed = 0
            
            for backup_file in backup_files:
                try:
                    if os.path.exists(backup_file):
                        file_size = os.path.getsize(backup_file)
                        os.remove(backup_file)
                        actual_size_freed += file_size
                except (PermissionError, FileNotFoundError, OSError):
                    continue
            
            return CleaningResult(
                action=action,
                success=True,
                actual_size_freed=actual_size_freed
            )
        
        except Exception as e:
            return CleaningResult(
                action=action,
                success=False,
                error_message=str(e)
            )
    
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
    
    def _get_path_size(self, path: str) -> int:
        """Calcule la taille d'un fichier ou répertoire"""
        if os.path.isfile(path):
            try:
                return os.path.getsize(path)
            except (PermissionError, FileNotFoundError, OSError):
                return 0
        elif os.path.isdir(path):
            return self._get_directory_size(path)
        else:
            return 0