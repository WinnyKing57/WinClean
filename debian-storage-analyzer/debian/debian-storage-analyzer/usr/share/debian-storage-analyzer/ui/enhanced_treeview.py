# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio
import gettext
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

_ = gettext.gettext

@dataclass
class ColumnConfig:
    """Configuration d'une colonne du TreeView"""
    title: str
    data_type: type
    sortable: bool = True
    filterable: bool = True
    renderer_type: str = "text"  # text, progress, icon
    width: int = -1

class EnhancedTreeView(Gtk.TreeView):
    """TreeView amélioré avec tri, filtrage et drag-and-drop"""
    
    def __init__(self, columns: List[ColumnConfig]):
        super().__init__()
        
        self.columns_config = columns
        self.filter_model = None
        self.sort_model = None
        self.base_model = None
        self.filters = {}
        
        # Configuration du style
        self.get_style_context().add_class("enhanced-treeview")
        
        # Configurer les colonnes
        self._setup_columns()
        
        # Configurer le tri et le filtrage
        self._setup_sorting_and_filtering()
        
        # Configurer le drag-and-drop
        self._setup_drag_and_drop()
        
        # Configurer la sélection multiple
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
    
    def _setup_columns(self):
        """Configure les colonnes du TreeView"""
        # Créer le modèle de base
        column_types = []
        for config in self.columns_config:
            if config.data_type == str:
                column_types.append(str)
            elif config.data_type == int:
                column_types.append(int)
            elif config.data_type == float:
                column_types.append(float)
            elif config.data_type == bool:
                column_types.append(bool)
            else:
                column_types.append(str)  # Fallback
        
        self.base_model = Gtk.ListStore(*column_types)
        
        # Créer les colonnes
        for i, config in enumerate(self.columns_config):
            column = self._create_column(config, i)
            self.append_column(column)
    
    def _create_column(self, config: ColumnConfig, column_id: int) -> Gtk.TreeViewColumn:
        """Crée une colonne avec la configuration spécifiée"""
        
        if config.renderer_type == "progress":
            renderer = Gtk.CellRendererProgress()
            column = Gtk.TreeViewColumn(config.title, renderer, value=column_id)
        elif config.renderer_type == "icon":
            renderer = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn(config.title, renderer, icon_name=column_id)
        else:  # text par défaut
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(config.title, renderer, text=column_id)
        
        # Configuration de la colonne
        if config.width > 0:
            column.set_fixed_width(config.width)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        else:
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        
        column.set_resizable(True)
        column.set_reorderable(True)
        
        # Configuration du tri
        if config.sortable:
            column.set_sort_column_id(column_id)
            column.set_clickable(True)
            
            # Ajouter une icône de tri
            header_button = column.get_button()
            if header_button:
                header_button.get_style_context().add_class("sortable-header")
        
        return column
    
    def _setup_sorting_and_filtering(self):
        """Configure le tri et le filtrage"""
        # Modèle de filtrage
        self.filter_model = self.base_model.filter_new()
        self.filter_model.set_visible_func(self._filter_func)
        
        # Modèle de tri
        self.sort_model = Gtk.TreeModelSort(model=self.filter_model)
        
        # Configurer les fonctions de tri personnalisées
        for i, config in enumerate(self.columns_config):
            if config.sortable:
                self.sort_model.set_sort_func(i, self._sort_func, i)
        
        # Appliquer le modèle au TreeView
        self.set_model(self.sort_model)
    
    def _setup_drag_and_drop(self):
        """Configure le drag-and-drop"""
        # Accepter les drops de fichiers/dossiers
        targets = [
            Gtk.TargetEntry.new("text/uri-list", 0, 0),
            Gtk.TargetEntry.new("text/plain", 0, 1)
        ]
        
        self.drag_dest_set(
            Gtk.DestDefaults.ALL,
            targets,
            Gdk.DragAction.COPY
        )
        
        # Connecter les signaux
        self.connect("drag-data-received", self._on_drag_data_received)
        self.connect("drag-motion", self._on_drag_motion)
        self.connect("drag-drop", self._on_drag_drop)
    
    def _filter_func(self, model, iter, data):
        """Fonction de filtrage"""
        if not self.filters:
            return True
        
        for column_id, filter_value in self.filters.items():
            if filter_value is None or filter_value == "":
                continue
                
            cell_value = model.get_value(iter, column_id)
            
            # Filtrage selon le type de données
            config = self.columns_config[column_id]
            
            if config.data_type == str:
                if filter_value.lower() not in str(cell_value).lower():
                    return False
            elif config.data_type in [int, float]:
                try:
                    filter_num = float(filter_value)
                    if float(cell_value) < filter_num:
                        return False
                except (ValueError, TypeError):
                    continue
            elif config.data_type == bool:
                filter_bool = filter_value.lower() in ['true', '1', 'yes', 'oui']
                if bool(cell_value) != filter_bool:
                    return False
        
        return True
    
    def _sort_func(self, model, iter1, iter2, column_id):
        """Fonction de tri personnalisée"""
        value1 = model.get_value(iter1, column_id)
        value2 = model.get_value(iter2, column_id)
        
        config = self.columns_config[column_id]
        
        # Tri selon le type de données
        if config.data_type == str:
            return self._compare_strings(str(value1), str(value2))
        elif config.data_type in [int, float]:
            return self._compare_numbers(value1, value2)
        elif config.data_type == bool:
            return self._compare_booleans(value1, value2)
        
        return 0
    
    def _compare_strings(self, str1: str, str2: str) -> int:
        """Compare deux chaînes de caractères"""
        if str1 < str2:
            return -1
        elif str1 > str2:
            return 1
        return 0
    
    def _compare_numbers(self, num1, num2) -> int:
        """Compare deux nombres"""
        try:
            n1 = float(num1) if num1 is not None else 0
            n2 = float(num2) if num2 is not None else 0
            
            if n1 < n2:
                return -1
            elif n1 > n2:
                return 1
            return 0
        except (ValueError, TypeError):
            return 0
    
    def _compare_booleans(self, bool1, bool2) -> int:
        """Compare deux booléens"""
        b1 = bool(bool1)
        b2 = bool(bool2)
        
        if b1 == b2:
            return 0
        elif b1:
            return 1
        else:
            return -1
    
    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        """Callback pour la réception de données drag-and-drop"""
        if info == 0:  # text/uri-list
            uris = data.get_uris()
            if uris:
                # Émettre un signal personnalisé avec les URIs
                self.emit("files-dropped", uris)
        elif info == 1:  # text/plain
            text = data.get_text()
            if text:
                self.emit("text-dropped", text)
        
        context.finish(True, False, time)
    
    def _on_drag_motion(self, widget, context, x, y, time):
        """Callback pour le mouvement de drag"""
        # Indiquer que le drop est accepté
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True
    
    def _on_drag_drop(self, widget, context, x, y, time):
        """Callback pour le drop"""
        # Demander les données
        target = widget.drag_dest_find_target(context, None)
        if target != Gdk.Atom.intern("NONE", False):
            widget.drag_get_data(context, target, time)
            return True
        return False
    
    def add_row(self, data: List[Any]):
        """Ajoute une ligne au modèle"""
        if len(data) != len(self.columns_config):
            raise ValueError(f"Expected {len(self.columns_config)} values, got {len(data)}")
        
        self.base_model.append(data)
    
    def clear(self):
        """Vide le modèle"""
        self.base_model.clear()
    
    def set_filter(self, column_id: int, filter_value: Any):
        """Définit un filtre pour une colonne"""
        if column_id < 0 or column_id >= len(self.columns_config):
            raise ValueError(f"Invalid column_id: {column_id}")
        
        self.filters[column_id] = filter_value
        self.filter_model.refilter()
    
    def clear_filters(self):
        """Supprime tous les filtres"""
        self.filters.clear()
        self.filter_model.refilter()
    
    def get_selected_rows_data(self) -> List[List[Any]]:
        """Retourne les données des lignes sélectionnées"""
        selection = self.get_selection()
        model, paths = selection.get_selected_rows()
        
        selected_data = []
        for path in paths:
            iter = model.get_iter(path)
            row_data = []
            for i in range(len(self.columns_config)):
                row_data.append(model.get_value(iter, i))
            selected_data.append(row_data)
        
        return selected_data
    
    def export_to_csv(self, filename: str):
        """Exporte les données vers un fichier CSV"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Écrire les en-têtes
            headers = [config.title for config in self.columns_config]
            writer.writerow(headers)
            
            # Écrire les données
            model = self.get_model()
            iter = model.get_iter_first()
            
            while iter:
                row_data = []
                for i in range(len(self.columns_config)):
                    row_data.append(model.get_value(iter, i))
                writer.writerow(row_data)
                iter = model.iter_next(iter)


# Enregistrer les signaux personnalisés
GLib.signal_new("files-dropped", EnhancedTreeView, GLib.SignalFlags.RUN_LAST,
                GLib.TYPE_NONE, (GLib.TYPE_PYOBJECT,))
GLib.signal_new("text-dropped", EnhancedTreeView, GLib.SignalFlags.RUN_LAST,
                GLib.TYPE_NONE, (GLib.TYPE_STRING,))