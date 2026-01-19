# -*- coding: utf-8 -*-

import os
from collections import namedtuple

# Utilisation d'un namedtuple pour une structure de données claire et immuable
FileInfo = namedtuple('FileInfo', ['path', 'size', 'is_dir'])

def get_item_size(path):
    """
    Calcule la taille totale d'un fichier ou d'un répertoire (récursivement).
    Retourne 0 si le chemin n'existe pas ou n'est pas accessible.
    """
    total_size = 0
    if not os.path.exists(path):
        return 0

    try:
        if os.path.isfile(path):
            total_size = os.path.getsize(path)
        elif os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    # Vérifier que ce n'est pas un lien symbolique cassé
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
    except (PermissionError, FileNotFoundError):
        # Si nous n'avons pas la permission de lire un dossier ou un fichier,
        # nous le comptons comme ayant une taille de 0.
        return 0

    return total_size

def analyze_directory(path):
    """
    Analyse le premier niveau d'un répertoire donné, calcule la taille de chaque
    élément (fichier ou dossier) et retourne une liste triée par taille.

    Args:
        path (str): Le chemin du répertoire à analyser.

    Returns:
        list: Une liste de namedtuples FileInfo, triée par taille décroissante.
              Retourne une liste vide en cas d'erreur (ex: chemin inexistant).
    """
    if not os.path.isdir(path):
        print(f"Erreur : Le chemin '{path}' n'est pas un répertoire valide.")
        return []

    results = []
    try:
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            size = get_item_size(full_path)
            is_dir = os.path.isdir(full_path)
            results.append(FileInfo(path=full_path, size=size, is_dir=is_dir))
    except PermissionError:
        print(f"Erreur de permission en accédant au répertoire '{path}'.")
        return []

    # Trier les résultats par taille, du plus grand au plus petit
    results.sort(key=lambda x: x.size, reverse=True)

    return results

if __name__ == '__main__':
    # Petit test pour vérifier le fonctionnement du module
    print("Création d'un environnement de test...")
    test_dir = 'temp_test_analyzer'
    os.makedirs(os.path.join(test_dir, 'subdir1'), exist_ok=True)
    os.makedirs(os.path.join(test_dir, 'subdir2'), exist_ok=True)

    with open(os.path.join(test_dir, 'file1.txt'), 'w') as f:
        f.write('a' * 1024) # 1 KB
    with open(os.path.join(test_dir, 'subdir1', 'file2.txt'), 'w') as f:
        f.write('a' * 4096) # 4 KB
    with open(os.path.join(test_dir, 'subdir2', 'file3.txt'), 'w') as f:
        f.write('a' * 2048) # 2 KB

    print(f"Analyse du répertoire '{test_dir}'...")
    analysis_result = analyze_directory(test_dir)

    print("\nRésultats de l'analyse :")
    for item in analysis_result:
        # Affichage lisible de la taille
        size_kb = item.size / 1024
        print(f"- Chemin: {item.path} | Taille: {size_kb:.2f} KB | Est un dossier: {item.is_dir}")

    # Nettoyage
    print("\nNettoyage de l'environnement de test...")
    import shutil
    shutil.rmtree(test_dir)
    print("Terminé.")
