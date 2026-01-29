# -*- coding: utf-8 -*-

import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

class ReportGenerator:
    """Générateur de rapports en formats CSV et PDF"""

    @staticmethod
    def export_to_csv(data: list, filepath: str) -> bool:
        """
        Exporte les données d'analyse vers un fichier CSV.
        data: Liste de dictionnaires ou tuples [(Nom, Taille, Type), ...]
        """
        try:
            df = pd.DataFrame(data, columns=["Nom", "Taille", "Type"])
            df.to_csv(filepath, index=False, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Erreur export CSV: {e}")
            return False

    @staticmethod
    def export_to_pdf(data: list, filepath: str, title: str = "Rapport d'Analyse de Stockage") -> bool:
        """
        Exporte les données d'analyse vers un fichier PDF.
        """
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Titre
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 12))

            # Table des données
            table_data = [["Nom", "Taille", "Type"]]
            for item in data:
                table_data.append([str(item[0]), str(item[1]), str(item[2])])

            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(t)

            doc.build(elements)
            return True
        except Exception as e:
            print(f"Erreur export PDF: {e}")
            return False
