# Roadmap et Améliorations Futures

Voici l'état d'avancement des pistes d'amélioration identifiées :

## ✅ Réalisé
- [x] **Navigation par onglets** : Utilisation de `Gtk.Stack` et `Gtk.StackSidebar`.
- [x] **Visualisation de données** : Intégration d'un graphique Camembert avec `Matplotlib` sur le Dashboard.
- [x] **Multithreading** : Scans et nettoyages exécutés dans des threads séparés pour la réactivité de l'UI.
- [x] **Scan haute performance** : Migration vers `os.scandir()`.
- [x] **Nettoyage étendu** : Ajout de l'autoremove APT et du cache Flatpak.
- [x] **Internationalisation (i18n)** : Infrastructure mise en place avec `gettext`.
- [x] **Sécurité (PolicyKit)** : Intégration correcte de `pkexec` pour les tâches root.

## 🎨 Interface Utilisateur (UI/UX)
- [ ] **Indicateurs de progression** : Ajouter des barres de progression pour les opérations longues.
- [ ] **Thème sombre** : Assurer une compatibilité parfaite avec les thèmes sombres de GNOME.

## ⚡ Optimisations et Performance
- [ ] **Mise en cache** : Mémoriser les résultats des analyses récentes.

## 🚀 Nouvelles Fonctionnalités
- [ ] **Analyse des Paquets** : Lister les paquets installés (`dpkg`/`apt`) par taille.
- [ ] **Nettoyage étendu** :
    - [ ] Cache Snap (nécessite root).
    - [ ] Miniatures d'images (thumbnails).
    - [ ] Vidage de la corbeille.
- [ ] **Recherche de Doublons** : Identifier les fichiers identiques pour gagner de l'espace.

## 🛠 Qualité de Code et Maintenance
- [ ] **Internationalisation (i18n)** : Traduction complète des fichiers `.po`.
- [ ] **Tests Automatisés** : Suite de tests unitaires avec `pytest`.
