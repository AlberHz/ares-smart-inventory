import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io

# Intento de carga de ReportLab para la generación del informe formal PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(
    layout="wide", 
    page_title="KPI 8 - INFORME GERENCIAL INTEGRADO",
    page_icon="📊"
)

# Estilos CSS ejecutivos para dashboards de dirección
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .executive-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    .executive-title {
        font-size: 0.80rem;
        font-weight: 800;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .executive-value {
        font-size: 1.8rem;
        font-weight: 900;
        color: #0f172a;
    }
    .executive-sub {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 4px;
    }
    .section-header-exec {
        font-size: 1.3rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 25px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 3px solid #1e293b;
    }
    .alert-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 0.95rem;
    }
    .alert-critical {
        background-color: #fef2f2;
        border-left: 5px solid #ef4444;
        color: #991b1b;
    }
    .alert-warning {
        background-color: #fffbeb;
        border-left: 5px solid #f59e0b;
        color: #92400e;
    }
    .alert-success {
        background-color: #f0fdf4;
        border-left: 5px solid #10b981;
        color: #166534;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# VALIDACIÓN DE ACCESO Y SESIÓN DE DATOS
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos de origen en el portal de inicio para sintetizar el informe gerencial.")
    st.stop()

# ==============================================================================
# MOTOR DE NORMALIZACIÓN Y CONSOLIDACIÓN INTEGRADA (MÓDULOS 1 AL 7)
# ==============================================================================
def sanitizar_numerico(serie):
    if serie is None or serie.empty:
        return pd.Series(dtype=float)
    return (
        serie.astype(str)
        .str.replace('S/.', '', regex=False)
        .str.replace('S/', '', regex=False)
        .str.replace('$', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0.0)
    )

@st.cache_data(show_spinner="Procesando métricas ejecutivas de los 7 módulos...")
def procesar_metricas_gerenciales(df_stock_raw, df_mov_raw):
    # Standard Stock
    df_stock = pd.DataFrame()
    df_stock['Codigo'] = df_stock_raw['Codigo'].astype(str).str.strip() if 'Codigo' in df_stock_raw.columns else df_stock_raw.iloc[:,0].astype(str).str.strip()
    df_stock['Descripcion'] = df_stock_raw['Descripcion'].astype(str).str.strip() if 'Descripcion' in df_stock_raw.columns else 'SIN DETALLE'
    df_stock['Almacen'] = df_stock_raw['Almacen'].astype(str).str.strip().str.upper() if 'Almacen' in df_stock_raw.columns else 'GENERAL'
    df_stock['Familia'] = df_stock_raw['Familia'].astype(str).str.strip().str.upper() if 'Familia' in df_stock_raw.columns else 'GENERAL'
    df_stock['SubFamilia'] = df_stock_raw['SubFamilia'].astype(str).str.strip().str.upper() if 'SubFamilia' in df_stock_raw.columns else 'GENERAL'
    df_stock['Stock'] = sanitizar_numerico(df_stock_raw['Stock']) if 'Stock' in df_stock_raw.columns else 0.0
    df_stock['Costo'] = sanitizar_numerico(df_stock_raw['Costo']) if 'Costo' in df_stock_raw.columns else 0.0
    df_stock['Valor_Total'] = df_stock['Stock'] * df_stock['Costo']

    # Standard Movimientos
    df_mov = pd.DataFrame()
    df_mov['Codigo'] = df_mov_raw['Codigo'].astype(str).str.strip() if 'Codigo' in df_mov_raw.columns else ''
    df_mov['Almacen'] = df_mov_raw['Almacen'].astype(str).str.strip().str.upper() if 'Almacen' in df_mov_raw.columns else 'GENERAL'
    df_mov['Tipo_Movimiento'] = df_mov_raw['Tipo_Movimiento'].astype(str).str.strip().str.upper() if 'Tipo_Movimiento' in df_mov_raw.columns else ''
    df_mov['Cantidad'] = sanitizar_numerico(df_mov_raw['Cantidad']) if 'Cantidad' in df_mov_raw.columns else 0.0
    df_mov['Transaccion'] = df_mov_raw['Transaccion'].astype(str).str.strip().str.upper() if 'Transaccion' in df_mov_raw.columns else ''
    if 'Fecha' in df_mov_raw.columns:
        df_mov['Fecha'] = pd.to_datetime(df_mov_raw['Fecha'], errors='coerce')
    else:
        df_mov['Fecha'] = pd.NaT

    # 1. METRICAS KPI 1 (Foto Actual)
    df_stock_act = df_stock[df_stock['Stock'] > 0]
    total_capital = df_stock_act['Valor_Total'].sum()
    total_unidades = df_stock_act['Stock'].sum()
    total_skus = df_stock_act['Codigo'].nunique()
    costo_prom_unidad = total_capital / total_unidades if total_unidades > 0 else 0

    # Concentración en Top 5 SKUs
    top5_skus = df_stock_act.groupby(['Codigo', 'Descripcion'])['Valor_Total'].sum().reset_index().sort_values(by='Valor_Total', ascending=False).head(5)
    cap_top5 = top5_skus['Valor_Total'].sum()
    pct_top5 = (cap_top5 / total_capital * 100) if total_capital > 0 else 0

    # 2. METRICAS KPI 3 (Pareto ABC Operativo)
    df_ns = df_mov[df_mov['Tipo_Movimiento'] == 'NS']
    frecuencia_pedidos = df_ns.groupby(['Codigo', 'Almacen']).size().reset_index(name='frecuencia')
    df_abc = pd.merge(df_stock_act, frecuencia_pedidos, on=['Codigo', 'Almacen'], how='left')
    df_abc['frecuencia'] = df_abc['frecuencia'].fillna(0)
    df_abc = df_abc.sort_values(by='frecuencia', ascending=False).reset_index(drop=True)
    
    tot_frec = df_abc['frecuencia'].sum()
    if tot_frec > 0:
        df_abc['frec_acum'] = df_abc['frecuencia'].cumsum() / tot_frec * 100
    else:
        df_abc['frec_acum'] = 0

    df_abc['clase_abc'] = np.select(
        [df_abc['frec_acum'] <= 80.001, df_abc['frec_acum'] <= 95.001],
        ['A', 'B'], default='C'
    )

    cap_clase_a = df_abc[df_abc['clase_abc'] == 'A']['Valor_Total'].sum()
    cap_clase_c = df_abc[df_abc['clase_abc'] == 'C']['Valor_Total'].sum()
    pct_cap_c = (cap_clase_c / total_capital * 100) if total_capital > 0 else 0
    skus_c = len(df_abc[df_abc['clase_abc'] == 'C'])

    # 3. METRICAS KPI 4 (Inmovilizados y Obsolescencia)
    ref_alm = df_stock_act.drop_duplicates('Codigo').set_index('Codigo')['Almacen'].to_dict()
    ref_fam = df_stock_act.drop_duplicates('Codigo').set_index('Codigo')['Familia'].to_dict()
    df_mov['Almacen_Ref'] = df_mov['Codigo'].map(ref_alm).fillna('')
    df_mov['Familia_Ref'] = df_mov['Codigo'].map(ref_fam).fillna('')
    
    df_mov['es_mp'] = df_mov['Almacen_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False) | df_mov['Familia_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False)
    df_mov['es_ingreso'] = df_mov['Tipo_Movimiento'].str.contains('NI|INGRESO', regex=True, na=False)
    salida_mp = df_mov['es_mp'] & df_mov['Transaccion'].str.contains('TD', regex=True, na=False)
    salida_otros = (~df_mov['es_mp']) & df_mov['Tipo_Movimiento'].str.contains('NS|SALIDA', regex=True, na=False)
    df_mov['es_salida'] = salida_mp | salida_otros

    fecha_hoy = pd.Timestamp(datetime.date.today())
    m_valid = df_mov[(df_mov['es_ingreso'] | df_mov['es_salida']) & df_mov['Fecha'].notnull()]

    if not m_valid.empty:
        s_ing = m_valid[m_valid['es_ingreso']].groupby('Codigo')['Fecha'].max()
        s_sal = m_valid[m_valid['es_salida']].groupby('Codigo')['Fecha'].max()
        m_sorted = m_valid.sort_values(['Codigo', 'Fecha'])
        m_sorted['gap'] = m_sorted.groupby('Codigo')['Fecha'].diff().dt.days
        s_max_gap = m_sorted.groupby('Codigo')['gap'].max().fillna(0)

        df_stock_act['f_ult_ingreso'] = df_stock_act['Codigo'].map(s_ing)
        df_stock_act['f_ult_salida'] = df_stock_act['Codigo'].map(s_sal)
        df_stock_act['max_gap'] = df_stock_act['Codigo'].map(s_max_gap).fillna(0)

        f_ref = df_stock_act['f_ult_salida'].combine_first(df_stock_act['f_ult_ingreso'])
        dias_inact = (fecha_hoy - f_ref).dt.days
        df_stock_act['dias_inactivo'] = dias_inact.fillna(999)
        df_stock_act['gap_efectivo'] = np.maximum(df_stock_act['dias_inactivo'], df_stock_act['max_gap'])
    else:
        df_stock_act['gap_efectivo'] = 999

    cap_critico_9m = df_stock_act[df_stock_act['gap_efectivo'] >= 270]['Valor_Total'].sum()
    cap_riesgo_6m = df_stock_act[(df_stock_act['gap_efectivo'] >= 180) & (df_stock_act['gap_efectivo'] < 270)]['Valor_Total'].sum()
    pct_critico = (cap_critico_9m / total_capital * 100) if total_capital > 0 else 0

    # 4. METRICAS KPI 5 (Kardex y Eficiencia de Quemado)
    tot_entradas_u = df_mov[df_mov['Tipo_Movimiento'] == 'NI']['Cantidad'].sum()
    tot_salidas_u = df_mov[df_mov['Tipo_Movimiento'] == 'NS']['Cantidad'].sum()
    
    costo_map = df_stock_act.set_index('Codigo')['Costo'].to_dict()
    df_mov['Costo'] = df_mov['Codigo'].map(costo_map).fillna(0.0)
    
    tot_entradas_soles = df_mov[df_mov['Tipo_Movimiento'] == 'NI'].eval('Cantidad * Costo').sum()
    tot_salidas_soles = df_mov[df_mov['Tipo_Movimiento'] == 'NS'].eval('Cantidad * Costo').sum()

    ratio_quemado = (tot_salidas_soles / tot_entradas_soles * 100) if tot_entradas_soles > 0 else 0.0

    return {
        'total_capital': total_capital,
        'total_unidades': total_unidades,
        'total_skus': total_skus,
        'costo_prom_unidad': costo_prom_unidad,
        'cap_top5': cap_top5,
        'pct_top5': pct_top5,
        'top5_skus': top5_skus,
        'cap_clase_a': cap_clase_a,
        'cap_clase_c': cap_clase_c,
        'pct_cap_c': pct_cap_c,
        'skus_c': skus_c,
        'cap_critico_9m': cap_critico_9m,
        'cap_riesgo_6m': cap_riesgo_6m,
        'pct_critico': pct_critico,
        'tot_entradas_soles': tot_entradas_soles,
        'tot_salidas_soles': tot_salidas_soles,
        'ratio_quemado': ratio_quemado,
        'df_stock_processed': df_stock_act,
        'df_abc': df_abc
    }

metrics = procesar_metricas_gerenciales(st.session_state['df_stock'], st.session_state['df_mov'])

# ==============================================================================
# ENCABEZADO Y CONTROLES DEL INFORME
# ==============================================================================
st.title("KPI 8 - INFORME GERENCIAL SINTETIZADO DE ALTA PRECISIÓN")
st.markdown("---")

st.markdown("""
<p style='color: #475569; font-size: 1.05rem;'>
Este módulo consolida de forma cuantitativa y cualitativa la salud operativa e inmovilizada del inventario. 
Extrae los hallazgos críticos de los Módulos 1 al 7 y genera recomendaciones dirigidas a Gerencia General, Finanzas y Operaciones.
</p>
""", unsafe_allow_html=True)

# BARRA LATERAL: PARÁMETROS DE REPORTE Y AUDITORÍA
st.sidebar.header("Parámetros del Informe Gerencial")
periodo_evaluado = st.sidebar.text_input("Periodo de Auditoría:", value=f"Cierre {datetime.date.today().strftime('%B %Y')}")
preparado_por = st.sidebar.text_input("Elaborado Por:", value="Unidad de Analítica & Cadena de Suministro")
dirigido_a = st.sidebar.text_input("Dirigido A:", value="Gerencia General / Dirección de Operaciones")

st.sidebar.markdown("---")
umbral_critico_pct = st.sidebar.slider("Umbral Máximo Tolerable de Inmovilizado (%):", min_value=5.0, max_value=25.0, value=10.0, step=0.5)

# ==============================================================================
# TABLERO GERENCIAL DE MANDO (RESUMEN EJECUTIVO DE KPIS)
# ==============================================================================
st.markdown("<div class='section-header-exec'>1. TABLERO INTEGRADO DE SALUD DEL INVENTARIO</div>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class='executive-card'>
        <div class='executive-title'>Capital Total Inmovilizado</div>
        <div class='executive-value'>S/. {metrics['total_capital']/1000:,.1f} K</div>
        <div class='executive-sub' style='color: #0284c7;'>{metrics['total_unidades']:,.0f} Unidades en Custodia</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    color_crit = "#dc2626" if metrics['pct_critico'] > umbral_critico_pct else "#d97706"
    st.markdown(f"""
    <div class='executive-card'>
        <div class='executive-title'>Riesgo Severo (>9 Meses Sin Flujo)</div>
        <div class='executive-value' style='color: {color_crit};'>S/. {metrics['cap_critico_9m']/1000:,.1f} K</div>
        <div class='executive-sub' style='color: {color_crit};'>{metrics['pct_critico']:.1f}% del Capital Total</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    color_c = "#dc2626" if metrics['pct_cap_c'] > 15.0 else "#2563eb"
    st.markdown(f"""
    <div class='executive-card'>
        <div class='executive-title'>Capital Atrapado en Clase C (Baja Rotación)</div>
        <div class='executive-value' style='color: {color_c};'>S/. {metrics['cap_clase_c']/1000:,.1f} K</div>
        <div class='executive-sub' style='color: #64748b;'>{metrics['skus_c']} SKUs con baja demanda</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    color_q = "#16a34a" if metrics['ratio_quemado'] >= 100.0 else "#dc2626"
    st.markdown(f"""
    <div class='executive-card'>
        <div class='executive-title'>Ratio Eficiencia Quemado (Salidas/Entradas)</div>
        <div class='executive-value' style='color: {color_q};'>{metrics['ratio_quemado']:.1f}%</div>
        <div class='executive-sub' style='color: #64748b;'>{"Flujo Sostenible (Despacho > Compra)" if metrics['ratio_quemado']>=100 else "Alerta: Acumulación Activa"}</div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# SÍNTESIS EVALUATIVA Y DIAGNÓSTICO NARRATIVO
# ==============================================================================
st.markdown("<div class='section-header-exec'>2. DIAGNÓSTICO ESTRATÉGICO Y DICTAMEN TÉCNICO</div>", unsafe_allow_html=True)

# Lógica de Diagnóstico Dinámico
if metrics['pct_critico'] > umbral_critico_pct:
    alerta_severidad = "CRÍTICA"
    box_class = "alert-critical"
    dictamen_texto = f"""Se detecta un nivel de inmovilizado del <b>{metrics['pct_critico']:.1f}%</b> (S/. {metrics['cap_critico_9m']:,.2f}), el cual superó el umbral máximo tolerable establecido por gerencia ({umbral_critico_pct:.1f}%). 
    Existe capital ineficiente expuesto a desvalorización y costo de oportunidad financiero elevado."""
else:
    alerta_severidad = "ACEPTABLE / CONTROLADA"
    box_class = "alert-success"
    dictamen_texto = f"""El nivel de inmovilizado severo se mantiene en <b>{metrics['pct_critico']:.1f}%</b>, por debajo del límite gerencial del {umbral_critico_pct:.1f}%. El stock presenta dinamismo pero requiere monitoreo contínuo."""

st.markdown(f"""
<div class='alert-box {box_class}'>
    <b>DIAGNÓSTICO GENERAL DE LA GESTIÓN DE STOCK (EVALUACIÓN {alerta_severidad}):</b><br>
    {dictamen_texto}
</div>
""", unsafe_allow_html=True)

col_diag1, col_diag2 = st.columns(2)

with col_diag1:
    st.subheader("Hallazgos Operativos Clave")
    st.markdown(f"""
    * **Vulnerabilidad por Concentración:** El **{metrics['pct_top5']:.1f}%** del valor total del inventario (S/. {metrics['cap_top5']:,.2f}) se concentra en tan solo 5 SKUs.
    * **Desfase en Matriz ABC:** Un total de **{metrics['skus_c']} SKUs** pertenecen a la Clase C (baja frecuencia de despacho), reteniendo **S/. {metrics['cap_clase_c']:,.2f}** ({metrics['pct_cap_c']:.1f}% del capital).
    * **Riesgo Medio de Obsolescencia:** Adicional al stock crítico, existen **S/. {metrics['cap_riesgo_6m']:,.2f}** en riesgo medio (entre 6 y 9 meses sin salidas).
    * **Comportamiento de Flujo (Kardex):** Durante el periodo evaluado, las entradas valorizadas sumaron **S/. {metrics['tot_entradas_soles']:,.2f}** frente a salidas por **S/. {metrics['tot_salidas_soles']:,.2f}**.
    """)

with col_diag2:
    st.subheader("Plan de Acción y Recomendaciones Gerenciales")
    st.markdown("""
    1. **Plan de Liquidación Inmediata (SKUs >9 Meses):** Conformar un comité técnico con Comercial/Operaciones para rematar o castigar el stock inmovilizado crítico y recuperar liquidez.
    2. **Revisión de Política de Compras para Clase C:** Congelar las órdenes de compra automáticas de SKUs en Clase C. Aplicar compras bajo pedido (Make-to-Order / Just-In-Time).
    3. **Ajuste de Stock Máximos en Top Concentración:** Revisar los puntos de reorden para los 5 SKUs principales para evitar la inmovilización de capital de trabajo masivo.
    4. **Regla de Balance de Quemado:** Mantener el índice de quemado por encima del 100% para evitar el sobrestockeo continuo de los almacenes.
    """)

st.markdown("---")

# ==============================================================================
# VISUALIZACIONES EJECUTIVAS RESUMIDAS
# ==============================================================================
st.markdown("<div class='section-header-exec'>3. MATRIZ DE CAPITAL Y ESTRUCTURA DE RIESGO</div>", unsafe_allow_html=True)

v1, v2 = st.columns(2)

with v1:
    st.subheader("Distribución de Capital por Tramo de Rotación")
    
    # Agrupamiento de Tramos
    df_sp = metrics['df_stock_processed'].copy()
    conds = [
        df_sp['gap_efectivo'] < 90,
        (df_sp['gap_efectivo'] >= 90) & (df_sp['gap_efectivo'] < 180),
        (df_sp['gap_efectivo'] >= 180) & (df_sp['gap_efectivo'] < 270)
    ]
    choices = ['1-3 Meses (Activo)', '3-6 Meses (Medio)', '6-9 Meses (Riesgo)']
    df_sp['Tramo'] = np.select(conds, choices, default='>9 Meses (Crítico)')
    
    df_tramo_g = df_sp.groupby('Tramo')['Valor_Total'].sum().reset_index()
    
    fig_tramo = px.pie(
        df_tramo_g, 
        values='Valor_Total', 
        names='Tramo', 
        hole=0.4,
        color='Tramo',
        color_discrete_map={
            '1-3 Meses (Activo)': '#10b981',
            '3-6 Meses (Medio)': '#f59e0b',
            '6-9 Meses (Riesgo)': '#f97316',
            '>9 Meses (Crítico)': '#ef4444'
        }
    )
    fig_tramo.update_traces(textinfo='percent+label', hovertemplate="<b>%{label}</b><br>Capital: S/. %{value:,.2f}<extra></extra>")
    fig_tramo.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
    st.plotly_chart(fig_tramo, use_container_width=True)

with v2:
    st.subheader("Top 5 SKUs de Mayor Concentración de Capital")
    df_top5_vis = metrics['top5_skus'].sort_values(by='Valor_Total', ascending=True)
    
    fig_top5 = px.bar(
        df_top5_vis,
        x='Valor_Total',
        y='Descripcion',
        orientation='h',
        text=df_top5_vis['Valor_Total'].apply(lambda x: f"S/. {x/1000:,.1f}K"),
        color_continuous_scale='blues'
    )
    fig_top5.update_traces(marker_color="#1e40af", textposition='outside')
    fig_top5.update_layout(height=350, plot_bgcolor="white", xaxis_title="Monto Inmovilizado (S/.)", yaxis_title="", margin=dict(t=20, b=20, l=10, r=80))
    st.plotly_chart(fig_top5, use_container_width=True)

# ==============================================================================
# SECCIÓN DE DESCARGA DE INFORMES EN PDF Y EXCEL
# ==============================================================================
st.markdown("<div class='section-header-exec'>4. EXPORTACIÓN DE INFORMES GERENCIALES</div>", unsafe_allow_html=True)

col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    st.subheader("📄 Generar Informe Ejecutivo en PDF")
    st.write("Descargue un documento PDF formateado con encabezado institucional, resumen ejecutivo y firmas directivas.")

    def generar_pdf_gerencial(m, periodo, autor, destinatario):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#475569'),
            spaceAfter=15
        )
        
        h2_style = ParagraphStyle(
            'H2Style',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155'),
            spaceAfter=6
        )

        elements = []

        # Encabezado
        elements.append(Paragraph("INFORME GERENCIAL DE AUDITORÍA Y SALUD DE INVENTARIO", title_style))
        elements.append(Paragraph(f"<b>Periodo:</b> {periodo} | <b>Elaborado por:</b> {autor} | <b>Dirigido a:</b> {destinatario}", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e293b'), spaceAfter=12))

        # Tabla de KPIS Gerenciales
        data_kpis = [
            ["Métrica Gerencial Evaluada", "Valor Obtenido", "Estado / Diagnóstico"],
            ["Capital Total Inmovilizado", f"S/. {m['total_capital']:,.2f}", f"{m['total_unidades']:,.0f} Unidades en custodia"],
            ["Riesgo Severo (>9 Meses)", f"S/. {m['cap_critico_9m']:,.2f}", f"{m['pct_critico']:.1f}% del capital total"],
            ["Capital en Clase C (Baja Rotación)", f"S/. {m['cap_clase_c']:,.2f}", f"{m['skus_c']} SKUs sin demanda frecuente"],
            ["Ratio de Eficiencia de Quemado", f"{m['ratio_quemado']:.1f}%", "Flujo Sostenible" if m['ratio_quemado']>=100 else "Riesgo de Acumulación"]
        ]
        
        t_kpis = Table(data_kpis, colWidths=[200, 140, 200])
        t_kpis.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_kpis)
        elements.append(Spacer(1, 12))

        # Resumen Ejecutivo
        elements.append(Paragraph("1. RESUMEN EJECUTIVO Y HALLAZGOS", h2_style))
        eval_txt = f"El valor total en custodia asciende a <b>S/. {m['total_capital']:,.2f}</b> distribuido en <b>{m['total_skus']} SKUs</b>. " \
                   f"Se detectó un nivel de inmovilizado crítico de <b>S/. {m['cap_critico_9m']:,.2f} ({m['pct_critico']:.1f}%)</b> con más de 9 meses sin rotación. " \
                   f"Existe una alta concentración en el Top 5 de productos que representan el <b>{m['pct_top5']:.1f}%</b> de la inversión total."
        elements.append(Paragraph(eval_txt, body_style))

        elements.append(Spacer(1, 8))
        elements.append(Paragraph("2. RECOMENDACIONES DE LA DIRECCIÓN", h2_style))
        rec_txt = "1. Aprobar el plan de remate / castigo del stock crítico con más de 9 meses inactivo.<br/>" \
                  "2. Restringir la emisión de nuevas órdenes de compra para artículos catalogados en Clase C.<br/>" \
                  "3. Rediseñar los stocks máximos para los SKUs de mayor impacto de capital."
        elements.append(Paragraph(rec_txt, body_style))

        elements.append(Spacer(1, 25))
        
        # Firmas
        data_firmas = [
            ["____________________________________", "____________________________________"],
            ["Unidad de Analítica / Logística", "Gerencia General / Dirección"]
        ]
        t_firmas = Table(data_firmas, colWidths=[270, 270])
        t_firmas.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#475569')),
        ]))
        elements.append(KeepTogether(t_firmas))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    if REPORTLAB_INSTALLED:
        pdf_data = generar_pdf_gerencial(metrics, periodo_evaluado, preparado_por, dirigido_a)
        st.download_button(
            label="📥 Descargar Informe Ejecutivo en PDF",
            data=pdf_data,
            file_name=f"Informe_Gerencial_Inventario_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.error("Para la exportación PDF, asegúrese de tener instalada la librería `reportlab` (`pip install reportlab`).")

with col_exp2:
    st.subheader("📊 Exportar Consolidado Completo en Excel")
    st.write("Obtenga el libro de trabajo con pestañas independientes para los tableros de control y detalle de SKUs.")

    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        # Pestaña 1: KPIs
        df_kpis_exp = pd.DataFrame([
            {"Métrica": "Capital Total Inmovilizado", "Valor": metrics['total_capital']},
            {"Métrica": "Total Unidades", "Valor": metrics['total_unidades']},
            {"Métrica": "Inmovilizado Crítico (>9 Meses)", "Valor": metrics['cap_critico_9m']},
            {"Métrica": "% Inmovilizado Crítico", "Valor": metrics['pct_critico']},
            {"Métrica": "Capital Clase C", "Valor": metrics['cap_clase_c']},
            {"Métrica": "Ratio Eficiencia Quemado (%)", "Valor": metrics['ratio_quemado']}
        ])
        df_kpis_exp.to_excel(writer, index=False, sheet_name='Resumen_Gerencial')
        
        # Pestaña 2: Top 5 SKUs
        metrics['top5_skus'].to_excel(writer, index=False, sheet_name='Top5_Concentracion')

        # Pestaña 3: Detalle Completo Stock
        metrics['df_stock_processed'].to_excel(writer, index=False, sheet_name='Detalle_Stock_Auditado')

    st.download_button(
        label="📥 Descargar Paquete Gerencial en Excel (.XLSX)",
        data=output_excel.getvalue(),
        file_name=f"Paquete_Gerencial_Inventarios_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )