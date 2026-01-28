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
    echo "❌ Dépendances de build manquantes: $MISSING_DEPS"
    echo "📦 Installation automatique des dépendances de build..."
    sudo apt update
    sudo apt install -y $MISSING_DEPS
fi

# Nettoyer les anciens builds
echo "🧹 Nettoyage des anciens builds..."
rm -f ../debian-storage-analyzer_*.deb
rm -f ../debian-storage-analyzer_*.changes
rm -f ../debian-storage-analyzer_*.buildinfo
rm -rf debian-storage-analyzer/debian/debian-storage-analyzer/

# Construire le package
echo "🔧 Construction du package v3.0..."
cd debian-storage-analyzer

if dpkg-buildpackage -us -uc -b; then
    echo "✅ Package v3.0 construit avec succès!"
    
    # Installer le package
    echo "📦 Installation du package v3.0..."
    cd ..
    
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
    echo "❌ Erreur lors de la construction du package"
    exit 1
fi