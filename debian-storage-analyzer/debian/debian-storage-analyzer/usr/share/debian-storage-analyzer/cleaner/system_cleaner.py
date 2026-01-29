# -*- coding: utf-8 -*-

import os
import shutil
import subprocess

def get_dir_size(path):
    """Calcule la taille totale d'un répertoire."""
    total = 0
    if not os.path.exists(path):
        return total
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp) and not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total

def clean_apt_cache():
    """
    Nettoie le cache des paquets APT.
    Nécessite les privilèges root.
    Retourne l'espace disque libéré (estimation).
    """
    path = "/var/cache/apt/archives"
    if not os.path.isdir(path):
        return 0

    initial_size = get_dir_size(path)

    try:
        # L'option -y n'est pas nécessaire pour 'clean' mais ne pose pas de problème
        subprocess.run(['apt-get', 'clean', '-y'], check=True, capture_output=True)
        final_size = get_dir_size(path)
        return initial_size - final_size
    except (subprocess.CalledProcessError, PermissionError) as e:
        print(f"Erreur lors du nettoyage du cache APT : {e}")
        return 0

def autoremove_packages():
    """
    Supprime les paquets orphelins (dépendances inutiles).
    Nécessite les privilèges root.
    Retourne True en cas de succès.
    """
    try:
        subprocess.run(['apt-get', 'autoremove', '-y'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, PermissionError) as e:
        print(f"Erreur lors de l'autoremove APT : {e}")
        return False

import time

def clean_temp_files(dirs_to_clean=['/tmp', '/var/tmp'], days_old=7):
    """
    Supprime les fichiers et dossiers plus anciens que `days_old` jours
    dans les répertoires temporaires. C'est une méthode bien plus sûre
    que de tout supprimer.
    Nécessite les privilèges root pour une suppression complète.
    Retourne l'espace disque libéré.
    """
    total_freed_space = 0
    cutoff_time = time.time() - (days_old * 86400)

    for directory in dirs_to_clean:
        if not os.path.isdir(directory):
            continue

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                # Vérifier si le fichier est assez ancien
                if os.path.getmtime(file_path) < cutoff_time:
                    size = 0
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        size = os.path.getsize(file_path)
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        size = get_dir_size(file_path)
                        shutil.rmtree(file_path)
                    total_freed_space += size
            except (PermissionError, FileNotFoundError) as e:
                # Ignore les fichiers que nous ne pouvons pas supprimer ou qui ont disparu
                print(f"Impossible de traiter {file_path}: {e}")
                continue
    return total_freed_space

def clean_journal_logs():
    """
    Réduit la taille des journaux système (journald).
    Nécessite les privilèges root.
    Retourne True en cas de succès, False sinon.
    """
    try:
        # Réduit les journaux pour qu'ils occupent au maximum 50M
        subprocess.run(
            ['journalctl', '--vacuum-size=50M'],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # FileNotFoundError si journalctl n'est pas installé
        print(f"Erreur lors du nettoyage des journaux système : {e}")
        return False

if __name__ == '__main__':
    print("--- Test du module de nettoyage sécurisé ---")

    test_dir = 'temp_test_cleaner_safe'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    # Création de fichiers de test
    recent_file = os.path.join(test_dir, 'recent_file.tmp')
    old_file = os.path.join(test_dir, 'old_file.tmp')

    with open(recent_file, 'w') as f:
        f.write('a' * 1024) # 1 KB
    with open(old_file, 'w') as f:
        f.write('a' * 2048) # 2 KB

    # Rendre le "old_file" plus vieux que 7 jours
    eight_days_ago = time.time() - (8 * 86400)
    os.utime(old_file, (eight_days_ago, eight_days_ago))

    initial_size = get_dir_size(test_dir)
    old_file_size = os.path.getsize(old_file)
    print(f"Taille initiale du répertoire : {initial_size / 1024:.2f} KB")
    print(f"Le fichier ancien ({old_file}) doit être supprimé ({old_file_size / 1024:.2f} KB).")
    print(f"Le fichier récent ({recent_file}) doit être conservé.")

    # Exécuter le nettoyage
    freed_space = clean_temp_files(dirs_to_clean=[test_dir], days_old=7)
    print(f"Espace libéré (calculé) : {freed_space / 1024:.2f} KB")

    # Vérifications
    final_size = get_dir_size(test_dir)
    recent_file_exists = os.path.exists(recent_file)
    old_file_exists = os.path.exists(old_file)

    print(f"Taille finale du répertoire : {final_size / 1024:.2f} KB")
    print(f"Le fichier récent existe-t-il ? {recent_file_exists}")
    print(f"Le fichier ancien existe-t-il ? {old_file_exists}")

    if freed_space == old_file_size and recent_file_exists and not old_file_exists:
        print("Test de clean_temp_files sécurisé : SUCCÈS")
    else:
        print("Test de clean_temp_files sécurisé : ÉCHEC")

    # Nettoyage
    shutil.rmtree(test_dir)
