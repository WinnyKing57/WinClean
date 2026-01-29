# -*- coding: utf-8 -*-

import os
import subprocess
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageInfo:
    """Informations sur un package installé"""
    name: str
    version: str
    size: int
    package_type: str  # 'deb', 'snap', 'flatpak', 'pip', 'npm'
    description: str
    dependencies: List[str]
    files: List[str]
    install_date: Optional[str] = None


class PackageAnalyzer:
    """Analyseur de packages installés sur le système"""
    
    def __init__(self):
        self.supported_types = ['deb', 'snap', 'flatpak', 'pip', 'npm']
        self.package_cache = {}
    
    def get_installed_packages(self, package_types: List[str] = None) -> Dict[str, List[PackageInfo]]:
        """
        Récupère la liste des packages installés par type
        
        Args:
            package_types: Types de packages à analyser (None = tous)
            
        Returns:
            Dictionnaire {type: [PackageInfo]}
        """
        if package_types is None:
            package_types = self.supported_types
        
        results = {}
        
        for pkg_type in package_types:
            if pkg_type in self.supported_types:
                try:
                    packages = self._get_packages_by_type(pkg_type)
                    results[pkg_type] = packages
                except Exception as e:
                    # En cas d'erreur, retourner une liste vide
                    results[pkg_type] = []
        
        return results
    
    def _get_packages_by_type(self, package_type: str) -> List[PackageInfo]:
        """Récupère les packages d'un type spécifique"""
        if package_type == 'deb':
            return self._get_deb_packages()
        elif package_type == 'snap':
            return self._get_snap_packages()
        elif package_type == 'flatpak':
            return self._get_flatpak_packages()
        elif package_type == 'pip':
            return self._get_pip_packages()
        elif package_type == 'npm':
            return self._get_npm_packages()
        else:
            return []
    
    def _get_deb_packages(self) -> List[PackageInfo]:
        """Récupère les packages .deb installés"""
        packages = []
        
        try:
            # Utiliser dpkg-query pour lister les packages
            result = subprocess.run([
                'dpkg-query', '-W', 
                '--showformat=${Package}\t${Version}\t${Installed-Size}\t${Description}\n'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            name = parts[0]
                            version = parts[1]
                            size_kb = parts[2]
                            description = parts[3]
                            
                            # Convertir la taille en octets
                            try:
                                size = int(size_kb) * 1024 if size_kb.isdigit() else 0
                            except ValueError:
                                size = 0
                            
                            # Obtenir les dépendances
                            dependencies = self._get_deb_dependencies(name)
                            
                            # Obtenir les fichiers (limité pour éviter la lenteur)
                            files = self._get_deb_files(name, limit=10)
                            
                            packages.append(PackageInfo(
                                name=name,
                                version=version,
                                size=size,
                                package_type='deb',
                                description=description,
                                dependencies=dependencies,
                                files=files
                            ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return packages
    
    def _get_deb_dependencies(self, package_name: str) -> List[str]:
        """Récupère les dépendances d'un package .deb"""
        try:
            result = subprocess.run([
                'dpkg-query', '-W', '--showformat=${Depends}', package_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                # Parser les dépendances (format complexe)
                deps_str = result.stdout.strip()
                # Simplification: extraire les noms de packages
                deps = []
                for dep in deps_str.split(','):
                    dep = dep.strip().split('(')[0].strip()  # Enlever les versions
                    if dep and not dep.startswith('${'):
                        deps.append(dep)
                return deps[:10]  # Limiter à 10 dépendances
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        
        return []
    
    def _get_deb_files(self, package_name: str, limit: int = 10) -> List[str]:
        """Récupère quelques fichiers d'un package .deb"""
        try:
            result = subprocess.run([
                'dpkg-query', '-L', package_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                # Retourner seulement les fichiers (pas les dossiers) et limiter
                file_list = []
                for f in files[:limit * 2]:  # Prendre plus pour filtrer
                    if f and os.path.isfile(f):
                        file_list.append(f)
                        if len(file_list) >= limit:
                            break
                return file_list
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        
        return []
    
    def _get_snap_packages(self) -> List[PackageInfo]:
        """Récupère les packages Snap installés"""
        packages = []
        
        try:
            result = subprocess.run([
                'snap', 'list'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line:
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            version = parts[1]
                            # Snap ne donne pas facilement la taille
                            
                            packages.append(PackageInfo(
                                name=name,
                                version=version,
                                size=0,  # Taille non disponible facilement
                                package_type='snap',
                                description=f"Snap package: {name}",
                                dependencies=[],
                                files=[]
                            ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return packages
    
    def _get_flatpak_packages(self) -> List[PackageInfo]:
        """Récupère les packages Flatpak installés"""
        packages = []
        
        try:
            result = subprocess.run([
                'flatpak', 'list', '--app', '--columns=name,version,size,application'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            name = parts[0]
                            version = parts[1] if len(parts) > 1 else 'unknown'
                            
                            packages.append(PackageInfo(
                                name=name,
                                version=version,
                                size=0,  # Taille complexe à obtenir
                                package_type='flatpak',
                                description=f"Flatpak application: {name}",
                                dependencies=[],
                                files=[]
                            ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return packages
    
    def _get_pip_packages(self) -> List[PackageInfo]:
        """Récupère les packages Python pip installés"""
        packages = []
        
        try:
            # Essayer pip3 d'abord, puis pip
            for pip_cmd in ['pip3', 'pip']:
                try:
                    result = subprocess.run([
                        pip_cmd, 'list', '--format=json'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        pip_packages = json.loads(result.stdout)
                        for pkg in pip_packages:
                            packages.append(PackageInfo(
                                name=pkg['name'],
                                version=pkg['version'],
                                size=0,  # Taille non disponible facilement
                                package_type='pip',
                                description=f"Python package: {pkg['name']}",
                                dependencies=[],
                                files=[]
                            ))
                        break  # Succès, pas besoin d'essayer l'autre commande
                
                except (json.JSONDecodeError, KeyError):
                    continue
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return packages
    
    def _get_npm_packages(self) -> List[PackageInfo]:
        """Récupère les packages Node.js npm installés globalement"""
        packages = []
        
        try:
            result = subprocess.run([
                'npm', 'list', '-g', '--depth=0', '--json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    npm_data = json.loads(result.stdout)
                    if 'dependencies' in npm_data:
                        for name, info in npm_data['dependencies'].items():
                            version = info.get('version', 'unknown')
                            packages.append(PackageInfo(
                                name=name,
                                version=version,
                                size=0,  # Taille non disponible facilement
                                package_type='npm',
                                description=f"Node.js package: {name}",
                                dependencies=[],
                                files=[]
                            ))
                
                except (json.JSONDecodeError, KeyError):
                    pass
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return packages
    
    def get_package_summary(self, packages: Dict[str, List[PackageInfo]]) -> Dict[str, any]:
        """Génère un résumé des packages installés"""
        summary = {
            'total_packages': 0,
            'total_size': 0,
            'by_type': {},
            'largest_packages': [],
            'most_dependencies': []
        }
        
        all_packages = []
        
        for pkg_type, pkg_list in packages.items():
            type_count = len(pkg_list)
            type_size = sum(pkg.size for pkg in pkg_list)
            
            summary['by_type'][pkg_type] = {
                'count': type_count,
                'size': type_size,
                'percentage': 0  # Sera calculé après
            }
            
            summary['total_packages'] += type_count
            summary['total_size'] += type_size
            
            all_packages.extend(pkg_list)
        
        # Calculer les pourcentages
        if summary['total_size'] > 0:
            for pkg_type in summary['by_type']:
                type_size = summary['by_type'][pkg_type]['size']
                summary['by_type'][pkg_type]['percentage'] = (type_size / summary['total_size']) * 100
        
        # Trouver les plus gros packages
        all_packages.sort(key=lambda p: p.size, reverse=True)
        summary['largest_packages'] = [
            {
                'name': pkg.name,
                'type': pkg.package_type,
                'size': pkg.size,
                'version': pkg.version
            }
            for pkg in all_packages[:10] if pkg.size > 0
        ]
        
        # Trouver les packages avec le plus de dépendances
        all_packages.sort(key=lambda p: len(p.dependencies), reverse=True)
        summary['most_dependencies'] = [
            {
                'name': pkg.name,
                'type': pkg.package_type,
                'dependencies_count': len(pkg.dependencies),
                'version': pkg.version
            }
            for pkg in all_packages[:10] if len(pkg.dependencies) > 0
        ]
        
        return summary
    
    def find_package_by_name(self, name: str, packages: Dict[str, List[PackageInfo]]) -> List[PackageInfo]:
        """Trouve un package par nom dans tous les types"""
        found_packages = []
        
        for pkg_list in packages.values():
            for pkg in pkg_list:
                if name.lower() in pkg.name.lower():
                    found_packages.append(pkg)
        
        return found_packages
    
    def get_package_conflicts(self, packages: Dict[str, List[PackageInfo]]) -> List[Dict[str, any]]:
        """Détecte les conflits potentiels entre packages"""
        conflicts = []
        all_packages = []
        
        # Collecter tous les packages
        for pkg_list in packages.values():
            all_packages.extend(pkg_list)
        
        # Chercher les noms similaires ou identiques
        name_groups = {}
        for pkg in all_packages:
            base_name = pkg.name.lower().replace('-', '').replace('_', '')
            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append(pkg)
        
        # Identifier les conflits potentiels
        for base_name, pkg_group in name_groups.items():
            if len(pkg_group) > 1:
                # Vérifier si ce sont des types différents
                types = set(pkg.package_type for pkg in pkg_group)
                if len(types) > 1:
                    conflicts.append({
                        'base_name': base_name,
                        'packages': [
                            {
                                'name': pkg.name,
                                'type': pkg.package_type,
                                'version': pkg.version
                            }
                            for pkg in pkg_group
                        ],
                        'conflict_type': 'multiple_package_types'
                    })
        
        return conflicts
    
    def clear_cache(self):
        """Vide le cache des packages"""
        self.package_cache.clear()