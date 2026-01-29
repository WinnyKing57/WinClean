#!/bin/bash
# Script pour construire et installer le package Debian v3.0

set -e

echo "🚀 Construction du package Debian Storage Analyzer v3.0..."

# Vérifier les dépendances de build
echo "📋 Vérification des dépendances de build..."
MISSING_DEPS=""

if ! dpkg -l | grep -q "debhelper"; then
    MISSING_DEPS="$MISSING_DEPS debhelper"
fi

if ! dpkg -l | grep -q "build-essential"; then
    MISSING_DEPS="$MISSING_DEPS build-essential"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo "📦 Installation automatique des dépendances de build..."
    sudo apt update
    sudo apt install -y $MISSING_DEPS
fi

# Nettoyer les anciens builds (plus robuste)
echo "🧹 Nettoyage complet des anciens builds..."
rm -f ../debian-storage-analyzer_*.deb
rm -f ../debian-storage-analyzer_*.changes
rm -f ../debian-storage-analyzer_*.buildinfo
rm -f ../debian-storage-analyzer_*.tar.xz
rm -f ../debian-storage-analyzer_*.dsc

# Nettoyer le répertoire de build
cd debian-storage-analyzer

# Nettoyage complet avec debian/rules
echo "🧹 Nettoyage avec debian/rules..."
debian/rules clean || true

# Nettoyage manuel des fichiers restants
echo "🧹 Nettoyage manuel des fichiers temporaires..."
rm -rf debian/debian-storage-analyzer
rm -rf debian/.debhelper
rm -f debian/files
rm -f debian/debhelper-build-stamp
rm -f debian/*.substvars
rm -f debian/*.log

# Construire le package
echo "🔧 Construction du package v3.0..."
if dpkg-buildpackage -us -uc -b; then
    echo "✅ Package v3.0 construit avec succès!"
    
    # Installer le package si demandé
    cd ..
    
    if [ "$1" = "--install" ]; then
        echo "📦 Installation du package v3.0..."
        
        if sudo dpkg -i debian-storage-analyzer_*.deb; then
            echo "✅ Package v3.0 installé avec succès!"
            
            # Les dépendances sont maintenant installées automatiquement par le postinst
            echo "🔄 Les dépendances ont été installées automatiquement..."
            
            echo ""
            echo "🎉 Installation v3.0 terminée!"
            echo ""
            echo "✨ Nouvelles fonctionnalités v3.0:"
            echo "   • Interface moderne avec thèmes adaptatifs"
            echo "   • Clic droit sur fichiers pour ouvrir dans l'explorateur"
            echo "   • Affichage des emplacements complets des fichiers"
            echo "   • Installation automatique des dépendances"
            echo "   • Graphiques interactifs et détection de doublons"
            echo ""
            echo "🎯 Vous pouvez maintenant:"
            echo "   • Lancer l'app depuis le terminal: debian-storage-analyzer"
            echo "   • La trouver dans le menu Applications > Système"
            echo "   • La chercher dans Discover/Software Center"
            echo ""
            echo "🔍 Pour vérifier l'installation:"
            echo "   dpkg -l | grep debian-storage-analyzer"
            
        else
            echo "❌ Erreur lors de l'installation du package"
            echo "   Les dépendances seront installées automatiquement au prochain essai"
            echo "   Essayez: sudo apt-get install -f"
            exit 1
        fi
    else
        echo "📦 Package créé: $(ls debian-storage-analyzer_*.deb)"
        echo ""
        echo "Pour installer:"
        echo "   sudo dpkg -i debian-storage-analyzer_*.deb"
        echo "   sudo apt-get install -f  # Si des dépendances manquent"
    fi
    
else
    echo "❌ Erreur lors de la construction du package"
    echo "🔍 Vérifiez les logs ci-dessus pour plus de détails"
    exit 1
fi