# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import gettext
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass

_ = gettext.gettext

@dataclass
class ChartData:
    """Données pour les graphiques"""
    labels: List[str]
    values: List[float]
    colors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class InteractiveCharts:
    """Gestionnaire de graphiques interactifs avec matplotlib et GTK"""
    
    def __init__(self, theme_manager=None):
        self.theme_manager = theme_manager
        self.click_callbacks = {}
        
        # Configuration des couleurs par défaut
        self.default_colors = [
            '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#f1c40f'
        ]
    
    def create_pie_chart(self, data: ChartData, title: str = "", 
                        interactive: bool = True, size: Tuple[int, int] = (400, 300)) -> Gtk.Widget:
        """Crée un graphique en camembert interactif"""
        
        # Créer la figure
        fig = Figure(figsize=(size[0]/100, size[1]/100), dpi=100)
        ax = fig.add_subplot(111)
        
        # Configurer les couleurs
        colors = data.colors or self.default_colors[:len(data.values)]
        
        # Créer le camembert
        wedges, texts, autotexts = ax.pie(
            data.values,
            labels=data.labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        # Améliorer l'apparence
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Rendre interactif si demandé
        if interactive:
            self._make_pie_interactive(fig, ax, wedges, data)
        
        # Adapter au thème
        self._apply_theme_to_figure(fig)
        
        # Créer le canvas GTK
        canvas = FigureCanvas(fig)
        canvas.set_size_request(size[0], size[1])
        
        return canvas
    
    def create_histogram(self, data: ChartData, title: str = "",
                        interactive: bool = True, size: Tuple[int, int] = (500, 400)) -> Gtk.Widget:
        """Crée un histogramme interactif"""
        
        # Créer la figure
        fig = Figure(figsize=(size[0]/100, size[1]/100), dpi=100)
        ax = fig.add_subplot(111)
        
        # Configurer les couleurs
        colors = data.colors or [self.default_colors[i % len(self.default_colors)] 
                               for i in range(len(data.values))]
        
        # Créer l'histogramme
        bars = ax.bar(range(len(data.values)), data.values, color=colors)
        
        # Configuration des axes
        ax.set_xticks(range(len(data.labels)))
        ax.set_xticklabels(data.labels, rotation=45, ha='right')
        ax.set_ylabel(_('Taille (octets)'))
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Formater les valeurs sur l'axe Y
        ax.yaxis.set_major_formatter(plt.FuncFormatter(self._format_bytes))
        
        # Ajouter des valeurs sur les barres
        for bar, value in zip(bars, data.values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   self._format_size(value),
                   ha='center', va='bottom', fontsize=8)
        
        # Rendre interactif si demandé
        if interactive:
            self._make_histogram_interactive(fig, ax, bars, data)
        
        # Adapter au thème
        self._apply_theme_to_figure(fig)
        
        # Ajuster la mise en page
        fig.tight_layout()
        
        # Créer le canvas GTK
        canvas = FigureCanvas(fig)
        canvas.set_size_request(size[0], size[1])
        
        return canvas
    
    def create_treemap(self, data: ChartData, title: str = "",
                      interactive: bool = True, size: Tuple[int, int] = (600, 400)) -> Gtk.Widget:
        """Crée un treemap interactif pour visualiser la hiérarchie des tailles"""
        
        # Créer la figure
        fig = Figure(figsize=(size[0]/100, size[1]/100), dpi=100)
        ax = fig.add_subplot(111)
        
        # Calculer les rectangles du treemap
        rectangles = self._calculate_treemap_rectangles(data.values, 0, 0, 1, 1)
        
        # Configurer les couleurs
        colors = data.colors or [self.default_colors[i % len(self.default_colors)] 
                               for i in range(len(data.values))]
        
        # Dessiner les rectangles
        patches_list = []
        for i, (rect, color) in enumerate(zip(rectangles, colors)):
            x, y, width, height = rect
            patch = patches.Rectangle((x, y), width, height, 
                                    facecolor=color, edgecolor='white', linewidth=1)
            ax.add_patch(patch)
            patches_list.append(patch)
            
            # Ajouter le label si le rectangle est assez grand
            if width > 0.1 and height > 0.1:
                ax.text(x + width/2, y + height/2, data.labels[i],
                       ha='center', va='center', fontsize=8, fontweight='bold',
                       color='white' if self._is_dark_color(color) else 'black')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.axis('off')  # Masquer les axes
        
        # Rendre interactif si demandé
        if interactive:
            self._make_treemap_interactive(fig, ax, patches_list, data)
        
        # Adapter au thème
        self._apply_theme_to_figure(fig)
        
        # Créer le canvas GTK
        canvas = FigureCanvas(fig)
        canvas.set_size_request(size[0], size[1])
        
        return canvas
    
    def _make_pie_interactive(self, fig, ax, wedges, data: ChartData):
        """Rend un camembert interactif"""
        def on_click(event):
            if event.inaxes != ax:
                return
            
            # Trouver le secteur cliqué
            for i, wedge in enumerate(wedges):
                if wedge.contains(event)[0]:
                    # Émettre un signal ou appeler un callback
                    if 'pie_click' in self.click_callbacks:
                        self.click_callbacks['pie_click'](i, data.labels[i], data.values[i])
                    break
        
        fig.canvas.mpl_connect('button_press_event', on_click)
        
        # Ajouter un effet de survol
        def on_hover(event):
            if event.inaxes != ax:
                return
            
            for wedge in wedges:
                wedge.set_alpha(0.7)  # Réinitialiser l'opacité
            
            for i, wedge in enumerate(wedges):
                if wedge.contains(event)[0]:
                    wedge.set_alpha(1.0)  # Mettre en évidence
                    fig.canvas.set_tooltip_text(f"{data.labels[i]}: {self._format_size(data.values[i])}")
                    break
            
            fig.canvas.draw_idle()
        
        fig.canvas.mpl_connect('motion_notify_event', on_hover)
    
    def _make_histogram_interactive(self, fig, ax, bars, data: ChartData):
        """Rend un histogramme interactif"""
        def on_click(event):
            if event.inaxes != ax:
                return
            
            # Trouver la barre cliquée
            for i, bar in enumerate(bars):
                if bar.contains(event)[0]:
                    if 'histogram_click' in self.click_callbacks:
                        self.click_callbacks['histogram_click'](i, data.labels[i], data.values[i])
                    break
        
        fig.canvas.mpl_connect('button_press_event', on_click)
        
        # Ajouter un effet de survol
        def on_hover(event):
            if event.inaxes != ax:
                return
            
            for bar in bars:
                bar.set_alpha(0.7)  # Réinitialiser l'opacité
            
            for i, bar in enumerate(bars):
                if bar.contains(event)[0]:
                    bar.set_alpha(1.0)  # Mettre en évidence
                    fig.canvas.set_tooltip_text(f"{data.labels[i]}: {self._format_size(data.values[i])}")
                    break
            
            fig.canvas.draw_idle()
        
        fig.canvas.mpl_connect('motion_notify_event', on_hover)
    
    def _make_treemap_interactive(self, fig, ax, patches_list, data: ChartData):
        """Rend un treemap interactif"""
        def on_click(event):
            if event.inaxes != ax:
                return
            
            # Trouver le rectangle cliqué
            for i, patch in enumerate(patches_list):
                if patch.contains(event)[0]:
                    if 'treemap_click' in self.click_callbacks:
                        self.click_callbacks['treemap_click'](i, data.labels[i], data.values[i])
                    break
        
        fig.canvas.mpl_connect('button_press_event', on_click)
    
    def _calculate_treemap_rectangles(self, values: List[float], x: float, y: float, 
                                    width: float, height: float) -> List[Tuple[float, float, float, float]]:
        """Calcule les rectangles pour un treemap en utilisant l'algorithme squarified"""
        if not values:
            return []
        
        total = sum(values)
        if total == 0:
            return []
        
        # Normaliser les valeurs
        normalized = [v / total for v in values]
        
        # Algorithme simple de treemap (peut être amélioré)
        rectangles = []
        current_x, current_y = x, y
        remaining_width, remaining_height = width, height
        
        for i, norm_value in enumerate(normalized):
            if i == len(normalized) - 1:
                # Dernier rectangle prend tout l'espace restant
                rect_width = remaining_width
                rect_height = remaining_height
            else:
                # Calculer la taille proportionnelle
                area = norm_value * width * height
                
                if remaining_width >= remaining_height:
                    # Diviser horizontalement
                    rect_width = area / remaining_height
                    rect_height = remaining_height
                else:
                    # Diviser verticalement
                    rect_width = remaining_width
                    rect_height = area / remaining_width
            
            rectangles.append((current_x, current_y, rect_width, rect_height))
            
            # Mettre à jour la position pour le prochain rectangle
            if remaining_width >= remaining_height:
                current_x += rect_width
                remaining_width -= rect_width
            else:
                current_y += rect_height
                remaining_height -= rect_height
        
        return rectangles
    
    def _apply_theme_to_figure(self, fig):
        """Applique le thème actuel à la figure"""
        if not self.theme_manager:
            return
        
        current_theme = self.theme_manager.get_current_theme()
        
        if current_theme == "dark":
            fig.patch.set_facecolor('#2d2d2d')
            for ax in fig.get_axes():
                ax.set_facecolor('#2d2d2d')
                ax.tick_params(colors='white')
                ax.xaxis.label.set_color('white')
                ax.yaxis.label.set_color('white')
                ax.title.set_color('white')
                for spine in ax.spines.values():
                    spine.set_color('white')
        else:
            fig.patch.set_facecolor('white')
            for ax in fig.get_axes():
                ax.set_facecolor('white')
    
    def _format_bytes(self, value, pos):
        """Formateur pour les valeurs en octets sur les axes"""
        return self._format_size(value)
    
    def _format_size(self, size: float) -> str:
        """Formate une taille en octets en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def _is_dark_color(self, color: str) -> bool:
        """Détermine si une couleur est sombre"""
        # Convertir la couleur hex en RGB
        if color.startswith('#'):
            color = color[1:]
        
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            # Calculer la luminance
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except (ValueError, IndexError):
            return False
    
    def set_click_callback(self, chart_type: str, callback: Callable):
        """Définit un callback pour les clics sur les graphiques"""
        self.click_callbacks[f"{chart_type}_click"] = callback
    
    def update_chart_data(self, canvas: FigureCanvas, new_data: ChartData, chart_type: str):
        """Met à jour les données d'un graphique existant"""
        # Cette méthode nécessiterait une refactorisation pour maintenir
        # les références aux éléments du graphique
        # Pour l'instant, on recommande de recréer le graphique
        pass