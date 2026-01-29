#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os

# === Gestion du Python Path ===
# Le script helper est installé dans /usr/libexec/, tandis que les modules
# principaux sont dans /usr/share/debian-storage-analyzer/src/. Pour que
# l'import `from cleaner import ...` fonctionne, nous devons ajouter
# explicitement le répertoire des modules au path de Python.

# 1. Chemin pour l'environnement de développement (exécution depuis le build dir)
#    On remonte de 'src/helpers' à la racine du projet pour trouver 'src'
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dev_path = os.path.join(project_root)
if os.path.isdir(os.path.join(dev_path, 'src', 'cleaner')): # Vérifie si on est en dév
    sys.path.insert(0, os.path.join(dev_path, 'src'))

# 2. Chemin pour le système installé (après `dpkg -i`)
#    Le packaging Debian garantit que ce chemin est fixe. C'est un peu
#    rigide, mais c'est une solution simple et fiable dans ce contexte.
installed_path = '/usr/share/debian-storage-analyzer'
if installed_path not in sys.path:
    sys.path.insert(0, installed_path)

try:
    from cleaner import system_cleaner, app_cleaner
except ImportError as e:
    print(f"Erreur d'importation : {e}", file=sys.stderr)
    print(f"Python Path: {sys.path}", file=sys.stderr)
    sys.exit(1)


def main():
    """
    Point d'entrée du script helper.
    Appelle les fonctions de nettoyage en fonction de l'argument reçu.
    """
    if os.geteuid() != 0:
        print("Erreur : Ce script doit être exécuté avec les privilèges root.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: pkexec debian-storage-analyzer-helper <action>", file=sys.stderr)
        print("Actions disponibles: apt, autoremove, temp, logs, snap", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    freed_space = 0

    if action == 'apt':
        print("Nettoyage du cache APT...")
        freed_space = system_cleaner.clean_apt_cache()
        if freed_space > 0:
            print(f"Espace libéré : {freed_space / 1024 / 1024:.2f} MB")
        else:
            print("Le cache APT était déjà propre ou une erreur est survenue.")

    elif action == 'temp':
        print("Nettoyage des fichiers temporaires...")
        freed_space = system_cleaner.clean_temp_files()
        print(f"Espace libéré : {freed_space / 1024 / 1024:.2f} MB")

    elif action == 'logs':
        print("Nettoyage des journaux système...")
        success = system_cleaner.clean_journal_logs()
        if success:
            print("Les journaux ont été nettoyés avec succès.")
        else:
            print("Erreur lors du nettoyage des journaux.")

    elif action == 'autoremove':
        print("Suppression des paquets inutiles...")
        success = system_cleaner.autoremove_packages()
        if success:
            print("Autoremove terminé.")
        else:
            print("Erreur lors de l'autoremove.")

    elif action == 'snap':
        print("Nettoyage du cache Snap...")
        freed_space = app_cleaner.clean_snap_cache()
        print(f"Espace libéré : {freed_space / 1024 / 1024:.2f} MB")

    else:
        print(f"Action '{action}' non reconnue.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
