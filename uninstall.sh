#!/bin/bash
# Script de désinstallation pour l'Analyseur de Stockage Debian

echo "🗑️  Désinstallation de l'Analyseur de Stockage Debian..."

# Désinstaller le package système s'il existe
if dpkg -l | grep -q debian-storage-analyzer; then
    echo "📦 Désinstallation du package système..."
    sudo apt remove --purge debian-storage-analyzer -y
fi

# Nettoyer l'installation locale
echo "🧹 Nettoyage de l'installation locale..."

# Supprimer les fichiers locaux
rm -f ~/.local/bin/debian-storage-analyzer
rm -f ~/.local/share/applications/debian-storage-analyzer.desktop
rm -f ~/.local/share/metainfo/fr.jules.debianstorageanalyzer.desktop.metainfo.xml

# Mettre à jour les bases de données
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
fi

# Nettoyer la configuration utilisateur (optionnel)
read -p "🤔 Voulez-vous aussi supprimer la configuration utilisateur? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗂️  Suppression de la configuration..."
    rm -rf ~/.config/debian-storage-analyzer/
    rm -rf ~/.local/share/debian-storage-analyzer/
fi

echo "✅ Désinstallation terminée!"