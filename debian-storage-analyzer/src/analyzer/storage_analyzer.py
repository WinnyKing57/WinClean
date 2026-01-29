# -*- coding: utf-8 -*-

import os
import logging
from collections import namedtuple

logger = logging.getLogger(__name__)

# Utilisation d'un namedtuple pour une structure de données claire et immuable
FileInfo = namedtuple('FileInfo', ['path', 'size', 'is_dir'])

def get_item_size(path, abort_event=None):
    """
    Calcule la taille totale d'un fichier ou d'un répertoire (itérativement).
    Retourne 0 si le chemin n'existe pas ou n'est pas accessible.
    Utilise os.scandir pour de meilleures performances et évite la récursion profonde.
    """
    if abort_event and abort_event.is_set():
        return 0

    try:
        st = os.lstat(path)
        if not os.path.isdir(path) or os.path.islink(path):
            return st.st_size
    except (PermissionError, FileNotFoundError, OSError):
        return 0

    total_size = 0
    stack = [path]

    while stack:
        if abort_event and abort_event.is_set():
            return 0

        current_path = stack.pop()
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            total_size += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_file():
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            stack.append(entry.path)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue

    return total_size

def analyze_directory(path, abort_event=None):
    """
    Analyse le premier niveau d'un répertoire donné, calcule la taille de chaque
    élément (fichier ou dossier) et retourne une liste triée par taille.
    Utilise os.scandir pour de meilleures performances.

    Args:
        path (str): Le chemin du répertoire à analyser.
        abort_event (threading.Event): Événement pour annuler l'analyse.

    Returns:
        list: Une liste de namedtuples FileInfo, triée par taille décroissante.
    """
    logger.info(f"Démarrage de l'analyse du répertoire : {path}")
    if not os.path.isdir(path):
        logger.error(f"Le chemin spécifié n'est pas un répertoire : {path}")
        return []

    results = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if abort_event and abort_event.is_set():
                    break
                try:
                    full_path = entry.path
                    size = get_item_size(full_path, abort_event)
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
