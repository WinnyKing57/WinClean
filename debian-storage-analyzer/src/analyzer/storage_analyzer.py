# -*- coding: utf-8 -*-

import os
from collections import namedtuple

# Utilisation d'un namedtuple pour une structure de données claire et immuable
FileInfo = namedtuple('FileInfo', ['path', 'size', 'is_dir'])

def get_item_size(path):
    """
    Calcule la taille totale d'un fichier ou d'un répertoire (récursivement).
    Retourne 0 si le chemin n'existe pas ou n'est pas accessible.
    Utilise os.scandir pour de meilleures performances.
    """
    total_size = 0
    try:
        # On utilise os.lstat pour ne pas suivre les liens symboliques lors de la mesure initiale
        st = os.lstat(path)
        if os.path.islink(path):
            return st.st_size

        if os.path.isfile(path):
            return st.st_size
        elif os.path.isdir(path):
            # Calcul récursif pour les répertoires
            for entry in os.scandir(path):
                try:
                    if entry.is_symlink():
                        total_size += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_file():
                        total_size += entry.stat().st_size
                    elif entry.is_dir():
                        total_size += get_item_size(entry.path)
                except (PermissionError, FileNotFoundError):
                    continue
    except (PermissionError, FileNotFoundError):
        return 0

    return total_size

def analyze_directory(path):
    """
    Analyse le premier niveau d'un répertoire donné, calcule la taille de chaque
    élément (fichier ou dossier) et retourne une liste triée par taille.
    Utilise os.scandir pour de meilleures performances.

    Args:
        path (str): Le chemin du répertoire à analyser.

    Returns:
        list: Une liste de namedtuples FileInfo, triée par taille décroissante.
    """
    if not os.path.isdir(path):
        return []

    results = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    full_path = entry.path
                    size = get_item_size(full_path)
                    is_dir = entry.is_dir()
                    results.append(FileInfo(path=full_path, size=size, is_dir=is_dir))
                except (PermissionError, FileNotFoundError):
                    continue
    except PermissionError:
        return []

    # Trier les résultats par taille, du plus grand au plus petit
    results.sort(key=lambda x: x.size, reverse=True)

    return results

if __name__ == '__main__':
    # Test rapide
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "sub")
        os.mkdir(sub)
        with open(os.path.join(sub, "test.txt"), "w") as f:
            f.write("test" * 1000) # ~4KB

        print(f"Analyse de {tmpdir}...")
        res = analyze_directory(tmpdir)
        for r in res:
            print(f"{r.path}: {r.size} bytes (dir: {r.is_dir})")
