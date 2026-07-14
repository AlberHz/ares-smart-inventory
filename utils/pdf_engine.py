"""
MÓDULO: utils/pdf_engine.py
DESCRIPCIÓN: Fábrica centralizada de generación de reportes PDF corporativos.
             Implementa un motor común de diseño (Maqueta Maestra) para estandarizar
             fuentes, colores, márgenes y sistema de numeración "Página X de Y".
             Reduce la redundancia de código a menos de 400 líneas totales para los 7 informes.
AUTOR: Principal Analytics & Supply Chain Architect
VERSIÓN: 2.3.0 (Diseño Unificado + Reporte Ejecutivo Gerencial)
"""

import io
import datetime
import pandas as pd
from typing import List, Any, Dict
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect

# =============================================================================
# 1. FUNCIONES UTILITARIAS DE BLINDAJE DE DATOS (ANTI-ERROR)
# =============================================================================

def limpiar_texto_xml(texto: Any) -> str:
    """Sanitiza strings para evitar que caracteres especiales rompan ReportLab."""
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def safe_float(val: Any) -> float:
    try:
        if pd.isna(val) or val is None:
            return 0.0
        return float(val)
    except:
        return 0.0

# =============================================================================
# 2. SISTEMA DE NUMERACIÓN DINÁMICO EN DOS PASADAS
# =============================================================================

class CorporateNumberedCanvas(canvas.Canvas):
    """Calcula dinámicamente 'Página X de Y' y añade decoraciones al canvas."""
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
        
        # --- ENCABEZADO (A partir de la página 2) ---
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_color)
            self.drawString(54, 755, "SISTEMA INTEGRADO DE GESTIÓN Y AUDITORÍA DE INVENTARIOS")
            
            self.setFont("Helvetica", 8)
            self.setFillColor(text_muted)
            self.drawRightString(558, 755, f"EMISIÓN: {datetime.date.today().strftime('%d/%m/%Y')}")
            
            self.setStrokeColor(border_color)
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)

        # --- PIE DE PÁGINA (Todas las páginas) ---
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#94a3b8"))
        self.drawString(54, 32, "CONFIDENCIAL - GESTIÓN INTERNA DE OPERACIONES Y LOGÍSTICA")
        
        page_string = f"Página {self._pageNumber} de {page_count}"
        self.setFont("Helvetica", 8)
        self.setFillColor(text_muted)
        self.drawRightString(558, 32, page_string)
        
        self.restoreState()


# =============================================================================
# 3. LA MAQUETA MAESTRA DE CONSTRUCCIÓN PDF (REUTILIZABLE)
# =============================================================================

def _compilar_pdf_base(titulo_reporte: str, subtitulo: str, elementos_especificos: List[Any]) -> bytes:
    """
    Ensambla y empaqueta la visualización de cualquier PDF.
    Evita redundancias e impide que el código de la app crezca de forma desmedida.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    COLOR_PRIMARY = colors.HexColor("#1e3a8a")
    
    style_title = ParagraphStyle(
        'DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=COLOR_PRIMARY, spaceAfter=4
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#475569"), spaceAfter=15
    )
    
    story: List[Any] = []
    
    # Encabezado institucional base
    story.append(Paragraph(titulo_reporte.upper(), style_title))
    story.append(Paragraph(f"Generado el: {datetime.date.today().strftime('%d/%m/%Y')} | {subtitulo}", style_subtitle))
    
    # Línea decorativa principal
    d = Drawing(504, 3)
    d.add(Rect(0, 0, 504, 3, fillColor=COLOR_PRIMARY, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 15))
    
    # Incorporación de elementos específicos del reporte
    story.extend(elementos_especificos)
    
    doc.build(story, canvasmaker=CorporateNumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =============================================================================
# 4. LOS 7 REPORTES ESPECÍFICOS DE LOS MÓDULOS
# =============================================================================

def _crear_tabla_estandar(df: pd.DataFrame, headers: List[str], col_widths: List[float], key_cols: List[str], is_numeric: List[bool], align_right: List[bool]) -> Table:
    """Función helper para generar tablas con diseño uniforme en ReportLab."""
    styles = getSampleStyleSheet()
    style_th = ParagraphStyle('TH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=1)
    style_td = ParagraphStyle('TD', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10)
    style_td_r = ParagraphStyle('TDR', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, alignment=2)
    
    table_data = [[Paragraph(limpiar_texto_xml(h), style_th) for h in headers]]
    
    for _, row in df.head(35).iterrows(): # Límite saludable para control de páginas
        row_cells = []
        for i, col in enumerate(key_cols):
            val = row.get(col, '')
            txt = ""
            if is_numeric[i]:
                f_val = safe_float(val)
                txt = f"{f_val:,.2f}" if "VALOR" in col.upper() or "COSTO" in col.upper() or "IMPACTO" in col.upper() else f"{f_val:,.0f}"
            else:
                txt = limpiar_texto_xml(str(val))
                
            style_celda = style_td_r if align_right[i] else style_td
            row_cells.append(Paragraph(txt, style_celda))
        table_data.append(row_cells)
        
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


# --- INFORME 1: VALORIZADO (VERSIÓN EJECUTIVA GERENCIAL) ---
def generar_pdf_valorizado(df: pd.DataFrame) -> bytes:
    """
    MÓDULO 1: Reporte Ejecutivo de Estructura Patrimonial y Capital Inmovilizado.
    Diseñado específicamente para toma de decisiones gerenciales.
    """
    styles = getSampleStyleSheet()
    
    # Estilos de texto adaptados
    style_body = ParagraphStyle('B_Val', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=8)
    style_h2 = ParagraphStyle('H2_Val', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#1e3a8a"), spaceBefore=10, spaceAfter=6)
    style_table_header = ParagraphStyle('TH_Val', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=1)
    style_table_cell = ParagraphStyle('TC_Val', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11)
    style_table_cell_r = ParagraphStyle('TCR_Val', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, alignment=2)

    # --- 1. PROCESAMIENTO DE DATOS CLAVE PARA GERENCIA ---
    total_capital = df['Valor_Total'].sum()
    total_unidades = df['Stock'].sum()
    
    # A. Consolidado por Almacén
    df_alm = df.groupby('Almacen').agg(
        Items=('Codigo', 'count'),
        Unidades=('Stock', 'sum'),
        Inversion=('Valor_Total', 'sum')
    ).reset_index().sort_values(by='Inversion', ascending=False)
    df_alm['Participacion'] = (df_alm['Inversion'] / total_capital) * 100 if total_capital > 0 else 0

    # B. Pareto de Familias
    df_fam = df.groupby('Familia').agg(
        Inversion=('Valor_Total', 'sum')
    ).reset_index().sort_values(by='Inversion', ascending=False)
    df_fam['Participacion'] = (df_fam['Inversion'] / total_capital) * 100 if total_capital > 0 else 0
    top_familias = df_fam.head(5)
    
    # --- 2. ENCHUFAR ELEMENTOS AL PDF ---
    elementos = []
    
    # Introducción Ejecutiva
    elementos.append(Paragraph("<b>1. RESUMEN EJECUTIVO</b>", style_h2))
    resumen_texto = (
        f"Al cierre del período analizado, el patrimonio total inmovilizado en inventarios asciende a "
        f"<b>S/. {total_capital:,.2f}</b>, distribuidos en un volumen físico de <b>{total_unidades:,.0f} unidades</b>. "
        f"Este informe de control de activos tiene como objetivo identificar los nodos de concentración de capital "
        f"por sede y categoría para optimizar el costo de oportunidad del dinero y el espacio en almacenes."
    )
    elementos.append(Paragraph(resumen_texto, style_body))
    elementos.append(Spacer(1, 10))
    
    # --- TABLA A: DISTRIBUCIÓN POR SEDE / ALMACÉN ---
    elementos.append(Paragraph("<b>2. CONCENTRACIÓN DE CAPITAL POR SEDE DE ALMACENAMIENTO</b>", style_h2))
    elementos.append(Paragraph("A continuación se muestra el análisis de custody de valores y la participación financiera que representa cada almacén sobre el total del balance:", style_body))
    
    # Cabeceras de tabla de almacén
    tabla_alm_data = [[
        Paragraph("Almacén Sede", style_table_header),
        Paragraph("Variedad (SKUs)", style_table_header),
        Paragraph("Volumen (UM)", style_table_header),
        Paragraph("Valorización (S/.)", style_table_header),
        Paragraph("Participación %", style_table_header)
    ]]
    
    # Llenado de filas de almacén
    for _, row in df_alm.iterrows():
        tabla_alm_data.append([
            Paragraph(limpiar_texto_xml(row['Almacen']), style_table_cell),
            Paragraph(f"{row['Items']:,.0f}", style_table_cell_r),
            Paragraph(f"{row['Unidades']:,.0f}", style_table_cell_r),
            Paragraph(f"S/. {row['Inversion']:,.2f}", style_table_cell_r),
            Paragraph(f"{row['Participacion']:.2f}%", style_table_cell_r)
        ])
    
    t_alm = Table(tabla_alm_data, colWidths=[144, 90, 90, 100, 80])
    t_alm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(t_alm)
    elementos.append(Spacer(1, 15))
    
    # --- TABLA B: TOP 5 FAMILIAS QUE CONCENTRAN CAPITAL ---
    elementos.append(Paragraph("<b>3. PARETO DE INVERSIÓN: TOP 5 FAMILIAS CON MAYOR IMPACTO FINANCIERO</b>", style_h2))
    elementos.append(Paragraph("Análisis de las 5 categorías comerciales que representan la mayor cantidad de capital inmovilizado en la compañía. Concentrar esfuerzos de negociación de compras aquí mejorará drásticamente el flujo de caja:", style_body))
    
    tabla_fam_data = [[
        Paragraph("Categoría / Familia", style_table_header),
        Paragraph("Capital Inmovilizado (S/.)", style_table_header),
        Paragraph("Participación Relativa %", style_table_header)
    ]]
    
    for _, row in top_familias.iterrows():
        tabla_fam_data.append([
            Paragraph(limpiar_texto_xml(row['Familia']), style_table_cell),
            Paragraph(f"S/. {row['Inversion']:,.2f}", style_table_cell_r),
            Paragraph(f"{row['Participacion']:.2f}%", style_table_cell_r)
        ])
        
    t_fam = Table(tabla_fam_data, colWidths=[244, 130, 130])
    t_fam.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(t_fam)
    elementos.append(Spacer(1, 15))
    
    # Nota de Auditoría Logística
    elementos.append(Paragraph("<i>Nota: Los datos expresados en este documento corresponden a valores de costo cargados en sistema y representan auditoría de activos corrientes tangibles para fines de toma de decisiones operativas.</i>", ParagraphStyle('Note', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, leading=9, textColor=colors.HexColor("#64748b"))))
    
    # Retornamos el PDF compilado usando la maqueta maestra
    return _compilar_pdf_base("Reporte Gerencial de Capital Inmovilizado", "Análisis de Estructura de Activos Corrientes", elementos)


# --- INFORME 2: ROTACIÓN ---
def generar_pdf_rotacion(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>2. Análisis de Rotación e Índice de Salida:</b> Evaluación del comportamiento de movimientos del almacén enfocado en la frecuencia acumulada y su categorización logística.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Código SKU", "Descripción", "Frecuencia NS", "Frec. Acum.", "% Acumulado", "Clasif. ABC"],
            col_widths=[80, 160, 70, 70, 64, 60],
            key_cols=["Codigo", "Descripcion", "FRECUENCIA", "FREQ_ACUM", "PORC_ACUM", "ABC_OPERATIVO"],
            is_numeric=[False, False, True, True, True, False],
            align_right=[False, False, True, True, True, False]
        )
    ]
    return _compilar_pdf_base("Reporte de Rotación ABC", "Clasificación Transaccional del Inventario", elementos)

# --- INFORME 3: COBERTURA ---
def generar_pdf_cobertura(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>3. Análisis de Cobertura y Días de Stock:</b> Diagnóstico del nivel de stock actual contra el promedio diario de despachos registrados en el período fiscal actual.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Código SKU", "Descripción", "Stock Físico", "Consumo Diario", "Días Cobertura", "Estatus"],
            col_widths=[80, 160, 64, 70, 70, 60],
            key_cols=["Codigo", "Descripcion", "Stock", "Consumo_Diario", "Dias_Cobertura", "Estatus_Cobertura"],
            is_numeric=[False, False, True, True, True, False],
            align_right=[False, False, True, True, True, False]
        )
    ]
    return _compilar_pdf_base("Reporte de Cobertura y Abastecimiento", "Gestión de Continuidad de Stock", elementos)

# --- INFORME 4: ENVEJECIMIENTO (AGING) ---
def generar_pdf_aging(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>4. Envejecimiento del Inventario (Aging):</b> Identificación de materiales de nula o baja rotación expuestos a riesgos de obsolescencia física y pérdida contable.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Código SKU", "Descripción", "Almacen", "Días Inactivo", "Costo Oport. Mensual"],
            col_widths=[80, 174, 90, 70, 90],
            key_cols=["Codigo", "Descripcion", "Almacen", "DIAS_INACTIVIDAD", "COSTO_OPORTUNIDAD_MENSUAL"],
            is_numeric=[False, False, False, True, True],
            align_right=[False, False, False, True, True]
        )
    ]
    return _compilar_pdf_base("Reporte de Envejecimiento (Aging)", "Evaluación de Obsolescencia y Costos Financieros", elementos)

# --- INFORME 5: CONCILIACIÓN ERI ---
def generar_pdf_eri(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>5. Conciliación ERI (Exactitud de Registro):</b> Balance de diferencias detectadas entre el conteo físico realizado en auditoría de campo y el stock de sistema.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Código SKU", "Almacén", "Teórico Sistema", "Físico Conteo", "Diferencia", "Impacto S/."],
            col_widths=[80, 114, 70, 70, 70, 100],
            key_cols=["Codigo", "Almacen", "Stock", "Conteo", "DIFERENCIA", "IMPACTO_FINANCIERO"],
            is_numeric=[False, False, True, True, True, True],
            align_right=[False, False, True, True, True, True]
        )
    ]
    return _compilar_pdf_base("Reporte de Exactitud de Registro (ERI)", "Auditoría Física y Ajustes Contables", elementos)

# --- INFORME 6: COMPRAS Y REAPROVISIONAMIENTO ---
def generar_pdf_compras(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>6. Sugerido de Reaprovisonamiento por Punto de Pedido:</b> Estimaciones calculadas para evitar quiebres de stock considerando el stock de seguridad.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Código SKU", "Descripción", "Stock Actual", "Pto. Pedido", "Stock Seg.", "Sugerido Compra"],
            col_widths=[80, 160, 64, 64, 66, 70],
            key_cols=["Codigo", "Descripcion", "Stock", "Punto_Pedido", "Stock_Seguridad", "Cantidad_Sugerida"],
            is_numeric=[False, False, True, True, True, True],
            align_right=[False, False, True, True, True, True]
        )
    ]
    return _compilar_pdf_base("Reporte Plan de Reaprovisonamiento", "Optimización de la Cadena de Suministro", elementos)

# --- INFORME 7: EVOLUCIÓN HISTÓRICA ---
def generar_pdf_evolucion(df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, spaceAfter=10)
    
    elementos = [
        Paragraph("<b>7. Evolutivo Mensual de Cierres Consolidados:</b> Reconstrucción histórica de los saldos del almacén calculados de manera inversa a partir de transacciones.", style_body),
        Spacer(1, 10),
        _crear_tabla_estandar(
            df=df,
            headers=["Período", "Stock Cierre (U)", "Valor de Inventario S/.", "Variación MoM %"],
            col_widths=[110, 130, 140, 124],
            key_cols=["MES", "STOCK_CIERRE", "VALOR_CIERRE", "VARIACION_MOM_%"],
            is_numeric=[False, True, True, True],
            align_right=[False, True, True, True]
        )
    ]
    return _compilar_pdf_base("Reporte Evolutivo de Cierres", "Análisis de Tendencias e Inventario Histórico", elementos)