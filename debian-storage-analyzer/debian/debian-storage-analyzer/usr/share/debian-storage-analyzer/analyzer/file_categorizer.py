# -*- coding: utf-8 -*-

import os
import mimetypes
from typing import Dict, List, Set
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CategoryStats:
    """Statistiques pour une catégorie de fichiers"""
    name: str
    file_count: int
    total_size: int
    percentage: float
    extensions: Set[str]

class FileCategorizer:
    """Catégorise les fichiers par type basé sur les extensions et le contenu"""
    
    def __init__(self):
        self.categories = {
            'images': {
                'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico'},
                'mimetypes': {'image/'}
            },
            'videos': {
                'extensions': {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'},
                'mimetypes': {'video/'}
            },
            'audio': {
                'extensions': {'.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a', '.wma'},
                'mimetypes': {'audio/'}
            },
            'documents': {
                'extensions': {'.pdf', '.doc', '.docx', '.txt', '.odt', '.rtf', '.tex', '.md'},
                'mimetypes': {'text/', 'application/pdf', 'application/msword'}
            },
            'spreadsheets': {
                'extensions': {'.xls', '.xlsx', '.ods', '.csv'},
                'mimetypes': {'application/vnd.ms-excel', 'application/vnd.oasis.opendocument.spreadsheet'}
            },
            'presentations': {
                'extensions': {'.ppt', '.pptx', '.odp'},
                'mimetypes': {'application/vnd.ms-powerpoint', 'application/vnd.oasis.opendocument.presentation'}
            },
            'archives': {
                'extensions': {'.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z', '.deb', '.rpm'},
                'mimetypes': {'application/zip', 'application/x-tar', 'application/gzip'}
            },
            'executables': {
                'extensions': {'.exe', '.msi', '.deb', '.rpm', '.dmg', '.app', '.appimage'},
                'mimetypes': {'application/x-executable', 'application/x-msdos-program'}
            },
            'code': {
                'extensions': {'.py', '.js', '.html', '.css', '.cpp', '.c', '.java', '.php', '.rb', '.go', '.rs'},
                'mimetypes': {'text/x-python', 'text/javascript', 'text/html'}
            },
            'fonts': {
                'extensions': {'.ttf', '.otf', '.woff', '.woff2', '.eot'},
                'mimetypes': {'font/'}
            },
            'system': {
                'extensions': {'.log', '.tmp', '.cache', '.lock', '.pid'},
                'mimetypes': {}
            }
        }
        
        # Initialiser mimetypes
        mimetypes.init()
    
    def categorize_file(self, filepath: str) -> str:
        """Catégorise un fichier selon son extension et son type MIME"""
        if not os.path.exists(filepath):
            return 'unknown'
        
        if os.path.isdir(filepath):
            return 'directories'
        
        # Obtenir l'extension
        _, ext = os.path.splitext(filepath.lower())
        
        # Obtenir le type MIME
        mime_type, _ = mimetypes.guess_type(filepath)
        
        # Chercher dans les catégories
        for category, config in self.categories.items():
            # Vérifier l'extension
            if ext in config['extensions']:
                return category
            
            # Vérifier le type MIME
            if mime_type:
                for mime_prefix in config['mimetypes']:
                    if mime_type.startswith(mime_prefix):
                        return category
        
        return 'other'
    
    def analyze_directory_categories(self, directory: str) -> Dict[str, CategoryStats]:
        """Analyse un répertoire et retourne les statistiques par catégorie"""
        category_data = {}
        total_size = 0
        total_files = 0
        
        # Initialiser les catégories
        all_categories = list(self.categories.keys()) + ['directories', 'other', 'unknown']
        for category in all_categories:
            category_data[category] = {
                'file_count': 0,
                'total_size': 0,
                'extensions': set()
            }
        
        # Parcourir le répertoire
        try:
            for root, dirs, files in os.walk(directory):
                # Analyser les dossiers
                for dirname in dirs:
                    dirpath = os.path.join(root, dirname)
                    try:
                        dir_size = self._get_directory_size(dirpath)
                        category_data['directories']['file_count'] += 1
                        category_data['directories']['total_size'] += dir_size
                        total_size += dir_size
                        total_files += 1
                    except (PermissionError, FileNotFoundError):
                        continue
                
                # Analyser les fichiers
                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        file_size = os.path.getsize(filepath)
                        category = self.categorize_file(filepath)
                        
                        category_data[category]['file_count'] += 1
                        category_data[category]['total_size'] += file_size
                        
                        # Ajouter l'extension
                        _, ext = os.path.splitext(filename.lower())
                        if ext:
                            category_data[category]['extensions'].add(ext)
                        
                        total_size += file_size
                        total_files += 1
                        
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        
        except (PermissionError, FileNotFoundError):
            pass
        
        # Calculer les pourcentages et créer les objets CategoryStats
        result = {}
        for category, data in category_data.items():
            if data['file_count'] > 0 or data['total_size'] > 0:
                percentage = (data['total_size'] / total_size * 100) if total_size > 0 else 0
                result[category] = CategoryStats(
                    name=category,
                    file_count=data['file_count'],
                    total_size=data['total_size'],
                    percentage=percentage,
                    extensions=data['extensions']
                )
        
        return result
    
    def _get_directory_size(self, directory: str) -> int:
        """Calcule la taille totale d'un répertoire"""
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
    
    def get_category_color(self, category: str) -> str:
        """Retourne une couleur associée à une catégorie"""
        color_map = {
            'images': '#e74c3c',      # Rouge
            'videos': '#9b59b6',      # Violet
            'audio': '#f39c12',       # Orange
            'documents': '#3498db',   # Bleu
            'spreadsheets': '#2ecc71', # Vert
            'presentations': '#e67e22', # Orange foncé
            'archives': '#95a5a6',    # Gris
            'executables': '#34495e', # Gris foncé
            'code': '#1abc9c',        # Turquoise
            'fonts': '#f1c40f',       # Jaune
            'system': '#7f8c8d',      # Gris moyen
            'directories': '#16a085', # Vert foncé
            'other': '#bdc3c7',       # Gris clair
            'unknown': '#ecf0f1'      # Gris très clair
        }
        
        return color_map.get(category, '#bdc3c7')
    
    def get_category_icon(self, category: str) -> str:
        """Retourne une icône GTK associée à une catégorie"""
        icon_map = {
            'images': 'image-x-generic',
            'videos': 'video-x-generic',
            'audio': 'audio-x-generic',
            'documents': 'text-x-generic',
            'spreadsheets': 'x-office-spreadsheet',
            'presentations': 'x-office-presentation',
            'archives': 'package-x-generic',
            'executables': 'application-x-executable',
            'code': 'text-x-script',
            'fonts': 'font-x-generic',
            'system': 'text-x-log',
            'directories': 'folder',
            'other': 'text-x-generic',
            'unknown': 'text-x-generic'
        }
        
        return icon_map.get(category, 'text-x-generic')
    
    def add_custom_category(self, name: str, extensions: Set[str], mimetypes: Set[str] = None):
        """Ajoute une catégorie personnalisée"""
        self.categories[name] = {
            'extensions': extensions,
            'mimetypes': mimetypes or set()
        }
    
    def get_file_type_summary(self, filepath: str) -> Dict[str, str]:
        """Retourne un résumé détaillé du type de fichier"""
        category = self.categorize_file(filepath)
        mime_type, encoding = mimetypes.guess_type(filepath)
        _, ext = os.path.splitext(filepath)
        
        return {
            'category': category,
            'mime_type': mime_type or 'unknown',
            'encoding': encoding or 'none',
            'extension': ext.lower() if ext else 'none',
            'icon': self.get_category_icon(category),
            'color': self.get_category_color(category)
        }