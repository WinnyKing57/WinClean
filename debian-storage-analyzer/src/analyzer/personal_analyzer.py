# -*- coding: utf-8 -*-

import os
from collections import namedtuple
from pathlib import Path

# Structure pour stocker les informations sur les fichiers trouvés
LargeFileInfo = namedtuple('LargeFileInfo', ['path', 'size'])

def find_large_files(directory_to_scan=None, min_size_mb=100):
    """
    Analyse un répertoire de manière récursive et trouve les fichiers dépassant
    une taille minimale spécifiée.

    Args:
        directory_to_scan (str, optional): Le chemin du répertoire à analyser.
                                           Par défaut, le répertoire personnel de l'utilisateur.
        min_size_mb (int, optional): La taille minimale en Mo pour qu'un fichier
                                     soit inclus dans les résultats. Par défaut 100 Mo.

    Returns:
        list: Une liste de namedtuples LargeFileInfo, triée par taille décroissante.
    """
    if directory_to_scan is None:
        directory_to_scan = str(Path.home())

    min_size_bytes = min_size_mb * 1024 * 1024
    large_files = []

    print(f"Démarrage de l'analyse de '{directory_to_scan}' pour les fichiers > {min_size_mb} Mo...")

    for dirpath, _, filenames in os.walk(directory_to_scan):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            try:
                # S'assurer que ce n'est pas un lien symbolique cassé avant de vérifier la taille
                if not os.path.islink(full_path):
                    file_size = os.path.getsize(full_path)
                    if file_size >= min_size_bytes:
                        large_files.append(LargeFileInfo(path=full_path, size=file_size))
            except (PermissionError, FileNotFoundError):
                # Ignorer les fichiers ou répertoires inaccessibles
                continue

    # Trier les résultats par taille, du plus grand au plus petit
    large_files.sort(key=lambda x: x.size, reverse=True)

    print(f"Analyse terminée. {len(large_files)} fichier(s) trouvé(s).")
    return large_files

def format_size(size_bytes):
    """Convertit une taille en octets en une chaîne de caractères lisible."""
    if size_bytes > 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} Go"
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / (1024**2):.2f} Mo"
    if size_bytes > 1024:
        return f"{size_bytes / 1024:.2f} Ko"
    return f"{size_bytes} octets"


if __name__ == '__main__':
    import shutil

    print("--- Test du module d'analyse de fichiers personnels ---")
    test_dir = 'temp_test_personal_analyzer'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(os.path.join(test_dir, 'subdir'))

    # Création de fichiers de test de différentes tailles
    with open(os.path.join(test_dir, 'small_file.txt'), 'w') as f:
        f.write('a' * 1024) # 1 Ko
    with open(os.path.join(test_dir, 'medium_file.bin'), 'w') as f:
        f.write('a' * (5 * 1024 * 1024)) # 5 Mo
    with open(os.path.join(test_dir, 'large_file.iso'), 'w') as f:
        f.write('a' * (150 * 1024 * 1024)) # 150 Mo
    with open(os.path.join(test_dir, 'subdir', 'another_large_file.zip'), 'w') as f:
        f.write('a' * (120 * 1024 * 1024)) # 120 Mo

    # Test 1: Seuil par défaut (100 Mo)
    print("\n--- Test 1: Recherche de fichiers > 100 Mo ---")
    results = find_large_files(directory_to_scan=test_dir)

    assert len(results) == 2
    assert results[0].path.endswith('large_file.iso')
    assert results[1].path.endswith('another_large_file.zip')

    print("Résultats :")
    for item in results:
        print(f"- {item.path} ({format_size(item.size)})")
    print("Test 1 : SUCCÈS")

    # Test 2: Seuil personnalisé (4 Mo)
    print("\n--- Test 2: Recherche de fichiers > 4 Mo ---")
    results_custom = find_large_files(directory_to_scan=test_dir, min_size_mb=4)

    assert len(results_custom) == 3
    assert results_custom[2].path.endswith('medium_file.bin')

    print("Résultats :")
    for item in results_custom:
        print(f"- {item.path} ({format_size(item.size)})")
    print("Test 2 : SUCCÈS")

    # Nettoyage
    print("\nNettoyage de l'environnement de test...")
    shutil.rmtree(test_dir)
    print("Terminé.")
