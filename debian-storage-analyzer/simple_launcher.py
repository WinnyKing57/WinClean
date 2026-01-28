#!/usr/bin/env python3
"""
Lanceur pour Debian Storage Analyzer v3.0
Interface moderne avec intégration explorateur de fichiers
"""

import sys
import subprocess
import os

def check_dependencies():
    """Vérifie si les dépendances sont installées"""
    missing = []
    
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except ImportError:
        missing.append("python3-gi python3-gi-cairo gir1.2-gtk-3.0")
    except ValueError:
        missing.append("gir1.2-gtk-3.0")
    
    try:
        import psutil
    except ImportError:
        missing.append("python3-psutil")
    
    try:
        import matplotlib
    except ImportError:
        missing.append("python3-matplotlib")
    
    try:
        import pandas
    except ImportError:
        missing.append("python3-pandas")
    
    try:
        import reportlab
    except ImportError:
        missing.append("python3-reportlab")
    
    return missing

def install_guide():
    """Guide d'installation des dépendances"""
    print("🔧 Dépendances manquantes détectées!")
    print("\n📦 Pour installer l'Analyseur de Stockage Debian v3.0, exécutez:")
    print("\n" + "="*70)
    print("sudo apt update")
    print("sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 \\")
    print("                 python3-psutil python3-matplotlib python3-pandas \\")
    print("                 python3-reportlab")
    print("="*70)
    print("\n✨ Puis relancez l'application depuis le menu ou avec:")
    print("   debian-storage-analyzer")
    print("\n💡 Astuce: Vous pouvez aussi chercher 'Analyseur de Stockage' dans Discover")
    print("\n🆕 Nouvelles fonctionnalités v3.0:")
    print("   • Interface moderne avec thèmes adaptatifs")
    print("   • Clic droit sur fichiers pour ouvrir dans l'explorateur")
    print("   • Affichage des emplacements complets des fichiers")
    print("   • Installation automatique des dépendances (.deb)")

def create_simple_gui():
    """Crée une interface simple pour guider l'installation"""
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, Gdk
        
        class InstallGuideWindow(Gtk.Window):
            def __init__(self):
                super().__init__(title="Analyseur de Stockage Debian v3.0 - Installation")
                self.set_default_size(600, 500)
                self.set_position(Gtk.WindowPosition.CENTER)
                self.set_resizable(False)
                
                # Container principal
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
                vbox.set_border_width(30)
                self.add(vbox)
                
                # Icône et titre
                header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
                
                icon = Gtk.Image.new_from_icon_name("drive-harddisk", Gtk.IconSize.DIALOG)
                header_box.pack_start(icon, False, False, 0)
                
                title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                title = Gtk.Label()
                title.set_markup("<span size='large' weight='bold'>Analyseur de Stockage Debian v3.0</span>")
                title.set_halign(Gtk.Align.START)
                title_box.pack_start(title, False, False, 0)
                
                subtitle = Gtk.Label("Interface moderne - Dépendances manquantes")
                subtitle.set_halign(Gtk.Align.START)
                title_box.pack_start(subtitle, False, False, 0)
                
                header_box.pack_start(title_box, True, True, 0)
                vbox.pack_start(header_box, False, False, 0)
                
                # Message
                message = Gtk.Label()
                message.set_markup(
                    "Pour utiliser l'Analyseur de Stockage Debian v3.0, vous devez d'abord\n"
                    "installer les dépendances système requises.\n\n"
                    "<b>Copiez et exécutez cette commande dans un terminal :</b>"
                )
                message.set_line_wrap(True)
                vbox.pack_start(message, False, False, 0)
                
                # Zone de commande
                frame = Gtk.Frame()
                frame.set_label("Commande d'installation")
                
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                scrolled.set_size_request(-1, 120)
                
                textview = Gtk.TextView()
                textview.set_editable(False)
                textview.set_cursor_visible(False)
                buffer = textview.get_buffer()
                buffer.set_text(
                    "sudo apt update\n"
                    "sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 \\\n"
                    "                 python3-psutil python3-matplotlib python3-pandas \\\n"
                    "                 python3-reportlab"
                )
                
                scrolled.add(textview)
                frame.add(scrolled)
                vbox.pack_start(frame, True, True, 0)
                
                # Nouvelles fonctionnalités v3.0
                features_frame = Gtk.Frame()
                features_frame.set_label("🆕 Nouvelles fonctionnalités v3.0")
                
                features_text = Gtk.Label()
                features_text.set_markup(
                    "• Interface moderne avec sidebar et thèmes adaptatifs\n"
                    "• Clic droit sur fichiers pour ouvrir dans l'explorateur\n"
                    "• Affichage des emplacements complets des fichiers\n"
                    "• Installation automatique des dépendances (package .deb)\n"
                    "• Graphiques interactifs et détection de doublons\n"
                    "• Surveillance temps réel et historique des analyses"
                )
                features_text.set_halign(Gtk.Align.START)
                features_text.set_margin_left(15)
                features_text.set_margin_right(15)
                features_text.set_margin_top(10)
                features_text.set_margin_bottom(10)
                
                features_frame.add(features_text)
                vbox.pack_start(features_frame, False, False, 0)
                
                # Boutons
                button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                button_box.set_halign(Gtk.Align.END)
                
                copy_btn = Gtk.Button(label="Copier la commande")
                copy_btn.connect("clicked", self.on_copy_clicked, buffer)
                button_box.pack_start(copy_btn, False, False, 0)
                
                close_btn = Gtk.Button(label="Fermer")
                close_btn.connect("clicked", lambda w: Gtk.main_quit())
                button_box.pack_start(close_btn, False, False, 0)
                
                vbox.pack_start(button_box, False, False, 0)
                
                self.show_all()
            
            def on_copy_clicked(self, widget, buffer):
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
                clipboard.set_text(text, -1)
                
                # Feedback visuel
                widget.set_label("✓ Copié!")
                def reset_label():
                    widget.set_label("Copier la commande")
                    return False
                from gi.repository import GLib
                GLib.timeout_add(2000, reset_label)
        
        app = InstallGuideWindow()
        Gtk.main()
        return True
        
    except Exception:
        return False

def main():
    missing = check_dependencies()
    
    if missing:
        # Essayer d'afficher l'interface graphique si GTK est disponible
        if not create_simple_gui():
            # Fallback vers l'interface texte
            install_guide()
        return 1
    
    # Si toutes les dépendances sont présentes, lancer l'application
    try:
        # Ajout du chemin src pour les imports
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
        
        from main.modern_main import ModernApplication
        app = ModernApplication()
        return app.run(sys.argv)
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        print("\nVérifiez que vous êtes dans le bon répertoire et que")
        print("toutes les dépendances sont installées.")
        return 1

if __name__ == "__main__":
    sys.exit(main())