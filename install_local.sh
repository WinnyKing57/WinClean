#!/bin/bash
# Script d'installation locale pour tester l'Analyseur de Stockage Debian

set -e

echo "🚀 Installation locale de l'Analyseur de Stockage Debian..."

# Créer les répertoires nécessaires
mkdir -p ~/.local/bin
mkdir -p ~/.local/share/applications
mkdir -p ~/.local/share/metainfo

# Copier le lanceur principal
echo "📁 Installation du lanceur..."
cat > ~/.local/bin/debian-storage-analyzer << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_DIR="$HOME/Depot Github prso/WinClean/WinClean/debian-storage-analyzer"

if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    exec python3 simple_launcher.py "$@"
else
    echo "❌ Erreur: Répertoire du projet non trouvé: $PROJECT_DIR"
    echo "Veuillez ajuster le chemin dans ~/.local/bin/debian-storage-analyzer"
    exit 1
fi
EOF

chmod +x ~/.local/bin/debian-storage-analyzer

# Copier le fichier .desktop
echo "🖥️  Installation du fichier .desktop..."
cp debian-storage-analyzer/data/applications/fr.jules.debianstorageanalyzer.desktop \
   ~/.local/share/applications/debian-storage-analyzer.desktop

# Ajuster le fichier .desktop pour l'installation locale
sed -i 's|Exec=debian-storage-analyzer|Exec=/home/'$USER'/.local/bin/debian-storage-analyzer|g' \
   ~/.local/share/applications/debian-storage-analyzer.desktop

# Copier les métadonnées
echo "📋 Installation des métadonnées..."
cp debian-storage-analyzer/data/metainfo/fr.jules.debianstorageanalyzer.desktop.metainfo.xml \
   ~/.local/share/metainfo/

# Mettre à jour les bases de données
echo "🔄 Mise à jour des bases de données..."
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database ~/.local/share/applications/
fi

# Vérifier que ~/.local/bin est dans le PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  ATTENTION: ~/.local/bin n'est pas dans votre PATH"
    echo "   Ajoutez cette ligne à votre ~/.bashrc ou ~/.profile :"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "✅ Installation terminée!"
echo ""
echo "🎯 Vous pouvez maintenant:"
echo "   • Lancer l'app depuis le terminal: debian-storage-analyzer"
echo "   • La trouver dans le menu Applications > Système"
echo "   • La chercher dans Discover/Software Center"
echo ""
echo "📦 Pour installer les dépendances (si nécessaire):"
echo "   sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 \\"
echo "                    python3-psutil python3-matplotlib python3-pandas \\"
echo "                    python3-reportlab"