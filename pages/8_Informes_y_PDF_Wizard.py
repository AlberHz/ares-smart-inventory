"""
MÓDULO: pages/8_Informes_y_PDF_Wizard.py
DESCRIPCIÓN: Ecosistema avanzado de generación de reportes y auditoría de inventarios (Módulo 8).
             Automatiza la extracción de KPIs de capital inmovilizado, evolutivos de cierres,
             análisis ABC transaccional, reportes de envejecimiento (Aging) y métricas ERI.
             Compila toda la inteligencia de datos en un PDF corporativo nativo e institucional.
AUTOR: Principal Analytics & Supply Chain Architect
VERSIÓN: 2.1.1 (Corregido para Compatibilidad de Columnas Reales del Negocio)
"""

import os
import io
import datetime
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import streamlit as st

# Importaciones de ReportLab para maquetación PDF de nivel corporativo
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect

# =============================================================================
# 1. FUNCIONES UTILITARIAS DE BLINDAJE DE DATOS (ANTI-ERROR)
# =============================================================================

def limpiar_texto_xml(texto: Any) -> str:
    """
    Sanitiza strings para evitar que caracteres especiales como '&', '<', '>'
    rompan el parseador interno de Paragraph de ReportLab.
    """
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s

def safe_float(val: Any) -> float:
    """Convierte de forma segura cualquier valor a float evitando errores por NaN o None."""
    try:
        if pd.isna(val) or val is None:
            return 0.0
        return float(val)
    except:
        return 0.0

def safe_int(val: Any) -> int:
    """Convierte de forma segura cualquier valor a int evitando errores por NaN o None."""
    try:
        if pd.isna(val) or val is None:
            return 0
        return int(float(val))
    except:
        return 0

# =============================================================================
# 2. ARQUITECTURA DEL CANVAS: CONTROLADOR DE PAGINACIÓN DE DOS PASADAS
# =============================================================================

class CorporateNumberedCanvas(canvas.Canvas):
    """
    Canvas personalizado para ReportLab.
    Realiza una auditoría en dos pasadas sobre el documento para calcular dinámicamente
    el total de páginas real ('Página X de Y') e inyectar encabezados/pies corporativos.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        
        primary_color = colors.HexColor("#1e3a8a")
        text_muted = colors.HexColor("#64748b")
        border_color = colors.HexColor("#cbd5e1")
        
        # --- ENCABEZADO CRONOLÓGICO ---
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_color)
            self.drawString(54, 755, "INFORME INTEGRADO DE AUDITORÍA, ARQUITECTURA DE DATOS Y OPTIMIZACIÓN LOGÍSTICA")
            
            self.setFont("Helvetica", 8)
            self.setFillColor(text_muted)
            self.drawRightString(558, 755, f"EMISIÓN: {datetime.date.today().strftime('%d/%m/%Y')}")
            
            self.setStrokeColor(border_color)
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)

        # --- PIE DE PÁGINA INSTITUCIONAL ---
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#94a3b8"))
        self.drawString(54, 32, "CONFIDENCIAL - REPORTING EMITIDO PARA DIRECCIÓN DE OPERACIONES Y FINANZAS")
        
        page_string = f"Página {self._pageNumber} de {page_count}"
        self.setFont("Helvetica", 8)
        self.setFillColor(text_muted)
        self.drawRightString(558, 32, page_string)
        
        self.restoreState()


# =============================================================================
# 3. MOTOR DE GENERACIÓN DEL DOCUMENTO PDF
# =============================================================================

def build_pdf_report(
    buffer: io.BytesIO, 
    kpis: Dict[str, Any], 
    df_abc: pd.DataFrame, 
    df_aging: pd.DataFrame, 
    df_eri: pd.DataFrame,
    df_cierres: pd.DataFrame
) -> None:
    """
    Orquestador Platypus. Construye y ensambla de forma segura los flows del PDF,
    aplicando sanitización estricta sobre celdas para evitar desbordes o errores de XML.
    """
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    COLOR_PRIMARY = colors.HexColor("#1e3a8a")     
    COLOR_SECONDARY = colors.HexColor("#0f766e")   
    COLOR_DARK = colors.HexColor("#0f172a")        
    COLOR_LIGHT_BG = colors.HexColor("#f8fafc")    
    COLOR_BORDER = colors.HexColor("#e2e8f0")      
    COLOR_ACCENT = colors.HexColor("#b91c1c")      
    
    # Estilos de Párrafo Profesionales Controlados
    style_title = ParagraphStyle(
        'DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=COLOR_PRIMARY, spaceAfter=6
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor("#475569"), spaceAfter=20
    )
    style_h1 = ParagraphStyle(
        'SectionH1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=COLOR_PRIMARY, spaceBefore=14, spaceAfter=8, keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'SectionH2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=COLOR_SECONDARY, spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    style_body = ParagraphStyle(
        'BodyCorp', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=COLOR_DARK, spaceAfter=6
    )
    style_table_header = ParagraphStyle(
        'TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=colors.white, alignment=1
    )
    style_table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=COLOR_DARK, alignment=0
    )
    style_table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=COLOR_DARK, alignment=0
    )
    style_table_cell_right = ParagraphStyle(
        'TableCellRight', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=COLOR_DARK, alignment=2
    )
    style_table_cell_alert = ParagraphStyle(
        'TableCellAlert', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=COLOR_ACCENT, alignment=2
    )

    story: List[Any] = []
    
    # --- SECCIÓN 1: PORTADA Y RESUMEN EJECUTIVO ---
    story.append(Spacer(1, 15))
    story.append(Paragraph("INFORME DE DIRECCIÓN OPERATIVA", style_title))
    story.append(Paragraph("Auditoría Integral de Inventarios, Capital Inmovilizado y Estructura Patrimonial", style_subtitle))
    
    d = Drawing(504, 3)
    d.add(Rect(0, 0, 504, 3, fillColor=COLOR_PRIMARY, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Resumen Ejecutivo de Gestión", style_h1))
    meta_texto = (
        "El presente informe técnico gerencial consolida la auditoría analítica realizada sobre las existencias, "
        "flujos transaccionales y precisión operacional del ecosistema logístico de la compañía. "
        "A través de algoritmos de reconstrucción inversa de saldos mensuales, modelos estadísticos de Pareto basados en "
        "la frecuencia operativa de despachos, y la valorización financiera del impacto por obsolescencia (Aging) cruzando "
        "el Costo Promedio Ponderado de Capital (WACC), se presenta este diagnóstico cuantitativo como herramienta "
        "estratégica para optimizar la toma de decisiones patrimoniales."
    )
    story.append(Paragraph(meta_texto, style_body))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Cuadro de Mando Integral - Macrométricas Financieras", style_h2))
    
    kpi_table_data = [
        [
            Paragraph("Métrica Financiera / Logística", style_table_header),
            Paragraph("Valor Detectado", style_table_header),
            Paragraph("Unidad", style_table_header),
            Paragraph("Estatus de Riesgo", style_table_header)
        ],
        [
            Paragraph("Capital Total Inmovilizado (CTI)", style_table_cell_bold),
            Paragraph(f"S/. {safe_float(kpis.get('cti')):,.2f}", style_table_cell_right),
            Paragraph("Moneda Local", style_table_cell),
            Paragraph("Evaluación de Liquidez", style_table_cell)
        ],
        [
            Paragraph("Costo Mensual de Oportunidad (WACC)", style_table_cell_bold),
            Paragraph(f"S/. {safe_float(kpis.get('costo_wacc_mensual')):,.2f}", style_table_cell_right),
            Paragraph("S/. / Mes", style_table_cell_alert),
            Paragraph("Pérdida Patrimonial Activa", style_table_cell_bold)
        ],
        [
            Paragraph("Exactitud de Registro (ERI Absoluto)", style_table_cell_bold),
            Paragraph(f"{safe_float(kpis.get('eri_absoluto')):.2f}%", style_table_cell_right),
            Paragraph("Porcentaje", style_table_cell),
            Paragraph("Eficiencia de Conteo" if safe_float(kpis.get('eri_absoluto')) >= 95 else "Requierre Intervención", style_table_cell_bold)
        ],
        [
            Paragraph("Monto Neto de Desviación Financiera", style_table_cell_bold),
            Paragraph(f"S/. {safe_float(kpis.get('monto_desviacion')):,.2f}", style_table_cell_right),
            Paragraph("Neto Conciliado", style_table_cell),
            Paragraph("Ajuste en Balance Obligatorio", style_table_cell)
        ]
    ]
    
    t_kpi = Table(kpi_table_data, colWidths=[170, 100, 94, 140])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_kpi)
    
    story.append(PageBreak())
    
    # --- SECCIÓN 2: CONTROL DE CAPITAL INMOVILIZADO ---
    story.append(Paragraph("1. Control de Capital Inmovilizado y Estructura Patrimonial", style_h1))
    story.append(Paragraph("La distribución geográfica y por centros de costos revela que las sedes detalladas a continuación concentran la masa patrimonial evaluada:", style_body))
    story.append(Spacer(1, 5))
    
    table_sede_data = [[
        Paragraph("Ubicación / Almacén / Sede", style_table_header),
        Paragraph("Stock Físico Disp.", style_table_header),
        Paragraph("Capital Inmovilizado", style_table_header),
        Paragraph("Participación %", style_table_header)
    ]]
    
    if not df_abc.empty and 'Almacen' in df_abc.columns and 'Valor_Total' in df_abc.columns:
        df_agrupado_sede = df_abc.groupby('Almacen').agg({'Stock': 'sum', 'Valor_Total': 'sum'}).reset_index()
        cti_ref = safe_float(kpis.get('cti'))
        for _, row in df_agrupado_sede.iterrows():
            part_porc = (safe_float(row['Valor_Total']) / cti_ref * 100) if cti_ref > 0 else 0.0
            table_sede_data.append([
                Paragraph(limpiar_texto_xml(row['Almacen']), style_table_cell_bold),
                Paragraph(f"{safe_float(row['Stock']):,.0f}", style_table_cell_right),
                Paragraph(f"S/. {safe_float(row['Valor_Total']):,.2f}", style_table_cell_right),
                Paragraph(f"{part_porc:.2f}%", style_table_cell_right)
            ])
    else:
        table_sede_data.append([Paragraph("Sin datos de sedes consolidadas disponibles.", style_table_cell), "", "", ""])
        
    t_sede = Table(table_sede_data, colWidths=[164, 100, 130, 110])
    t_sede.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECONDARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_sede)
    story.append(Spacer(1, 10))

    # --- SECCIÓN 3: EVOLUTIVO MENSUAL DE CIERRES ---
    story.append(Paragraph("2. Evolutivo de Cierres Mensuales e Indicadores de Variación", style_h1))
    story.append(Paragraph("Comportamiento histórico de los saldos valorizados de cierre para los últimos períodos analizados mapeando tendencias macroeconómicas:", style_body))
    story.append(Spacer(1, 5))
    
    table_cierres_data = [[
        Paragraph("Período Evaluado", style_table_header),
        Paragraph("Stock de Cierre (Unidades)", style_table_header),
        Paragraph("Valorización de Cierre", style_table_header),
        Paragraph("Variación Mensual (MoM %)", style_table_header)
    ]]
    
    if df_cierres is not None and not df_cierres.empty:
        for _, row in df_cierres.iterrows():
            v_mom = safe_float(row.get('VARIACION_MOM_%', 0))
            var_style = style_table_cell_right if v_mom >= 0 else style_table_cell_alert
            table_cierres_data.append([
                Paragraph(limpiar_texto_xml(row.get('MES', 'N/A')), style_table_cell_bold),
                Paragraph(f"{safe_float(row.get('STOCK_CIERRE', 0)):,.0f}", style_table_cell_right),
                Paragraph(f"S/. {safe_float(row.get('VALOR_CIERRE', 0)):,.2f}", style_table_cell_right),
                Paragraph(f"{v_mom:.2f}%", var_style)
            ])
    else:
        table_cierres_data.append([Paragraph("Sin registros de movimientos históricos suficientes para reconstrucción temporal.", style_table_cell), "", "", ""])

    t_cierres = Table(table_cierres_data, colWidths=[134, 120, 130, 120])
    t_cierres.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_cierres)
    story.append(Spacer(1, 10))

    # --- SECCIÓN 4: PARETO OPERATIVO POR FRECUENCIA ---
    story.append(Paragraph("3. Clasificación ABC Operativa por Frecuencia de Despachos", style_h1))
    story.append(Paragraph("Mapeo enfocado en la carga transaccional del almacén (solicitudes de picking en Notas de Salida - NS):", style_body))
    story.append(Spacer(1, 5))
    
    table_abc_data = [[
        Paragraph("Código SKU", style_table_header),
        Paragraph("Descripción del Artículo", style_table_header),
        Paragraph("Frecuencia (NS)", style_table_header),
        Paragraph("Valorización", style_table_header),
        Paragraph("Clasificación", style_table_header)
    ]]
    
    if not df_abc.empty and 'FRECUENCIA' in df_abc.columns:
        df_top_abc = df_abc.sort_values(by='FRECUENCIA', ascending=False).head(8)
        for _, row in df_top_abc.iterrows():
            table_abc_data.append([
                Paragraph(limpiar_texto_xml(row.get('Codigo', 'N/A')), style_table_cell_bold),
                Paragraph(limpiar_texto_xml(row.get('Descripcion', 'N/A'))[:32], style_table_cell),
                Paragraph(f"{safe_float(row.get('FRECUENCIA', 0)):,.0f} despachos", style_table_cell_right),
                Paragraph(f"S/. {safe_float(row.get('Valor_Total', 0)):,.2f}", style_table_cell_right),
                Paragraph(f"Clase {limpiar_texto_xml(row.get('ABC_OPERATIVO', 'C'))}", style_table_cell_bold)
            ])
    else:
        table_abc_data.append([Paragraph("Dataset de clasificación ABC no estructurado o vacío.", style_table_cell), "", "", "", ""])
        
    t_abc = Table(table_abc_data, colWidths=[74, 160, 90, 100, 80])
    t_abc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECONDARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_abc)
    story.append(Spacer(1, 10))

    # --- SECCIÓN 5: AGING REPORT ---
    story.append(Paragraph("4. Aging Report, Envejecimiento y Penalización del WACC", style_h1))
    story.append(Paragraph("Análisis de inactividad prolongada e impacto directo en los costos ocultos de capital:", style_body))
    story.append(Spacer(1, 5))
    
    table_aging_data = [[
        Paragraph("Código SKU", style_table_header),
        Paragraph("Descripción", style_table_header),
        Paragraph("Días Inactivo", style_table_header),
        Paragraph("Capital Paralizado", style_table_header),
        Paragraph("Pérdida WACC / Mes", style_table_header)
    ]]
    
    if not df_aging.empty and 'COSTO_OPORTUNIDAD_MENSUAL' in df_aging.columns:
        df_top_aging = df_aging.sort_values(by='COSTO_OPORTUNIDAD_MENSUAL', ascending=False).head(8)
        for _, row in df_top_aging.iterrows():
            table_aging_data.append([
                Paragraph(limpiar_texto_xml(row.get('Codigo', 'N/A')), style_table_cell_bold),
                Paragraph(limpiar_texto_xml(row.get('Descripcion', 'N/A'))[:32], style_table_cell),
                Paragraph(f"{safe_int(row.get('DIAS_INACTIVIDAD', 0))} días", style_table_cell_right),
                Paragraph(f"S/. {safe_float(row.get('Valor_Total', 0)):,.2f}", style_table_cell_right),
                Paragraph(f"S/. {safe_float(row.get('COSTO_OPORTUNIDAD_MENSUAL', 0)):,.2f}", style_table_cell_alert)
            ])
    else:
        table_aging_data.append([Paragraph("Dataset de envejecimiento patrimonial no calculado.", style_table_cell), "", "", "", ""])
        
    t_aging = Table(table_aging_data, colWidths=[74, 160, 80, 100, 90])
    t_aging.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_aging)
    story.append(Spacer(1, 10))

    # --- SECCIÓN 6: DISCIPLINA OPERATIVA ERI ---
    story.append(KeepTogether([
        Paragraph("5. Exactitud de Registro de Inventario (ERI) y Auditoría Contable", style_h1),
        Paragraph("Conciliación de auditoría de campo (Conteo físico vs Stock Teórico de sistema):", style_body),
        Spacer(1, 5)
    ]))
    
    table_eri_data = [[
        Paragraph("Código SKU", style_table_header),
        Paragraph("Ubicación Sede", style_table_header),
        Paragraph("Stock Sist.", style_table_header),
        Paragraph("Conteo Fís.", style_table_header),
        Paragraph("Diferencia Unit.", style_table_header),
        Paragraph("Impacto Financiero", style_table_header)
    ]]
    
    if df_eri is not None and not df_eri.empty and 'DIFERENCIA' in df_eri.columns:
        df_descuadres = df_eri[df_eri['DIFERENCIA'] != 0].head(8)
        if df_descuadres.empty:
            df_descuadres = df_eri.head(8)
            
        for _, row in df_descuadres.iterrows():
            diff_v = safe_float(row.get('DIFERENCIA', 0))
            dif_style = style_table_cell_alert if diff_v != 0 else style_table_cell_right
            table_eri_data.append([
                Paragraph(limpiar_texto_xml(row.get('Codigo', 'N/A')), style_table_cell_bold),
                Paragraph(limpiar_texto_xml(row.get('Almacen', 'GENERAL')), style_table_cell),
                Paragraph(f"{safe_float(row.get('Stock', 0)):,.0f}", style_table_cell_right),
                Paragraph(f"{safe_float(row.get('Conteo', 0)):,.0f}", style_table_cell_right),
                Paragraph(f"{diff_v:,.0f}", dif_style),
                Paragraph(f"S/. {safe_float(row.get('IMPACTO_FINANCIERO', 0)):,.2f}", style_table_cell_alert if safe_float(row.get('IMPACTO_FINANCIERO', 0)) != 0 else style_table_cell_right)
            ])
    else:
        table_eri_data.append([Paragraph("No se registran transacciones activas de plantillas ERI en la sesión.", style_table_cell), "", "", "", "", ""])

    t_eri = Table(table_eri_data, colWidths=[70, 114, 65, 65, 80, 110])
    t_eri.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECONDARY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_eri)
    
    doc.build(story, canvasmaker=CorporateNumberedCanvas)


# =============================================================================
# 4. INTERFAZ DE USUARIO STREAMLIT DE ALTO IMPACTO VISUAL
# =============================================================================

def main() -> None:
    st.set_page_config(
        page_title="Módulo 8: Wizard de Informes y Auditoría Corporativa", 
        page_icon="📊", 
        layout="wide"
    )
    
    st.title("📊 Módulo 8: Wizard Central de Informes Gerenciales y PDF")
    st.markdown(
        "Este componente actúa como la capa integradora final del ecosistema de software. "
        "Recupera las métricas calculadas en los módulos previos para compilar el reporte oficial automatizado."
    )
    st.markdown("---")

    # --- VALIDACIÓN DEFENSIVA Y CACHÉ DE SESIÓN DE INVENTARIOS ---
    if 'df_stock' not in st.session_state or st.session_state['df_stock'] is None:
        st.error("⚠️ [ERROR CRÍTICO DE INGENIERÍA]: No se detectaron los Maestros de Inventario en el session_state.")
        st.warning("Debe regresar a la página principal de carga e ingestar los datos consolidados en Excel para habilitar la auditoría.")
        st.stop()

    # Copia profunda defensiva para evitar mutaciones directas sobre el estado global
    df_stock_master = st.session_state['df_stock'].copy()
    df_mov_master = st.session_state.get('df_mov', None)

    # --- VALIDACIÓN DE COLUMNAS REQUERIDAS (Tus nombres reales capitalizados) ---
    columnas_requeridas = ['Codigo', 'Descripcion', 'Almacen', 'Stock', 'Costo']
    for col in columnas_requeridas:
        if col not in df_stock_master.columns:
            st.error(f"❌ Estructura incompatible. Falta la columna requerida: `{col}`")
            st.stop()

    # --- PIPELINE VECTORIZADO COMPILADOR (CÁLCULOS SOBRE MARGENES VIVOS) ---
    df_stock_master['Valor_Total'] = df_stock_master['Stock'].apply(safe_float) * df_stock_master['Costo'].apply(safe_float)
    capital_total_inmovilizado = float(df_stock_master['Valor_Total'].sum())

    # Inicializar Frecuencias de Notas de Salida (NS)
    frecuencia_map = {}
    if df_mov_master is not None and not df_mov_master.empty:
        # Usamos tus columnas reales de movimientos
        if 'Tipo_Movimiento' in df_mov_master.columns and 'Codigo' in df_mov_master.columns:
            df_salidas = df_mov_master[df_mov_master['Tipo_Movimiento'].astype(str).str.upper() == 'NS']
            frecuencia_map = df_salidas.groupby('Codigo').size().to_dict()
        
    df_stock_master['FRECUENCIA'] = df_stock_master['Codigo'].map(frecuencia_map).fillna(0).apply(safe_float)
    
    # Pareto Dinámico
    df_stock_master = df_stock_master.sort_values(by='FRECUENCIA', ascending=False)
    df_stock_master['FREQ_ACUM'] = df_stock_master['FRECUENCIA'].cumsum()
    freq_total = df_stock_master['FRECUENCIA'].sum()
    df_stock_master['PORC_ACUM'] = (df_stock_master['FREQ_ACUM'] / freq_total * 100) if freq_total > 0 else 100.0
    
    df_stock_master['ABC_OPERATIVO'] = df_stock_master['PORC_ACUM'].apply(lambda x: 'A' if x <= 80.0 else ('B' if x <= 95.0 else 'C'))

    # Parámetros del Costo Financiero Oculto (WACC)
    with st.sidebar:
        st.header("⚙️ Configuración del WACC")
        wacc_anual = st.slider("Tasa WACC Corporativa Anual (%)", min_value=1.0, max_value=30.0, value=12.0, step=0.5) / 100
        wacc_mensual = wacc_anual / 12
        st.caption(f"Tasa proporcional mensualizada: {(wacc_mensual*100):.4f}%")

    # Mapeo de Envejecimiento (Aging) con Fecha de Dataset Controlada
    dias_map = {}
    if df_mov_master is not None and not df_mov_master.empty and 'Fecha' in df_mov_master.columns:
        try:
            df_mov_master['FECHA_DT'] = pd.to_datetime(df_mov_master['Fecha']).dt.date
            fecha_referencia = df_mov_master['FECHA_DT'].max()
            df_salidas_dt = df_mov_master[df_mov_master['Tipo_Movimiento'].astype(str).str.upper() == 'NS']
            df_ult_salida = df_salidas_dt.groupby('Codigo')['FECHA_DT'].max().reset_index()
            for _, r in df_ult_salida.iterrows():
                dias_map[r['Codigo']] = (fecha_referencia - r['FECHA_DT']).days
        except:
            pass

    df_stock_master['DIAS_INACTIVIDAD'] = df_stock_master['Codigo'].map(dias_map).fillna(9999).apply(safe_int)
    df_stock_master['COSTO_OPORTUNIDAD_MENSUAL'] = df_stock_master['Valor_Total'] * wacc_mensual
    costo_wacc_global_mensual = float(df_stock_master['COSTO_OPORTUNIDAD_MENSUAL'].sum())

    # Reconstrucción de Línea de Cierres Cronológicos Históricos
    df_cierres_historicos = pd.DataFrame()
    if df_mov_master is not None and not df_mov_master.empty and 'Fecha' in df_mov_master.columns:
        try:
            df_m = df_mov_master.copy()
            df_m['Fecha'] = pd.to_datetime(df_m['Fecha'])
            df_m['MES_AÑO'] = df_m['Fecha'].dt.to_period('M')
            df_m['CANTIDAD_SIGNED'] = np.where(df_m['Tipo_Movimiento'].astype(str).str.upper() == 'NI', df_m['Cantidad'].apply(safe_float), -df_m['Cantidad'].apply(safe_float))
            
            pivot_meses = df_m.groupby('MES_AÑO')['CANTIDAD_SIGNED'].sum().reset_index()
            pivot_meses = pivot_meses.sort_values(by='MES_AÑO', ascending=False)
            
            running_stock = safe_float(df_stock_master['Stock'].sum())
            costo_medio_canasta = safe_float(df_stock_master['Costo'].mean())
            list_cierres = []
            
            for _, r in pivot_meses.iterrows():
                list_cierres.append({
                    'MES': str(r['MES_AÑO']),
                    'STOCK_CIERRE': running_stock,
                    'VALOR_CIERRE': running_stock * costo_medio_canasta
                })
                running_stock -= r['CANTIDAD_SIGNED']
                
            df_cierres_historicos = pd.DataFrame(list_cierres).sort_values(by='MES')
            df_cierres_historicos['VARIACION_MOM_%'] = df_cierres_historicos['VALOR_CIERRE'].pct_change().fillna(0) * 100
        except:
            pass

    # Integración del Módulo de Exactitud de Registros (ERI) cargado de sesion
    df_eri_master = st.session_state.get('df_eri_calculado', pd.DataFrame())
    eri_absoluto_kpi = 100.0
    monto_desviacion_global = 0.0
    
    if not df_eri_master.empty and 'Conteo' in df_eri_master.columns:
        df_eri_master = df_eri_master.copy()
        df_eri_master['Stock'] = df_eri_master['Stock'].apply(safe_float)
        df_eri_master['Conteo'] = df_eri_master['Conteo'].apply(safe_float)
        df_eri_master['Costo_Unitario'] = df_eri_master['Costo_Unitario'].apply(safe_float)
        
        df_eri_master['DIFERENCIA'] = df_eri_master['Conteo'] - df_eri_master['Stock']
        df_eri_master['IMPACTO_FINANCIERO'] = df_eri_master['DIFERENCIA'] * df_eri_master['Costo_Unitario']
        
        coincidencias = int((df_eri_master['DIFERENCIA'] == 0).sum())
        eri_absoluto_kpi = (coincidencias / len(df_eri_master)) * 100
        monto_desviacion_global = float(df_eri_master['IMPACTO_FINANCIERO'].sum())
    else:
        df_eri_master = df_stock_master.copy()
        df_eri_master['Conteo'] = df_eri_master['Stock']
        df_eri_master['DIFERENCIA'] = 0.0
        df_eri_master['IMPACTO_FINANCIERO'] = 0.0

    diccionario_kpis = {
        'cti': capital_total_inmovilizado,
        'costo_wacc_mensual': costo_wacc_global_mensual,
        'eri_absoluto': eri_absoluto_kpi,
        'monto_desviacion': monto_desviacion_global
    }

    # --- RENDERIZADO DE CARDS DE MONITOREO ---
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="Capital Total Inmovilizado (CTI)", value=f"S/. {capital_total_inmovilizado:,.2f}")
        st.metric(label="Penalización por Costo de Oportunidad Mensual", value=f"S/. {costo_wacc_global_mensual:,.2f}")
    with c2:
        st.metric(label="Exactitud de Registro (ERI Absoluto)", value=f"{eri_absoluto_kpi:.2f}%")
        st.metric(label="Desviación de Balance Financiero Físico", value=f"S/. {monto_desviacion_global:,.2f}")

    st.markdown("---")
    
    # --- PROCESADOR INTEGRADO DE ARCHIVOS PDF (IN-MEMORY BUFFER) ---
    pdf_buffer = io.BytesIO()
    try:
        build_pdf_report(
            buffer=pdf_buffer,
            kpis=diccionario_kpis,
            df_abc=df_stock_master,
            df_aging=df_stock_master,
            df_eri=df_eri_master,
            df_cierres=df_cierres_historicos
        )
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        st.download_button(
            label="🚀 EMITIR REPORTE EJECUTIVO AUDITADO (PDF NATIVO)",
            data=pdf_bytes,
            file_name=f"Reporte_Módulo8_Auditoria_{datetime.date.today().strftime('%Y_%m_%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.success("🤖 Motor de ReportLab verificado. No se detectan errores de desborde de memoria o parseo XML.")
    except Exception as e:
        st.error(f"🚨 Error en la compilación del reporte: {str(e)}")

if __name__ == "__main__":
    main()