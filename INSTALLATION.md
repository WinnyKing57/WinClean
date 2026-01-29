# Installation de l'Analyseur de Stockage Debian v3.1

## 🆕 Nouveautés Version 3.1

### Interface Moderne Avancée
- **Sidebar moderne** avec navigation fluide et thèmes adaptatifs
- **Intégration explorateur** : Clic droit sur fichiers pour ouvrir dans l'explorateur
- **Emplacements complets** : Affichage des chemins complets des fichiers
- **Installation automatique** : Les dépendances s'installent automatiquement avec le .deb

### Fonctionnalités Avancées
- **Graphiques interactifs** et tableaux triables avec colonnes redimensionnables
- **Détection de doublons** avec hash SHA-256
- **Analyse par catégories** (images, vidéos, documents, archives)
- **Surveillance temps réel** avec notifications desktop
- **Historique complet** des analyses et nettoyages avec tendances

## 🚀 Installation Rapide (Recommandée)

### Option 1: Installation locale (pour tester)
```bash
./install_local.sh
```

### Option 2: Construction et installation du package Debian v3.0
```bash
./build_and_install.sh
```
**✨ Nouveau :** Les dépendances s'installent automatiquement !

## 📋 Prérequis

### Dépendances de construction (pour build_and_install.sh)
```bash
sudo apt install debhelper build-essential
```
**Note :** Le script `build_and_install.sh` installe automatiquement ces dépendances.

### Dépendances d'exécution (installation automatique avec .deb)
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
                 python3-psutil python3-matplotlib python3-pandas \
                 python3-reportlab
```
**✨ Nouveau :** Ces dépendances s'installent automatiquement lors de l'installation du package .deb !

## 🎯 Utilisation après installation

L'application sera disponible :
- **Terminal** : `debian-storage-analyzer`
- **Menu Applications** : Système > Analyseur de Stockage Debian 3.0
- **Discover/Software Center** : Rechercher "Analyseur de Stockage"

## 🆕 Nouvelles Fonctionnalités v3.0

### Interface Moderne
- **Sidebar avec navigation fluide** entre Dashboard, Analyse, Nettoyage, Historique
- **Thèmes adaptatifs** : Suit automatiquement le thème système (clair/sombre)
- **Colonnes redimensionnables** dans les tableaux avec tri avancé

### Intégration Explorateur
- **Clic droit sur fichiers** : Menu contextuel avec options d'ouverture
- **"Ouvrir l'emplacement"** : Ouvre le dossier dans l'explorateur système
- **"Ouvrir avec l'app par défaut"** : Lance le fichier avec son application
- **Copier le chemin** : Copie le chemin complet dans le presse-papiers
- **Propriétés** : Affiche les détails du fichier (taille, permissions, etc.)

### Affichage Amélioré
- **Colonne "Emplacement"** : Affiche le chemin complet de chaque fichier
- **Chemins ellipsés** : Affichage intelligent des longs chemins
- **Fenêtre plus grande** : Interface optimisée pour plus d'informations

## 🔧 Résolution des problèmes

### L'application ne se lance pas
1. **Avec le package .deb** : Les dépendances s'installent automatiquement
2. **Installation manuelle** : Vérifiez que les dépendances sont installées :
   ```bash
   debian-storage-analyzer
   ```
   Le lanceur vous guidera pour installer les dépendances manquantes.

### Problème avec l'environnement conda/venv
Si vous utilisez conda ou un environnement virtuel, l'application utilise automatiquement le Python système pour accéder aux packages installés via `apt`.

### L'application n'apparaît pas dans le menu
```bash
update-desktop-database ~/.local/share/applications/
```

### L'application n'apparaît pas dans Discover
1. Vérifiez que le fichier metainfo est présent
2. Redémarrez Discover ou votre session

## 🗑️ Désinstallation

```bash
./uninstall.sh
```

## 📁 Structure des fichiers installés

### Installation locale
- `~/.local/bin/debian-storage-analyzer` - Lanceur principal
- `~/.local/share/applications/debian-storage-analyzer.desktop` - Fichier .desktop
- `~/.local/share/metainfo/fr.jules.debianstorageanalyzer.desktop.metainfo.xml` - Métadonnées

### Installation système (package .deb v3.0)
- `/usr/bin/debian-storage-analyzer` - Lanceur principal
- `/usr/share/debian-storage-analyzer/` - Code source de l'application
- `/usr/share/applications/fr.jules.debianstorageanalyzer.desktop` - Fichier .desktop
- `/usr/share/metainfo/fr.jules.debianstorageanalyzer.desktop.metainfo.xml` - Métadonnées
- `/usr/libexec/debian-storage-analyzer-helper` - Helper pour les opérations privilégiées
- `/usr/share/polkit-1/actions/fr.jules.debianstorageanalyzer.policy` - Règles PolicyKit

## 🛠️ Développement

Pour développer l'application :
1. Installez les dépendances
2. Lancez directement : `python3 debian-storage-analyzer/simple_launcher.py`

## 📝 Notes v3.0

- **Installation automatique** : Plus besoin d'installer manuellement les dépendances avec le .deb
- **Interface moderne** : Sidebar, thèmes adaptatifs, colonnes redimensionnables
- **Intégration explorateur** : Clic droit pour ouvrir fichiers/dossiers dans l'explorateur
- **Emplacements complets** : Nouvelle colonne affichant les chemins complets
- **Compatibilité environnements** : Fonctionne même dans conda/venv en utilisant le Python système
- **Installation locale** parfaite pour tester sans affecter le système
- **Installation via package .deb** recommandée pour un usage quotidien avec installation automatique des dépendances