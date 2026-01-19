# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path

# Importer les helpers du module de nettoyage système.
# L'astuce sys.path est nécessaire pour l'exécution en tant que script.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cleaner.system_cleaner import get_dir_size

def clean_firefox_cache():
    """
    Nettoie le cache de tous les profils Firefox trouvés.
    Opère avec les droits de l'utilisateur.
    """
    firefox_cache_dir = Path.home() / ".cache/mozilla/firefox"
    freed_space = 0

    if not firefox_cache_dir.is_dir():
        return 0

    # Itérer sur les répertoires de profils (ex: abcde123.default-release)
    for profile_dir in firefox_cache_dir.iterdir():
        if profile_dir.is_dir() and profile_dir.name.endswith((".default", ".default-release")):
            cache_path = profile_dir / "cache2"
            if cache_path.is_dir():
                size = get_dir_size(str(cache_path))
                try:
                    shutil.rmtree(str(cache_path))
                    freed_space += size
                except OSError as e:
                    print(f"Erreur lors de la suppression du cache de Firefox {cache_path}: {e}")

    return freed_space

def clean_chromium_cache():
    """
    Nettoie le cache de Chromium.
    Opère avec les droits de l'utilisateur.
    """
    chromium_cache_dir = Path.home() / ".cache/chromium"
    freed_space = 0

    if not chromium_cache_dir.is_dir():
        return 0

    # Le cache principal de Chromium
    cache_path = chromium_cache_dir / "Default" / "Cache"
    if cache_path.is_dir():
        size = get_dir_size(str(cache_path))
        try:
            shutil.rmtree(str(cache_path))
            freed_space += size
        except OSError as e:
            print(f"Erreur lors de la suppression du cache de Chromium {cache_path}: {e}")

    return freed_space


if __name__ == '__main__':
    print("--- Test du module de nettoyage d'applications ---")

    # Créer un faux répertoire HOME pour les tests
    fake_home_dir = Path("./temp_test_app_cleaner")
    if fake_home_dir.exists():
        shutil.rmtree(fake_home_dir)

    # Les fonctions cherchent dans ~/.cache/, nous devons donc recréer cette structure.
    fake_cache_dir = fake_home_dir / ".cache"

    # Faux cache Firefox
    ff_profile = fake_cache_dir / "mozilla/firefox/test123.default-release/cache2/entries"
    os.makedirs(ff_profile)
    with open(ff_profile / "dummy_file", "w") as f:
        f.write("a" * 2048) # 2 Ko

    # Faux cache Chromium
    chromium_cache = fake_cache_dir / "chromium/Default/Cache/data_1"
    os.makedirs(os.path.dirname(chromium_cache))
    with open(chromium_cache, "w") as f:
        f.write("a" * 4096) # 4 Ko

    # Remplacer Path.home() pour pointer vers notre faux HOME
    original_home = Path.home
    Path.home = lambda: fake_home_dir

    print("Nettoyage du faux cache Firefox...")
    ff_freed = clean_firefox_cache()
    print(f"Espace libéré : {ff_freed} octets")
    assert ff_freed == 2048

    print("Nettoyage du faux cache Chromium...")
    chromium_freed = clean_chromium_cache()
    print(f"Espace libéré : {chromium_freed} octets")
    assert chromium_freed == 4096

    # Restaurer Path.home() à sa valeur d'origine
    Path.home = original_home

    print("Tests du nettoyeur d'applications : SUCCÈS")

    # Nettoyage final
    shutil.rmtree(fake_home_dir)
    print("Environnement de test nettoyé.")
