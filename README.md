# Debian Storage Analyzer (Analyseur de Stockage Debian)

Une application graphique puissante et sécurisée conçue spécifiquement pour Debian afin d'analyser l'utilisation du stockage et de nettoyer le système.

## But de l'application

L'Analyseur de Stockage Debian est un outil tout-en-un pour la maintenance de votre espace disque. Il combine les fonctionnalités de plusieurs outils classiques (comme BleachBit ou Stacer) dans une interface moderne et parfaitement intégrée à l'écosystème Debian.

### Fonctionnalités principales :

*   **Analyse de stockage intelligente** : Scannez vos répertoires pour identifier instantanément les dossiers et fichiers les plus volumineux.
*   **Nettoyage Système Sécurisé** : Libérez de l'espace en supprimant le cache APT, en purgeant les anciens journaux système (`journalctl`) et en nettoyant les fichiers temporaires de manière prudente.
*   **Nettoyage d'Applications** : Identifiez et supprimez les caches encombrants des navigateurs web (Firefox, Chromium) et d'autres applications courantes.
*   **Recherche de Fichiers Volumineux** : Localisez rapidement les fichiers personnels massifs qui saturent votre disque dur.

## Philosophie du Projet

*   **Sécurité et Privilèges** : L'application suit le principe du moindre privilège. L'interface graphique s'exécute sans droits root, tandis que les actions sensibles sont gérées via PolicyKit.
*   **Intégration Debian** : Conçue exclusivement pour Debian, elle respecte les standards du système (FHS) et utilise les outils natifs.
*   **Packaging Natif** : Distribuée sous forme de paquet `.deb` pour une installation et une mise à jour simplifiées.

## Architecture Technique

*   **Langage** : Python 3
*   **Interface** : GTK 3 (via PyGObject)
*   **Sécurité** : PolicyKit (pkexec)
*   **Packaging** : Format Debian natif 3.0
