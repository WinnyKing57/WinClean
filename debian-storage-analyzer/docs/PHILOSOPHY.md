# Philosophie du Projet : Analyseur de Stockage Debian

Ce document décrit les principes directeurs, les choix techniques et la vision à long terme de l'Analyseur de Stockage Debian.

## 1. Principes Fondamentaux

- **Simplicité et Clarté** : L'interface doit être intuitive et aller droit au but. L'utilisateur ne doit jamais se sentir perdu. Chaque fonctionnalité doit avoir un objectif clair et compréhensible.
- **Sécurité avant tout** : L'application touche à des parties sensibles du système. Le principe du moindre privilège est donc non négociable. L'interface utilisateur ne doit jamais s'exécuter avec des droits `root`. Toutes les actions privilégiées doivent être déléguées à un mécanisme sécurisé comme PolicyKit.
- **Intégration à Debian** : Ce n'est pas une application générique pour Linux, mais une application conçue *pour* Debian. Cela signifie utiliser les outils standards de Debian (`apt`, `journalctl`), respecter l'arborescence du système de fichiers (FHS), et fournir un packaging `.deb` propre et de haute qualité.
- **Modularité** : La séparation des préoccupations est essentielle. Le code de l'interface (UI), la logique d'analyse (Analyzer) et la logique de nettoyage (Cleaner) doivent être dans des modules distincts et bien définis pour faciliter la maintenance et les tests.

## 2. Choix Techniques

- **Langage : Python 3**
  - **Raison** : omniprésent sur les systèmes Debian, il dispose d'un écosystème de bibliothèques très riche et permet un développement rapide et lisible.

- **Interface Graphique : GTK (via PyGObject)**
  - **Raison** : C'est la boîte à outils native de l'environnement de bureau GNOME, qui est le bureau par défaut de Debian. Utiliser GTK garantit une intégration visuelle parfaite et une performance optimale sans ajouter de lourdes dépendances.

- **Sécurité : PolicyKit**
  - **Raison** : C'est le framework standard et moderne sur les systèmes Linux de bureau pour gérer les permissions et l'élévation de privilèges. Il est bien plus propre et sécurisé que de lancer toute l'application avec `sudo` ou de bricoler avec le bit `setuid`.

- **Packaging : .deb**
  - **Raison** : C'est le format de paquet natif de Debian. Fournir un paquet `.deb` est la seule manière correcte de distribuer une application système pour cet environnement.

## 3. Vision et Évolution Future

Ce projet initial pose des bases solides. Voici les axes d'évolution envisagés :

- **Amélioration de la visualisation** : Intégrer Matplotlib pour créer des graphiques (camemberts, barres) afin de rendre l'analyse plus visuelle et plus facile à interpréter.
- **Analyse plus fine** : Permettre de "descendre" dans l'arborescence depuis l'interface pour explorer les sous-dossiers et trouver plus précisément où se trouve l'espace utilisé.
- **Nettoyage des fichiers personnels** : Ajouter un module pour identifier les fichiers volumineux ou les doublons dans le répertoire personnel de l'utilisateur. Cette fonctionnalité devra être conçue avec une extrême prudence, avec de multiples confirmations de l'utilisateur.
- **Internationalisation (i18n)** : Permettre la traduction de l'interface en plusieurs langues.
- **Tests unitaires** : Développer une suite de tests complète pour garantir la non-régression et la fiabilité des modules `analyzer` et `cleaner`.
