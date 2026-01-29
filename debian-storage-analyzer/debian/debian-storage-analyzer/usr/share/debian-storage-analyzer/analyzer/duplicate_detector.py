# -*- coding: utf-8 -*-

import os
import hashlib
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class DuplicateGroup:
    """Groupe de fichiers dupliqués"""
    hash_value: str
    file_size: int
    file_paths: List[str]
    total_wasted_space: int

class DuplicateDetector:
    """Détecteur de fichiers dupliqués utilisant SHA-256"""
    
    def __init__(self, chunk_size: int = 8192, max_workers: int = 4):
        self.chunk_size = chunk_size
        self.max_workers = max_workers
        self.size_groups = defaultdict(list)
        self.hash_cache = {}
        self._lock = threading.Lock()
    
    def find_duplicates(self, directory: str, min_size: int = 0) -> Dict[str, DuplicateGroup]:
        """
        Trouve les fichiers dupliqués dans un répertoire
        
        Args:
            directory: Répertoire à analyser
            min_size: Taille minimale des fichiers à considérer (en octets)
            
        Returns:
            Dictionnaire des groupes de doublons (clé = hash, valeur = DuplicateGroup)
        """
        # Étape 1: Grouper les fichiers par taille
        self._group_files_by_size(directory, min_size)
        
        # Étape 2: Calculer les hashes pour les fichiers de même taille
        duplicate_groups = self._find_duplicates_by_hash()
        
        # Nettoyer les données temporaires
        self.size_groups.clear()
        
        return duplicate_groups
    
    def _group_files_by_size(self, directory: str, min_size: int):
        """Groupe les fichiers par taille (première optimisation)"""
        self.size_groups.clear()
        
        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    try:
                        # Ignorer les liens symboliques
                        if os.path.islink(filepath):
                            continue
                        
                        file_size = os.path.getsize(filepath)
                        
                        # Filtrer par taille minimale
                        if file_size >= min_size:
                            self.size_groups[file_size].append(filepath)
                    
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        
        except (PermissionError, FileNotFoundError):
            pass
    
    def _find_duplicates_by_hash(self) -> Dict[str, DuplicateGroup]:
        """Trouve les doublons en calculant les hashes des fichiers de même taille"""
        duplicate_groups = {}
        hash_groups = defaultdict(list)
        
        # Ne traiter que les tailles qui ont plusieurs fichiers
        size_groups_with_duplicates = {
            size: paths for size, paths in self.size_groups.items() 
            if len(paths) > 1
        }
        
        if not size_groups_with_duplicates:
            return duplicate_groups
        
        # Calculer les hashes en parallèle
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre toutes les tâches de calcul de hash
            future_to_file = {}
            
            for file_size, file_paths in size_groups_with_duplicates.items():
                for filepath in file_paths:
                    future = executor.submit(self._calculate_file_hash, filepath)
                    future_to_file[future] = (filepath, file_size)
            
            # Collecter les résultats
            for future in as_completed(future_to_file):
                filepath, file_size = future_to_file[future]
                
                try:
                    file_hash = future.result()
                    if file_hash:
                        hash_groups[file_hash].append((filepath, file_size))
                
                except Exception as e:
                    # Ignorer les erreurs de calcul de hash
                    continue
        
        # Créer les groupes de doublons
        for file_hash, file_info_list in hash_groups.items():
            if len(file_info_list) > 1:
                file_paths = [info[0] for info in file_info_list]
                file_size = file_info_list[0][1]  # Tous ont la même taille
                
                # Calculer l'espace gaspillé (tous les fichiers sauf un)
                total_wasted_space = file_size * (len(file_paths) - 1)
                
                duplicate_groups[file_hash] = DuplicateGroup(
                    hash_value=file_hash,
                    file_size=file_size,
                    file_paths=file_paths,
                    total_wasted_space=total_wasted_space
                )
        
        return duplicate_groups
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calcule le hash SHA-256 d'un fichier"""
        # Vérifier le cache
        with self._lock:
            if filepath in self.hash_cache:
                return self.hash_cache[filepath]
        
        try:
            hash_sha256 = hashlib.sha256()
            
            with open(filepath, 'rb') as f:
                # Lire le fichier par chunks pour économiser la mémoire
                while chunk := f.read(self.chunk_size):
                    hash_sha256.update(chunk)
            
            file_hash = hash_sha256.hexdigest()
            
            # Mettre en cache le résultat
            with self._lock:
                self.hash_cache[filepath] = file_hash
            
            return file_hash
        
        except (PermissionError, FileNotFoundError, OSError, IOError):
            return None
    
    def get_duplicate_summary(self, duplicate_groups: Dict[str, DuplicateGroup]) -> Dict[str, any]:
        """Génère un résumé des doublons trouvés"""
        if not duplicate_groups:
            return {
                'total_duplicate_groups': 0,
                'total_duplicate_files': 0,
                'total_wasted_space': 0,
                'largest_duplicate_group': None,
                'most_wasted_space_group': None
            }
        
        total_duplicate_files = sum(len(group.file_paths) for group in duplicate_groups.values())
        total_wasted_space = sum(group.total_wasted_space for group in duplicate_groups.values())
        
        # Trouver le groupe avec le plus de fichiers
        largest_group = max(duplicate_groups.values(), key=lambda g: len(g.file_paths))
        
        # Trouver le groupe qui gaspille le plus d'espace
        most_wasted_group = max(duplicate_groups.values(), key=lambda g: g.total_wasted_space)
        
        return {
            'total_duplicate_groups': len(duplicate_groups),
            'total_duplicate_files': total_duplicate_files,
            'total_wasted_space': total_wasted_space,
            'largest_duplicate_group': {
                'hash': largest_group.hash_value,
                'file_count': len(largest_group.file_paths),
                'file_size': largest_group.file_size,
                'sample_path': largest_group.file_paths[0]
            },
            'most_wasted_space_group': {
                'hash': most_wasted_group.hash_value,
                'wasted_space': most_wasted_group.total_wasted_space,
                'file_count': len(most_wasted_group.file_paths),
                'file_size': most_wasted_group.file_size
            }
        }
    
    def select_files_for_deletion(self, duplicate_group: DuplicateGroup, 
                                 keep_strategy: str = 'first') -> List[str]:
        """
        Sélectionne les fichiers à supprimer dans un groupe de doublons
        
        Args:
            duplicate_group: Groupe de fichiers dupliqués
            keep_strategy: Stratégie pour choisir quel fichier garder
                          'first' - garder le premier dans la liste
                          'shortest_path' - garder celui avec le chemin le plus court
                          'newest' - garder le plus récent
                          'oldest' - garder le plus ancien
        
        Returns:
            Liste des chemins de fichiers à supprimer
        """
        if len(duplicate_group.file_paths) <= 1:
            return []
        
        file_paths = duplicate_group.file_paths.copy()
        
        # Choisir le fichier à conserver
        if keep_strategy == 'first':
            keep_file = file_paths[0]
        
        elif keep_strategy == 'shortest_path':
            keep_file = min(file_paths, key=len)
        
        elif keep_strategy == 'newest':
            keep_file = max(file_paths, key=lambda f: self._get_file_mtime(f))
        
        elif keep_strategy == 'oldest':
            keep_file = min(file_paths, key=lambda f: self._get_file_mtime(f))
        
        else:
            # Stratégie par défaut
            keep_file = file_paths[0]
        
        # Retourner tous les autres fichiers
        files_to_delete = [f for f in file_paths if f != keep_file]
        return files_to_delete
    
    def _get_file_mtime(self, filepath: str) -> float:
        """Obtient le temps de modification d'un fichier"""
        try:
            return os.path.getmtime(filepath)
        except (PermissionError, FileNotFoundError, OSError):
            return 0.0
    
    def verify_duplicates(self, file_paths: List[str]) -> bool:
        """Vérifie que les fichiers sont vraiment identiques"""
        if len(file_paths) < 2:
            return True
        
        # Calculer le hash du premier fichier
        first_hash = self._calculate_file_hash(file_paths[0])
        if not first_hash:
            return False
        
        # Vérifier que tous les autres ont le même hash
        for filepath in file_paths[1:]:
            file_hash = self._calculate_file_hash(filepath)
            if file_hash != first_hash:
                return False
        
        return True
    
    def clear_cache(self):
        """Vide le cache des hashes"""
        with self._lock:
            self.hash_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache"""
        with self._lock:
            return {
                'cached_files': len(self.hash_cache),
                'cache_size_bytes': sum(len(hash_val) for hash_val in self.hash_cache.values())
            }