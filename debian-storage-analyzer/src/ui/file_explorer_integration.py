# -*- coding: utf-8 -*-
"""
Intégration avec l'explorateur de fichiers
Permet d'ouvrir des fichiers/dossiers dans l'explorateur système
"""

import os
import subprocess
import shutil
from typing import Optional
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio


class FileExplorerIntegration:
    """Gestionnaire d'intégration avec l'explorateur de fichiers"""
    
    def __init__(self):
        self.preferred_file_manager = self._detect_file_manager()
    
    def _detect_file_manager(self) -> str:
        """Détecte l'explorateur de fichiers disponible sur le système"""
        file_managers = [
            ('nautilus', 'Nautilus (GNOME)'),
            ('pcmanfm', 'PCManFM (LXDE)'),
            ('thunar', 'Thunar (XFCE)'),
            ('dolphin', 'Dolphin (KDE)'),
            ('nemo', 'Nemo (Cinnamon)'),
            ('caja', 'Caja (MATE)'),
        ]
        
        for fm_cmd, fm_name in file_managers:
            if shutil.which(fm_cmd):
                print(f"Explorateur détecté: {fm_name}")
                return fm_cmd
        
        return 'xdg-open'  # Fallback universel
    
    def open_file_location(self, file_path: str) -> bool:
        """
        Ouvre l'emplacement d'un fichier dans l'explorateur
        
        Args:
            file_path: Chemin vers le fichier ou dossier
            
        Returns:
            True si l'ouverture a réussi, False sinon
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            if not os.path.exists(abs_path):
                return False
            
            if self.preferred_file_manager == 'nautilus':
                # Nautilus peut sélectionner le fichier
                if os.path.isfile(abs_path):
                    subprocess.Popen(['nautilus', '--select', abs_path])
                else:
                    subprocess.Popen(['nautilus', abs_path])
            
            elif self.preferred_file_manager == 'dolphin':
                # Dolphin peut aussi sélectionner
                if os.path.isfile(abs_path):
                    subprocess.Popen(['dolphin', '--select', abs_path])
                else:
                    subprocess.Popen(['dolphin', abs_path])
            
            elif self.preferred_file_manager in ['thunar', 'pcmanfm', 'nemo', 'caja']:
                # Pour les autres, ouvrir le dossier parent si c'est un fichier
                if os.path.isfile(abs_path):
                    parent_dir = os.path.dirname(abs_path)
                    subprocess.Popen([self.preferred_file_manager, parent_dir])
                else:
                    subprocess.Popen([self.preferred_file_manager, abs_path])
            
            else:
                # Fallback avec xdg-open
                if os.path.isfile(abs_path):
                    parent_dir = os.path.dirname(abs_path)
                    subprocess.Popen(['xdg-open', parent_dir])
                else:
                    subprocess.Popen(['xdg-open', abs_path])
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'ouverture de {file_path}: {e}")
            return False
    
    def open_file_with_default_app(self, file_path: str) -> bool:
        """
        Ouvre un fichier avec l'application par défaut
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            True si l'ouverture a réussi, False sinon
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            if not os.path.isfile(abs_path):
                return False
            
            subprocess.Popen(['xdg-open', abs_path])
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'ouverture de {file_path}: {e}")
            return False
    
    def get_file_properties(self, file_path: str) -> Optional[dict]:
        """
        Récupère les propriétés d'un fichier
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Dictionnaire avec les propriétés ou None
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            if not os.path.exists(abs_path):
                return None
            
            stat = os.stat(abs_path)
            
            return {
                'path': abs_path,
                'name': os.path.basename(abs_path),
                'size': stat.st_size,
                'is_dir': os.path.isdir(abs_path),
                'is_file': os.path.isfile(abs_path),
                'modified': stat.st_mtime,
                'permissions': oct(stat.st_mode)[-3:],
                'owner_readable': os.access(abs_path, os.R_OK),
                'owner_writable': os.access(abs_path, os.W_OK),
                'owner_executable': os.access(abs_path, os.X_OK),
            }
            
        except Exception as e:
            print(f"Erreur lors de la récupération des propriétés de {file_path}: {e}")
            return None


class ContextMenuHandler:
    """Gestionnaire de menu contextuel pour les fichiers"""
    
    def __init__(self, file_explorer: FileExplorerIntegration):
        self.file_explorer = file_explorer
    
    def create_context_menu(self, file_path: str) -> Gtk.Menu:
        """
        Crée un menu contextuel pour un fichier/dossier
        
        Args:
            file_path: Chemin vers le fichier ou dossier
            
        Returns:
            Menu contextuel GTK
        """
        menu = Gtk.Menu()
        
        # Ouvrir dans l'explorateur
        open_location_item = Gtk.MenuItem(label="📁 Ouvrir l'emplacement")
        open_location_item.connect("activate", 
                                 lambda w: self.file_explorer.open_file_location(file_path))
        menu.append(open_location_item)
        
        # Si c'est un fichier, ajouter "Ouvrir avec"
        if os.path.isfile(file_path):
            open_with_item = Gtk.MenuItem(label="🚀 Ouvrir avec l'app par défaut")
            open_with_item.connect("activate", 
                                 lambda w: self.file_explorer.open_file_with_default_app(file_path))
            menu.append(open_with_item)
        
        # Séparateur
        menu.append(Gtk.SeparatorMenuItem())
        
        # Copier le chemin
        copy_path_item = Gtk.MenuItem(label="📋 Copier le chemin")
        copy_path_item.connect("activate", lambda w: self._copy_path_to_clipboard(file_path))
        menu.append(copy_path_item)
        
        # Propriétés
        properties_item = Gtk.MenuItem(label="ℹ️ Propriétés")
        properties_item.connect("activate", lambda w: self._show_properties_dialog(file_path))
        menu.append(properties_item)
        
        menu.show_all()
        return menu
    
    def _copy_path_to_clipboard(self, file_path: str):
        """Copie le chemin du fichier dans le presse-papiers"""
        try:
            clipboard = Gtk.Clipboard.get(gi.repository.Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(os.path.abspath(file_path), -1)
            print(f"Chemin copié: {file_path}")
        except Exception as e:
            print(f"Erreur lors de la copie: {e}")
    
    def _show_properties_dialog(self, file_path: str):
        """Affiche une boîte de dialogue avec les propriétés du fichier"""
        properties = self.file_explorer.get_file_properties(file_path)
        
        if not properties:
            return
        
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"Propriétés de {properties['name']}"
        )
        
        details = f"""
Chemin: {properties['path']}
Taille: {self._format_size(properties['size'])}
Type: {'Dossier' if properties['is_dir'] else 'Fichier'}
Permissions: {properties['permissions']}
Modifié: {self._format_timestamp(properties['modified'])}
        """.strip()
        
        dialog.format_secondary_text(details)
        dialog.run()
        dialog.destroy()
    
    def _format_size(self, size: int) -> str:
        """Formate une taille en octets"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Formate un timestamp"""
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%d/%m/%Y %H:%M:%S")


def setup_treeview_context_menu(treeview: Gtk.TreeView, 
                               path_column_index: int = 0) -> ContextMenuHandler:
    """
    Configure un menu contextuel pour un TreeView
    
    Args:
        treeview: Le TreeView à configurer
        path_column_index: Index de la colonne contenant le chemin du fichier
        
    Returns:
        Le gestionnaire de menu contextuel
    """
    file_explorer = FileExplorerIntegration()
    context_handler = ContextMenuHandler(file_explorer)
    
    def on_button_press(widget, event):
        if event.button == 3:  # Clic droit
            path = widget.get_path_at_pos(int(event.x), int(event.y))
            if path:
                tree_path, column, cell_x, cell_y = path
                model = widget.get_model()
                iter = model.get_iter(tree_path)
                file_path = model.get_value(iter, path_column_index)
                
                menu = context_handler.create_context_menu(file_path)
                menu.popup(None, None, None, None, event.button, event.time)
                return True
        return False
    
    treeview.connect("button-press-event", on_button_press)
    return context_handler