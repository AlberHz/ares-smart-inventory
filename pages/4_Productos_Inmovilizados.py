import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS UI/UX
# ==============================================================================
st.set_page_config(
    layout="wide", 
    page_title="KPI 4 - CÓDIGOS INMOVILIZADOS",
    page_icon="📦"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .kpi-title {
        font-size: 0.72rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.3rem;
        font-weight: 800;
        color: #0f172a;
    }
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 25px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNCIONES DE LIMPIEZA Y ESTANDARIZACIÓN
# ==============================================================================
def sanitizar_serie_numerica(serie):
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

def estandarizar_columnas(df):
    df = df.copy()
    mapeo = {}
    for col in df.columns:
        col_clean = str(col).strip().upper()
        col_clean_sin_tilde = col_clean.replace('Ó', 'O').replace('Í', 'I').replace('Á', 'A').replace('É', 'E').replace('Ú', 'U')
        
        if col_clean_sin_tilde in ['CODIGO', 'SKU', 'MATERIAL', 'ARTICULO', 'CODIGO_MATERIAL', 'CODIGO MATERIAL', 'ITEM']:
            mapeo[col] = 'CODIGO'
        elif col_clean_sin_tilde in ['DESCRIPCION', 'PRODUCTO', 'DETALLE', 'MATERIAL_DESCRIPCION', 'NOMBRE']:
            mapeo[col] = 'DESCRIPCION'
        elif col_clean_sin_tilde in ['ALMACEN', 'ALM', 'CENTRO', 'BODEGA', 'DEPOSITO', 'NOMALMACEN']:
            mapeo[col] = 'ALMACEN'
        elif col_clean_sin_tilde in ['FAMILIA', 'CATEGORIA', 'LINEA']:
            mapeo[col] = 'FAMILIA'
        elif col_clean_sin_tilde in ['SUBFAMILIA', 'SUBCATEGORIA', 'SUBLINEA']:
            mapeo[col] = 'SUBFAMILIA'
        elif col_clean_sin_tilde in ['COSTO', 'COSTO_UNITARIO', 'COSTO UNITARIO', 'PRECIO', 'VAL UNIT']:
            mapeo[col] = 'COSTO'
        elif col_clean_sin_tilde in ['STOCK', 'CANTIDAD_STOCK', 'STOCK_ACTUAL', 'CANTIDAD_ACTUAL', 'CANTIDAD', 'SALDO']:
            mapeo[col] = 'STOCK'
        elif col_clean_sin_tilde in ['TIPO_MOVIMIENTO', 'TIPO_MOV', 'TIPO', 'TIPO_OPERACION', 'TIPO DOC', 'DOCUMENTO', 'MOVIMIENTO']:
            mapeo[col] = 'TIPO_MOVIMIENTO'
        elif col_clean_sin_tilde in ['TRANSACCION', 'TRANS', 'TIPO TRANSACCION', 'TIPO_TRANSACCION']:
            mapeo[col] = 'TRANSACCION'
        elif col_clean_sin_tilde in ['FECHA', 'FEC DOC', 'FEC MOV', 'FECHA_MOVIMIENTO']:
            mapeo[col] = 'FECHA'
            
    return df.rename(columns=mapeo)

# ==============================================================================
# 1. CARGA Y PREPARACIÓN DE DATOS
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock_raw = estandarizar_columnas(st.session_state['df_stock'])
df_mov_raw = estandarizar_columnas(st.session_state['df_mov'])

# Asegurar existencia de columnas necesarias
for c in ['CODIGO', 'DESCRIPCION', 'ALMACEN', 'FAMILIA', 'SUBFAMILIA', 'STOCK', 'COSTO']:
    if c not in df_stock_raw.columns:
        if c == 'DESCRIPCION': df_stock_raw[c] = 'SIN DESCRIPCIÓN'
        elif c in ['ALMACEN', 'FAMILIA', 'SUBFAMILIA']: df_stock_raw[c] = 'GENERAL'
        else: df_stock_raw[c] = 0

for c in ['CODIGO', 'TIPO_MOVIMIENTO', 'TRANSACCION', 'FECHA']:
    if c not in df_mov_raw.columns:
        df_mov_raw[c] = ''

df_stock_base = pd.DataFrame({
    'CODIGO': df_stock_raw['CODIGO'].astype(str).str.strip().str.upper(),
    'DESCRIPCION': df_stock_raw['DESCRIPCION'].astype(str).str.strip(),
    'ALMACEN': df_stock_raw['ALMACEN'].astype(str).str.strip().str.upper(),
    'FAMILIA': df_stock_raw['FAMILIA'].astype(str).str.strip().str.upper(),
    'SUBFAMILIA': df_stock_raw['SUBFAMILIA'].astype(str).str.strip().str.upper(),
    'STOCK': sanitizar_serie_numerica(df_stock_raw['STOCK']),
    'COSTO': sanitizar_serie_numerica(df_stock_raw['COSTO'])
})

# FILTRO CLAVE: Únicamente considerar SKUs con Stock Físico > 0
df_stock = df_stock_base[df_stock_base['STOCK'] > 0].copy()

df_mov = pd.DataFrame({
    'CODIGO': df_mov_raw['CODIGO'].astype(str).str.strip().str.upper(),
    'TIPO_MOVIMIENTO': df_mov_raw['TIPO_MOVIMIENTO'].astype(str).str.strip().str.upper(),
    'TRANSACCION': df_mov_raw['TRANSACCION'].astype(str).str.strip().str.upper(),
    'FECHA': pd.to_datetime(df_mov_raw['FECHA'], errors='coerce')
})

# ==============================================================================
# 2. LÓGICA REGLA TD EN MATERIA PRIMA VS NI/NS
# ==============================================================================
ref_almacen = df_stock.drop_duplicates('CODIGO').set_index('CODIGO')['ALMACEN'].to_dict()
ref_familia = df_stock.drop_duplicates('CODIGO').set_index('CODIGO')['FAMILIA'].to_dict()

df_mov['Almacen_Ref'] = df_mov['CODIGO'].map(ref_almacen).fillna('')
df_mov['Familia_Ref'] = df_mov['CODIGO'].map(ref_familia).fillna('')

df_mov['es_mp'] = (
    df_mov['Almacen_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False) |
    df_mov['Familia_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False)
)

df_mov['es_ingreso'] = df_mov['TIPO_MOVIMIENTO'].str.contains('NI|INGRESO', regex=True, na=False)

salida_mp = df_mov['es_mp'] & df_mov['TRANSACCION'].str.contains('TD', regex=True, na=False)
salida_otros = (~df_mov['es_mp']) & df_mov['TIPO_MOVIMIENTO'].str.contains('NS|SALIDA', regex=True, na=False)
df_mov['es_salida'] = salida_mp | salida_otros

# ==============================================================================
# 3. MOTOR VECTORIZADO DE CÁLCULOS DE GAPS
# ==============================================================================
@st.cache_data(show_spinner=False)
def calcular_gaps_vectorizado(df_s, df_m):
    base = df_s.copy()
    fecha_hoy = pd.Timestamp(datetime.date.today())
    
    m_valid = df_m[(df_m['es_ingreso'] | df_m['es_salida']) & df_m['FECHA'].notnull()]
    
    if m_valid.empty:
        base['f_ult_ingreso'] = pd.NaT
        base['f_ult_salida'] = pd.NaT
        base['dias_inactivo_hoy'] = 999
        base['max_gap_historico'] = 0
        base['gap_efectivo'] = 999
        base['es_espejismo'] = False
    else:
        s_ingresos = m_valid[m_valid['es_ingreso']].groupby('CODIGO')['FECHA'].max()
        s_salidas = m_valid[m_valid['es_salida']].groupby('CODIGO')['FECHA'].max()
        
        m_sorted = m_valid.sort_values(['CODIGO', 'FECHA'])
        m_sorted['gap'] = m_sorted.groupby('CODIGO')['FECHA'].diff().dt.days
        s_max_gap = m_sorted.groupby('CODIGO')['gap'].max().fillna(0)
        
        base['f_ult_ingreso'] = base['CODIGO'].map(s_ingresos)
        base['f_ult_salida'] = base['CODIGO'].map(s_salidas)
        base['max_gap_historico'] = base['CODIGO'].map(s_max_gap).fillna(0)
        
        f_ref = base['f_ult_salida'].combine_first(base['f_ult_ingreso'])
        dias_inact = (fecha_hoy - f_ref).dt.days
        base['dias_inactivo_hoy'] = dias_inact.fillna(999)
        
        base['gap_efectivo'] = np.maximum(base['dias_inactivo_hoy'], base['max_gap_historico'])
        
        base['es_espejismo'] = (
            base['f_ult_salida'].notnull() & 
            (base['dias_inactivo_hoy'] < 90) & 
            (base['max_gap_historico'] >= 180)
        )
        
    conds = [
        base['gap_efectivo'] < 90,
        (base['gap_efectivo'] >= 90) & (base['gap_efectivo'] < 180),
        (base['gap_efectivo'] >= 180) & (base['gap_efectivo'] < 270)
    ]
    choices = [
        '1 a 3 Meses (Rotación Activa)',
        '3 a 6 Meses (Rotación Media)',
        '6 a 9 Meses (Rotación Baja / Riesgo)'
    ]
    base['tramo_rotacion'] = np.select(conds, choices, default='9 a Más Meses (Inmovilizado Crítico)')
    base['capital_total'] = base['STOCK'] * base['COSTO']
    
    return base

df_datos_maestros = calcular_gaps_vectorizado(df_stock, df_mov)

orden_tramos = [
    '1 a 3 Meses (Rotación Activa)',
    '3 a 6 Meses (Rotación Media)',
    '6 a 9 Meses (Rotación Baja / Riesgo)',
    '9 a Más Meses (Inmovilizado Crítico)'
]

colores_tramos = {
    '1 a 3 Meses (Rotación Activa)': '#10b981',
    '3 a 6 Meses (Rotación Media)': '#f59e0b',
    '6 a 9 Meses (Rotación Baja / Riesgo)': '#f97316',
    '9 a Más Meses (Inmovilizado Crítico)': '#b91c1c'
}

# ==============================================================================
# 4. CONTROLES Y FILTROS
# ==============================================================================
st.title("KPI 4 - ANÁLISIS DE PRODUCTOS INMOVILIZADOS")
st.markdown("---")

lista_almacenes = ["TODOS"] + sorted([x for x in df_datos_maestros['ALMACEN'].unique() if x and str(x) != 'nan'])
lista_familias = ["TODAS"] + sorted([x for x in df_datos_maestros['FAMILIA'].unique() if x and str(x) != 'nan'])

f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1: almacen_filtro = st.selectbox("Almacén", lista_almacenes)
with f_col2: familia_filtro = st.selectbox("Familia", lista_familias)

df_prev_sub = df_datos_maestros.copy()
if familia_filtro != "TODAS": 
    df_prev_sub = df_prev_sub[df_prev_sub['FAMILIA'] == familia_filtro]
lista_subfamilias = ["TODAS"] + sorted([x for x in df_prev_sub['SUBFAMILIA'].unique() if x and str(x) != 'nan'])

with f_col3: subfamilia_filtro = st.selectbox("Subfamilia", lista_subfamilias)
with f_col4: tramo_filtro = st.selectbox("Rotación", ["TODOS"] + orden_tramos)

# Aplicar filtros
df_filtrado = df_datos_maestros.copy()
if almacen_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['ALMACEN'] == almacen_filtro]
if familia_filtro != "TODAS": 
    df_filtrado = df_filtrado[df_filtrado['FAMILIA'] == familia_filtro]
if subfamilia_filtro != "TODAS": 
    df_filtrado = df_filtrado[df_filtrado['SUBFAMILIA'] == subfamilia_filtro]
if tramo_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['tramo_rotacion'] == tramo_filtro]

# ==============================================================================
# 5. KPIS EJECUTIVOS (5 TARJETAS)
# ==============================================================================
v_total = df_filtrado['capital_total'].sum()
cant_skus = len(df_filtrado)

v_critico = df_filtrado[df_filtrado['tramo_rotacion'] == '9 a Más Meses (Inmovilizado Crítico)']['capital_total'].sum()
v_riesgo = df_filtrado[df_filtrado['tramo_rotacion'] == '6 a 9 Meses (Rotación Baja / Riesgo)']['capital_total'].sum()
v_media = df_filtrado[df_filtrado['tramo_rotacion'] == '3 a 6 Meses (Rotación Media)']['capital_total'].sum()
v_activa = df_filtrado[df_filtrado['tramo_rotacion'] == '1 a 3 Meses (Rotación Activa)']['capital_total'].sum()

pct_critico = (v_critico / v_total * 100) if v_total > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Capital Total Filtrado</div>
        <div class='kpi-value'>S/. {v_total:,.2f}</div>
        <div style='font-size:0.8rem; color:#64748b;'>{cant_skus:,} SKUs en Total</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Inmovilizado Crítico (> 9M)</div>
        <div class='kpi-value' style='color:#b91c1c;'>S/. {v_critico:,.2f}</div>
        <div style='font-size:0.8rem; color:#e11d48;'>{pct_critico:.1f}% del Capital Actual</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Riesgo Próximo (6 a 9M)</div>
        <div class='kpi-value' style='color:#f97316;'>S/. {v_riesgo:,.2f}</div>
        <div style='font-size:0.8rem; color:#d97706;'>Futuro inmovilizado si no se liquida</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Rotación Media (3 a 6M)</div>
        <div class='kpi-value' style='color:#f59e0b;'>S/. {v_media:,.2f}</div>
        <div style='font-size:0.8rem; color:#b45309;'>Bajo monitoreo de consumo</div>
    </div>
    """, unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Rotación Activa (1 a 3M)</div>
        <div class='kpi-value' style='color:#10b981;'>S/. {v_activa:,.2f}</div>
        <div style='font-size:0.8rem; color:#64748b;'>Capital con flujo constante</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 6. TABLEROS Y REPORTES DETALLADOS
# ==============================================================================
tab_alm, tab_top15, tab_tabla = st.tabs([
    "MATRIZ POR ALMACÉN", 
    "TOP 15 (SKUs, FAMILIAS Y SUBFAMILIAS)", 
    "DETALLE COMPLETO DE SKUs Y CAPITAL"
])

# ------------------------------------------------------------------------------
# TAB 1: MATRIZ CONSOLIDADA POR ALMACÉN
# ------------------------------------------------------------------------------
with tab_alm:
    st.markdown("<div class='section-header'>ROTACIÓN DE CAPITAL POR ALMACÉN</div>", unsafe_allow_html=True)
    
    df_chart_alm = df_filtrado.groupby(['ALMACEN', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    
    if not df_chart_alm.empty:
        fig_alm_stacked = px.bar(
            df_chart_alm, 
            y='ALMACEN', 
            x='capital_total', 
            color='tramo_rotacion', 
            orientation='h',
            text_auto='.2s',
            color_discrete_map=colores_tramos,
            category_orders={'tramo_rotacion': orden_tramos}
        )
        fig_alm_stacked.update_layout(
            yaxis=dict(autorange="reversed", title="Almacén"),
            xaxis=dict(title="Monto Valorizado (S/.)"),
            height=360,
            legend=dict(title="Tramo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_alm_stacked, use_container_width=True)
    
    st.markdown("<div class='section-header'>MATRIZ DETALLADA DE INMOVILIZADOS</div>", unsafe_allow_html=True)
    
    pivot_capital = df_filtrado.pivot_table(
        index='ALMACEN', columns='tramo_rotacion', values='capital_total', aggfunc='sum', fill_value=0
    ).reindex(columns=orden_tramos, fill_value=0)
    
    pivot_skus = df_filtrado.pivot_table(
        index='ALMACEN', columns='tramo_rotacion', values='CODIGO', aggfunc='nunique', fill_value=0
    ).reindex(columns=orden_tramos, fill_value=0)
    
    skus_totales = df_filtrado.groupby('ALMACEN')['CODIGO'].nunique().rename('SKUs Con Stock (>0)')
    capital_tot = df_filtrado.groupby('ALMACEN')['capital_total'].sum().rename('Capital Total (S/.)')
    
    df_matriz_alm = pd.concat([
        skus_totales,
        pivot_skus['1 a 3 Meses (Rotación Activa)'].rename('SKUs Activos (1-3M)'),
        pivot_skus['3 a 6 Meses (Rotación Media)'].rename('SKUs Media Rot (3-6M)'),
        pivot_skus['6 a 9 Meses (Rotación Baja / Riesgo)'].rename('SKUs Riesgo (6-9M)'),
        pivot_skus['9 a Más Meses (Inmovilizado Crítico)'].rename('SKUs Inmov. (>9M)'),
        capital_tot,
        pivot_capital['1 a 3 Meses (Rotación Activa)'].rename('Capital Activo (S/.)'),
        pivot_capital['3 a 6 Meses (Rotación Media)'].rename('Capital Media Rot (S/.)'),
        pivot_capital['6 a 9 Meses (Rotación Baja / Riesgo)'].rename('Capital Riesgo (S/.)'),
        pivot_capital['9 a Más Meses (Inmovilizado Crítico)'].rename('Capital Inmovilizado (S/.)')
    ], axis=1).fillna(0).reset_index()
    
    df_matriz_alm['% Inmovilizado (>9M)'] = np.where(
        df_matriz_alm['Capital Total (S/.)'] > 0,
        (df_matriz_alm['Capital Inmovilizado (S/.)'] / df_matriz_alm['Capital Total (S/.)']) * 100, 0
    )
    df_matriz_alm['% En Riesgo (6-9M)'] = np.where(
        df_matriz_alm['Capital Total (S/.)'] > 0,
        (df_matriz_alm['Capital Riesgo (S/.)'] / df_matriz_alm['Capital Total (S/.)']) * 100, 0
    )
    
    df_matriz_alm = df_matriz_alm.sort_values(by='Capital Total (S/.)', ascending=False)
    
    df_matriz_view = df_matriz_alm.copy()
    df_matriz_view['Capital Total (S/.)'] = df_matriz_view['Capital Total (S/.)'].map('S/. {:,.2f}'.format)
    df_matriz_view['Capital Activo (S/.)'] = df_matriz_view['Capital Activo (S/.)'].map('S/. {:,.2f}'.format)
    df_matriz_view['Capital Media Rot (S/.)'] = df_matriz_view['Capital Media Rot (S/.)'].map('S/. {:,.2f}'.format)
    df_matriz_view['Capital Riesgo (S/.)'] = df_matriz_view['Capital Riesgo (S/.)'].map('S/. {:,.2f}'.format)
    df_matriz_view['Capital Inmovilizado (S/.)'] = df_matriz_view['Capital Inmovilizado (S/.)'].map('S/. {:,.2f}'.format)
    df_matriz_view['% Inmovilizado (>9M)'] = df_matriz_view['% Inmovilizado (>9M)'].map('{:.1f}%'.format)
    df_matriz_view['% En Riesgo (6-9M)'] = df_matriz_view['% En Riesgo (6-9M)'].map('{:.1f}%'.format)
    
    st.dataframe(df_matriz_view, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# TAB 2: TOP 15s VERTICALES
# ------------------------------------------------------------------------------
with tab_top15:
    st.markdown("<div class='section-header'>TOP 15 SKUs con Mayor Capital Valorizado</div>", unsafe_allow_html=True)
    df_top_sku = df_filtrado.sort_values(by='capital_total', ascending=False).head(15)
    
    if not df_top_sku.empty:
        fig_skus = px.bar(
            df_top_sku, 
            x='capital_total', 
            y='DESCRIPCION', 
            orientation='h',
            text_auto='.2s',
            color='tramo_rotacion', 
            color_discrete_map=colores_tramos
        )
        fig_skus.update_layout(
            yaxis=dict(autorange="reversed", title=""),
            xaxis=dict(title="Capital (S/.)"),
            height=450, 
            legend=dict(title="Tramo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_skus, use_container_width=True)
    else:
        st.info("Sin datos con los filtros aplicados.")
        
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>TOP 15 Familias por Capital</div>", unsafe_allow_html=True)
    df_top_fam = df_filtrado.groupby(['FAMILIA', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    top_fam_list = df_filtrado.groupby('FAMILIA')['capital_total'].sum().nlargest(15).index
    df_top_fam = df_top_fam[df_top_fam['FAMILIA'].isin(top_fam_list)]
    
    if not df_top_fam.empty:
        fig_fam = px.bar(
            df_top_fam, 
            x='capital_total', 
            y='FAMILIA', 
            orientation='h',
            text_auto='.2s',
            color='tramo_rotacion',
            color_discrete_map=colores_tramos
        )
        fig_fam.update_layout(
            yaxis=dict(autorange="reversed", title=""),
            xaxis=dict(title="Capital (S/.)"),
            height=450,
            showlegend=False
        )
        st.plotly_chart(fig_fam, use_container_width=True)
    else:
        st.info("Sin datos de Familias.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>TOP 15 Subfamilias por Capital</div>", unsafe_allow_html=True)
    df_top_sub = df_filtrado.groupby(['SUBFAMILIA', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    top_sub_list = df_filtrado.groupby('SUBFAMILIA')['capital_total'].sum().nlargest(15).index
    df_top_sub = df_top_sub[df_top_sub['SUBFAMILIA'].isin(top_sub_list)]
    
    if not df_top_sub.empty:
        fig_sub = px.bar(
            df_top_sub, 
            x='capital_total', 
            y='SUBFAMILIA', 
            orientation='h',
            text_auto='.2s',
            color='tramo_rotacion',
            color_discrete_map=colores_tramos
        )
        fig_sub.update_layout(
            yaxis=dict(autorange="reversed", title=""),
            xaxis=dict(title="Capital (S/.)"),
            height=450,
            showlegend=False
        )
        st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.info("Sin datos de Subfamilias.")

# ------------------------------------------------------------------------------
# TAB 3: TABLA DETALLADA COMPLETA DE SKUs
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown("<div class='section-header'>Listado Completo de SKUs POR TIEMPO INMOVILIZADO</div>", unsafe_allow_html=True)
    
    if not df_filtrado.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='INMOVILIZADOS_DETALLE')
        
        st.download_button(
            label="📥 Descargar Reporte Completo en Excel (.XLSX)",
            data=output.getvalue(),
            file_name=f"Reporte_Inmovilizados_Gaps_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_tabla = df_filtrado.copy()
    df_tabla_view = df_tabla[[
        'CODIGO', 'DESCRIPCION', 'ALMACEN', 'FAMILIA', 'SUBFAMILIA', 
        'STOCK', 'COSTO', 'capital_total', 'tramo_rotacion', 'dias_inactivo_hoy', 'max_gap_historico'
    ]].rename(columns={
        'CODIGO': 'SKU / Código',
        'DESCRIPCION': 'Descripción del Producto',
        'ALMACEN': 'Almacén',
        'FAMILIA': 'Familia',
        'SUBFAMILIA': 'Subfamilia',
        'STOCK': 'Stock Físico',
        'COSTO': 'Costo U. (S/.)',
        'capital_total': 'Capital Total (S/.)',
        'tramo_rotacion': 'Rotación',
        'dias_inactivo_hoy': 'Días Inactivo',
        'max_gap_historico': 'Días Máximos sin Salidas'
    }).sort_values(by='Capital Total (S/.)', ascending=False)
    
    df_tabla_view['Stock Físico'] = df_tabla_view['Stock Físico'].map('{:,.2f}'.format)
    df_tabla_view['Costo U. (S/.)'] = df_tabla_view['Costo U. (S/.)'].map('S/. {:,.2f}'.format)
    df_tabla_view['Capital Total (S/.)'] = df_tabla_view['Capital Total (S/.)'].map('S/. {:,.2f}'.format)
    
    st.dataframe(df_tabla_view, use_container_width=True, hide_index=True)