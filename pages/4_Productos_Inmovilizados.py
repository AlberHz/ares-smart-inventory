import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import io

st.set_page_config(layout="wide")

# ==============================================================================
# 1. VALIDACIÓN DE CONTENEDORES EN MEMORIA
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos en el portal de inicio (app.py) para acceder a este módulo.")
    st.stop()

# Copias de seguridad operativas
df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

# Estandarización de claves de negocio
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_stock['Descripcion'] = df_stock.get('Descripcion', df_stock.get('Item', 'PRODUCTO SIN DETALLE')).astype(str).str.strip()
df_stock['Almacen'] = df_stock['Almacen'].astype(str).str.strip()
df_stock['Familia'] = df_stock['Familia'].astype(str).str.strip().str.upper()
df_stock['SubFamilia'] = df_stock.get('SubFamilia', pd.Series(['GENERAL'] * len(df_stock))).astype(str).str.strip().str.upper()

df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()
df_mov['Tipo_Movimiento'] = df_mov['Tipo_Movimiento'].astype(str).str.strip().str.upper()

# ==============================================================================
# 2. PROCESAMIENTO DEL CUBO DE ENVEJECIMIENTO (EQUIVALENTE A LA LOGICA SQL)
# ==============================================================================
@st.cache_data(show_spinner=False)
def procesar_cubo_envejecimiento(df_s, df_m):
    # Filtrar existencias reales
    base_inventario = df_s[df_s['Stock'] > 0].copy()
    
    # Obtener la fecha del último despacho de cliente (NS) por código
    df_ns = df_m[df_m['Tipo_Movimiento'] == 'NS'].copy()
    df_ns['Fecha'] = pd.to_datetime(df_ns['Fecha'], errors='coerce')
    ultimas_salidas = df_ns.groupby('Codigo')['Fecha'].max().reset_index(name='ultima_fecha')
    
    # Cruce maestro de información (LEFT JOIN)
    df_maestro = pd.merge(base_inventario, ultimas_salidas, on='Codigo', how='left')
    
    # Calcular días de inactividad en base a la fecha de ejecución
    fecha_hoy = pd.Timestamp(datetime.date.today())
    
    def calcular_dias(row):
        if pd.isna(row['ultima_fecha']):
            return 9999  # Sin historial
        delta = (fecha_hoy - row['ultima_fecha']).days
        return delta if delta >= 0 else 0

    df_maestro['dias_inactivo'] = df_maestro.apply(calcular_dias, axis=1)
    df_maestro['valor_total'] = df_maestro['Stock'] * df_maestro['Costo']
    
    return df_maestro

df_datos_maestros = procesar_cubo_envejecimiento(df_stock, df_mov)

# ==============================================================================
# 3. FILTROS ESTRATÉGICOS SUPERIORES
# ==============================================================================
st.title("🗂️ Dashboard Ejecutivo de Inventario Inmovilizado y Obsolescencia")
st.markdown("---")

lista_almacenes = ["TODOS"] + sorted(df_datos_maestros['Almacen'].dropna().unique().tolist())
lista_familias = ["TODAS"] + sorted(df_datos_maestros['Familia'].dropna().unique().tolist())

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    almacen_filtro = st.selectbox("📍 1. Almacén Operativo", lista_almacenes)
with col_f2:
    familia_filtro = st.selectbox("📦 2. Familia Contable", lista_familias)

# Filtro dinámico de subfamilias reactivo al filtro de familias
df_prev_sub = df_datos_maestros.copy()
if familia_filtro != "TODAS":
    df_prev_sub = df_prev_sub[df_prev_sub['Familia'] == familia_filtro]
lista_subfamilias = ["TODAS"] + sorted(df_prev_sub['SubFamilia'].dropna().unique().tolist())

with col_f3:
    subfamilia_filtro = st.selectbox("🌿 3. Subfamilia Específica", lista_subfamilias)
with col_f4:
    dias_alerta = st.selectbox(
        "🚨 4. Alerta de Inactividad Mínima",
        [90, 180, 270, 365],
        index=1,
        format_func=lambda x: f"⏱️ Mayor a {x} Días ({x//30} Meses)"
    )

# Parámetro financiero clave para presentar a Gerencia
st.sidebar.header("Parámetros de Costo Financiero")
tasa_wacc = st.sidebar.slider("Costo de Oportunidad Anual de Capital (WACC) %", 5.0, 25.0, 12.0, step=0.5) / 100.0

# Aplicación estricta de filtros cruzados en cascada
df_filtrado_combos = df_datos_maestros.copy()
if almacen_filtro != "TODOS":
    df_filtrado_combos = df_filtrado_combos[df_filtrado_combos['Almacen'] == almacen_filtro]
if familia_filtro != "TODAS":
    df_filtrado_combos = df_filtrado_combos[df_filtrado_combos['Familia'] == familia_filtro]
if subfamilia_filtro != "TODAS":
    df_filtrado_combos = df_filtrado_combos[df_filtrado_combos['SubFamilia'] == subfamilia_filtro]

# Segmentación crítica de riesgo
df_inmovilizados_criticos = df_filtrado_combos[df_filtrado_combos['dias_inactivo'] >= dias_alerta].copy()

# ==============================================================================
# 4. LÓGICA DE ASIGNACIÓN DE TRAMOS DE MADURACIÓN (AGING)
# ==============================================================================
def obtener_nombre_tramo(dias):
    if dias == 9999: return 'Sin Historial de Salidas'
    if dias > 365: return 'Más de 1 Año (>365 días)'
    if dias > 270: return '9 Meses (271 a 365 días)'
    if dias > 180: return '6 Meses (181 a 270 días)'
    if dias >= 90: return '3 Meses (90 a 180 días)'
    return 'Rotación Activa (0 a 89 días)'

df_filtrado_combos['tramo_aging'] = df_filtrado_combos['dias_inactivo'].apply(obtener_nombre_tramo)
df_inmovilizados_criticos['tramo_aging'] = df_inmovilizados_criticos['dias_inactivo'].apply(obtener_nombre_tramo)

# ==============================================================================
# 5. CONSTRUCCIÓN DE CUADRO DE MANDOS DE KPIs FINANCIEROS (SUMMARY PANELS)
# ==============================================================================
valor_total_universo = df_filtrado_combos['valor_total'].sum()
total_skus_con_stock = len(df_filtrado_combos)
capital_paralizado = df_inmovilizados_criticos['valor_total'].sum()
total_skus_inmovilizados = len(df_inmovilizados_criticos)

porcentaje_capital_riesgo = (capital_paralizado / valor_total_universo * 100) if valor_total_universo > 0 else 0
costo_mantenimiento_mensual = (capital_paralizado * tasa_wacc) / 12

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(
        label="💰 Valorización de Stock Activo",
        value=f"S/. {valor_total_universo:,.2f}",
        delta=f"{total_skus_con_stock:,} SKUs en Existencia",
        delta_color="off"
    )

with kpi_col2:
    st.metric(
        label="⚠️ Capital Paralizado en Riesgo",
        value=f"S/. {capital_paralizado:,.2f}",
        delta=f"{porcentaje_capital_riesgo:.1f}% del Inventario",
        delta_color="inverse"
    )

with kpi_col3:
    st.metric(
        label="📉 Pérdida Financiera Mensual (WACC)",
        value=f"S/. {costo_mantenimiento_mensual:,.2f}",
        delta="Costo de oportunidad de caja",
        delta_color="inverse"
    )

with kpi_col4:
    st.metric(
        label="📦 SKUs Bajo Alerta Crítica",
        value=f"{total_skus_inmovilizados:,} Items",
        delta=f"Inactividad >= {dias_alerta} días",
        delta_color="inverse"
    )

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 6. PESTAÑAS DE NAVEGACIÓN E INTELIGENCIA DE NEGOCIO (BI)
# ==============================================================================
tabs = st.tabs([
    "📊 ANÁLISIS AVANZADO GRÁFICOS BI",
    "🧮 MATRIZ DE ENVEJECIMIENTO (AGING REPORT)",
    f"📋 AUDITORÍA DE CÓDIGOS CRÍTICOS ({total_skus_inmovilizados})"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: GRÁFICOS ANALÍTICOS BI
# ------------------------------------------------------------------------------
with tabs[0]:
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Participación Financiera por Familia Inmovilizada</h6>", unsafe_allow_html=True)
        
        chart_pie_familias = df_inmovilizados_criticos.groupby('Familia')['valor_total'].sum().reset_index()
        chart_pie_familias = chart_pie_familias.sort_values(by='valor_total', ascending=False).head(7)
        
        if chart_pie_familias.empty:
            st.info("Sin datos bajo los criterios de alerta seleccionados.")
        else:
            fig_pie = go.Figure(data=[go.Pie(
                labels=chart_pie_familias['Familia'],
                values=chart_pie_familias['valor_total'],
                hole=0.4,
                marker=dict(colors=['#10b981', '#3b82f6', '#f59e0b', '#e67e22', '#ef4444', '#64748b', '#7c3aed']),
                textinfo='percent+label'
            )])
            fig_pie.update_layout(
                showlegend=False, 
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                plot_bgcolor="white"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with col_g2:
        st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Distribución Económica por Bloques de Envejecimiento</h6>", unsafe_allow_html=True)
        
        # Agrupación por orden lógico establecido del Reporte de Aging
        orden_tramos = [
            'Rotación Activa (0 a 89 días)', '3 Meses (90 a 180 días)', 
            '6 Meses (181 a 270 días)', '9 Meses (271 a 365 días)', 
            'Más de 1 Año (>365 días)', 'Sin Historial de Salidas'
        ]
        
        df_aging_agrupado = df_filtrado_combos.groupby('tramo_aging')['valor_total'].sum().reindex(orden_tramos).fillna(0).reset_index()
        
        mapa_colores = {
            'Rotación Activa (0 a 89 días)': '#10b981',
            '3 Meses (90 a 180 días)': '#3b82f6',
            '6 Meses (181 a 270 días)': '#f59e0b',
            '9 Meses (271 a 365 días)': '#e67e22',
            'Más de 1 Año (>365 días)': '#ef4444',
            'Sin Historial de Salidas': '#64748b'
        }
        
        fig_bar_aging = go.Figure(data=[go.Bar(
            y=df_aging_agrupado['tramo_aging'],
            x=df_aging_agrupado['valor_total'],
            orientation='h',
            marker_color=[mapa_colores[x] for x in df_aging_agrupado['tramo_aging']],
            text=[f"S/. {v:,.0f}" for v in df_aging_agrupado['valor_total']],
            textposition='outside'
        )])
        
        fig_bar_aging.update_layout(
            margin=dict(l=20, r=40, t=10, b=10),
            height=280,
            plot_bgcolor="white"
        )
        # CORRECCIÓN DE SEGURIDAD EXCLUSIVA: 'family' en lugar de 'fontfamily' para evitar excepciones de Plotly
        fig_bar_aging.update_yaxes(tickfont=dict(size=10, family="monospace"), tickmode='linear')
        fig_bar_aging.update_xaxes(gridcolor="#f1f5f9")
        st.plotly_chart(fig_bar_aging, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Top Subfamilias con Mayor Concentración de Obsolescencia</h6>", unsafe_allow_html=True)
    
    chart_subf = df_inmovilizados_criticos.groupby('SubFamilia')['valor_total'].sum().reset_index()
    chart_subf = chart_subf.sort_values(by='valor_total', ascending=False).head(10)
    
    if chart_subf.empty:
        st.info("Sin registros de criticidad en subfamilias.")
    else:
        fig_subf = go.Figure(data=[go.Bar(
            x=chart_subf['SubFamilia'],
            y=chart_subf['valor_total'],
            marker_color="#7c3aed",
            text=[f"S/. {v:,.0f}" for v in chart_subf['valor_total']],
            textposition='outside'
        )])
        fig_subf.update_layout(plot_bgcolor="white", height=280, margin=dict(l=20, r=20, t=20, b=40))
        fig_subf.update_xaxes(tickangle=-20, tickfont=dict(size=10))
        fig_subf.update_yaxes(gridcolor="#f1f5f9")
        st.plotly_chart(fig_subf, use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: MATRIZ ESTRUCTURADA AGING REPORT
# ------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Cuadro Técnico de Maduración Comercial (Realizabilidad)</h6>", unsafe_allow_html=True)
    
    df_matriz_aging = df_filtrado_combos.groupby('tramo_aging').agg(
        skus=('Codigo', 'count'),
        valor_existencia=('valor_total', 'sum')
    ).reindex(orden_tramos).fillna(0).reset_index()
    
    df_matriz_aging['% Impacto s/ Selección'] = (df_matriz_aging['valor_existencia'] / valor_total_universo * 100) if valor_total_universo > 0 else 0
    
    st.dataframe(
        df_matriz_aging.rename(columns={
            'tramo_aging': 'Tramo de Maduración / Envejecimiento',
            'skus': 'Cantidad de SKUs',
            'valor_existencia': 'Valorización de Existencias'
        }).style.format({
            'Cantidad de SKUs': '{:,}',
            'Valorización de Existencias': 'S/. {:,.2f}',
            '% Impacto s/ Selección': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )

# ------------------------------------------------------------------------------
# PESTAÑA 3: AUDITORÍA DE CÓDIGOS CRÍTICOS Y PLANES DE ACCIÓN
# ------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Plan de Liquidación y Auditoría Operativa de SKUs Estancados</h6>", unsafe_allow_html=True)
    
    # Descarga directa en Excel limpia para Tablas Dinámicas
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado_combos.to_excel(writer, index=False, sheet_name='AGING_COMPLETO_PIVOT')
    excel_binario = output.getvalue()
    
    st.download_button(
        label="📥 Exportar Universo Base Completo para Tabla Dinámica (.XLSX)",
        data=excel_binario,
        file_name=f"MAESTRO_REPORT_AGING_{almacen_filtro}_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if df_inmovilizados_criticos.empty:
        st.success("🎉 ¡Excelente! Ningún código califica en el estado crítico seleccionado.")
    else:
        # Definir acciones sugeridas para presentar a Gerencia
        def definir_estrategia_gerencial(dias):
            if dias == 9999: return '🔍 Investigar: Sin registros de venta histórica. Evaluar descarte o merma.'
            if dias > 365: return '🛑 Liquidación Extrema: Descuento agresivo o venta en lote para liberar espacio.'
            if dias > 270: return '⚠️ Oferta Comercial: Promocionar con el equipo de ventas, bonos por salida.'
            return '🔄 Rotación Lenta: Redistribuir a almacenes de mayor demanda regional.'

        df_inmovilizados_criticos['Plan de Acción Gerencial'] = df_inmovilizados_criticos['dias_inactivo'].apply(definir_estrategia_gerencial)
        
        # Formatear columna de visualización de días
        df_inmovilizados_criticos['Inactividad Real'] = df_inmovilizados_criticos['dias_inactivo'].apply(
            lambda x: "Sin Historial" if x == 9999 else f"{x} días ({round(x/30, 1)} meses)"
        )
        
        df_tabla_final = df_inmovilizados_criticos[[
            'Codigo', 'Descripcion', 'Almacen', 'Familia', 'Stock', 'Costo', 'valor_total', 'Inactividad Real', 'Plan de Acción Gerencial'
        ]].rename(columns={
            'valor_total': 'Valorización',
            'Stock': 'Stock Físico',
            'Costo': 'Costo U.'
        }).sort_values(by='Valorización', ascending=False)
        
        st.dataframe(
            df_tabla_final.style.format({
                'Stock Físico': '{:,}',
                'Costo U.': 'S/. {:,.4f}',
                'Valorización': 'S/. {:,.2f}'
            }),
            use_container_width=True, hide_index=True
        )