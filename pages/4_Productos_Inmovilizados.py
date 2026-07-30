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
    page_title="KPI 4 - CODIGOS INMOVILIZADOS",
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
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.4rem;
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
# FUNCIONES AUXILIARES VECTORIZADAS
# ==============================================================================
def buscar_columna(df, opciones_posibles, defecto=""):
    for op in opciones_posibles:
        for col in df.columns:
            col_norm = str(col).lower().replace('_', ' ').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').strip()
            if op.lower() in col_norm:
                return col
    return defecto

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

# ==============================================================================
# 1. CARGA Y LIMPIEZA DE DATOS (SOLO STOCK > 0)
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock_raw = st.session_state['df_stock']
df_mov_raw = st.session_state['df_mov']

col_cod_s = buscar_columna(df_stock_raw, ['codigo', 'item', 'sku', 'articulo'])
col_desc_s = buscar_columna(df_stock_raw, ['descripcion', 'detalle', 'nombre', 'producto'])
col_alm_s = buscar_columna(df_stock_raw, ['almacen', 'deposito', 'nomalmacen'])
col_fam_s = buscar_columna(df_stock_raw, ['familia', 'linea', 'categoria'])
col_subfam_s = buscar_columna(df_stock_raw, ['subfamilia', 'sublinea', 'subcategoria'])
col_stk_s = buscar_columna(df_stock_raw, ['stock', 'cantidad', 'cant', 'saldo'])
col_costo_s = buscar_columna(df_stock_raw, ['costo', 'precio', 'val unit'])

df_stock_base = pd.DataFrame({
    'Codigo': df_stock_raw[col_cod_s].astype(str).str.strip() if col_cod_s else df_stock_raw.iloc[:, 0].astype(str).str.strip(),
    'Descripcion': df_stock_raw[col_desc_s].astype(str).str.strip() if col_desc_s else 'SIN DESCRIPCIÓN',
    'Almacen': df_stock_raw[col_alm_s].astype(str).str.strip().str.upper() if col_alm_s else 'GENERAL',
    'Familia': df_stock_raw[col_fam_s].astype(str).str.strip().str.upper() if col_fam_s else 'GENERAL',
    'SubFamilia': df_stock_raw[col_subfam_s].astype(str).str.strip().str.upper() if col_subfam_s else 'GENERAL',
    'Stock': sanitizar_serie_numerica(df_stock_raw[col_stk_s]) if col_stk_s else 0.0,
    'Costo': sanitizar_serie_numerica(df_stock_raw[col_costo_s]) if col_costo_s else 0.0
})

# FILTRO CLAVE: Únicamente considerar SKUs con Stock Físico > 0
df_stock = df_stock_base[df_stock_base['Stock'] > 0].copy()

col_cod_m = buscar_columna(df_mov_raw, ['codigo', 'item', 'sku', 'articulo'])
col_tipo_m = buscar_columna(df_mov_raw, ['tipo movimiento', 'tipo doc', 'documento', 'movimiento', 'tipo'])
col_trans_m = buscar_columna(df_mov_raw, ['transaccion', 'trans', 'tipo transaccion'])
col_fec_m = buscar_columna(df_mov_raw, ['fecha', 'fec doc', 'fec mov'])

df_mov = pd.DataFrame({
    'Codigo': df_mov_raw[col_cod_m].astype(str).str.strip() if col_cod_m else '',
    'Tipo_Movimiento': df_mov_raw[col_tipo_m].astype(str).str.strip().str.upper() if col_tipo_m else '',
    'Transaccion': df_mov_raw[col_trans_m].astype(str).str.strip().str.upper() if col_trans_m else '',
    'Fecha': pd.to_datetime(df_mov_raw[col_fec_m], errors='coerce') if col_fec_m else pd.NaT
})

# ==============================================================================
# 2. LOGICA REGLA TD EN MATERIA PRIMA VS NI/NS
# ==============================================================================
ref_almacen = df_stock.drop_duplicates('Codigo').set_index('Codigo')['Almacen'].to_dict()
ref_familia = df_stock.drop_duplicates('Codigo').set_index('Codigo')['Familia'].to_dict()

df_mov['Almacen_Ref'] = df_mov['Codigo'].map(ref_almacen).fillna('')
df_mov['Familia_Ref'] = df_mov['Codigo'].map(ref_familia).fillna('')

df_mov['es_mp'] = (
    df_mov['Almacen_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False) |
    df_mov['Familia_Ref'].str.contains('MATERIA|MP|PRIMA', regex=True, na=False)
)

df_mov['es_ingreso'] = df_mov['Tipo_Movimiento'].str.contains('NI|INGRESO', regex=True, na=False)

salida_mp = df_mov['es_mp'] & df_mov['Transaccion'].str.contains('TD', regex=True, na=False)
salida_otros = (~df_mov['es_mp']) & df_mov['Tipo_Movimiento'].str.contains('NS|SALIDA', regex=True, na=False)
df_mov['es_salida'] = salida_mp | salida_otros

# ==============================================================================
# 3. MOTOR VECTORIZADO DE CALCULOS DE GAPS
# ==============================================================================
@st.cache_data(show_spinner=False)
def calcular_gaps_vectorizado(df_s, df_m):
    base = df_s.copy()
    fecha_hoy = pd.Timestamp(datetime.date.today())
    
    m_valid = df_m[(df_m['es_ingreso'] | df_m['es_salida']) & df_m['Fecha'].notnull()]
    
    if m_valid.empty:
        base['f_ult_ingreso'] = pd.NaT
        base['f_ult_salida'] = pd.NaT
        base['dias_inactivo_hoy'] = 999
        base['max_gap_historico'] = 0
        base['gap_efectivo'] = 999
        base['es_espejismo'] = False
    else:
        s_ingresos = m_valid[m_valid['es_ingreso']].groupby('Codigo')['Fecha'].max()
        s_salidas = m_valid[m_valid['es_salida']].groupby('Codigo')['Fecha'].max()
        
        m_sorted = m_valid.sort_values(['Codigo', 'Fecha'])
        m_sorted['gap'] = m_sorted.groupby('Codigo')['Fecha'].diff().dt.days
        s_max_gap = m_sorted.groupby('Codigo')['gap'].max().fillna(0)
        
        base['f_ult_ingreso'] = base['Codigo'].map(s_ingresos)
        base['f_ult_salida'] = base['Codigo'].map(s_salidas)
        base['max_gap_historico'] = base['Codigo'].map(s_max_gap).fillna(0)
        
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
    base['capital_total'] = base['Stock'] * base['Costo']
    
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

lista_almacenes = ["TODOS"] + sorted([x for x in df_datos_maestros['Almacen'].unique() if x and str(x) != 'nan'])
lista_familias = ["TODAS"] + sorted([x for x in df_datos_maestros['Familia'].unique() if x and str(x) != 'nan'])

f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1: almacen_filtro = st.selectbox("Almacén", lista_almacenes)
with f_col2: familia_filtro = st.selectbox("Familia", lista_familias)

df_prev_sub = df_datos_maestros.copy()
if familia_filtro != "TODAS": 
    df_prev_sub = df_prev_sub[df_prev_sub['Familia'] == familia_filtro]
lista_subfamilias = ["TODAS"] + sorted([x for x in df_prev_sub['SubFamilia'].unique() if x and str(x) != 'nan'])

with f_col3: subfamilia_filtro = st.selectbox("Subfamilia", lista_subfamilias)
with f_col4: tramo_filtro = st.selectbox("Rotación", ["TODOS"] + orden_tramos)

# Aplicar filtros
df_filtrado = df_datos_maestros.copy()
if almacen_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['Almacen'] == almacen_filtro]
if familia_filtro != "TODAS": 
    df_filtrado = df_filtrado[df_filtrado['Familia'] == familia_filtro]
if subfamilia_filtro != "TODAS": 
    df_filtrado = df_filtrado[df_filtrado['SubFamilia'] == subfamilia_filtro]
if tramo_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['tramo_rotacion'] == tramo_filtro]

# ==============================================================================
# 5. KPIS EJECUTIVOS
# ==============================================================================
v_total = df_filtrado['capital_total'].sum()
cant_skus = len(df_filtrado)
v_critico = df_filtrado[df_filtrado['tramo_rotacion'] == '9 a Más Meses (Inmovilizado Crítico)']['capital_total'].sum()
v_riesgo = df_filtrado[df_filtrado['tramo_rotacion'] == '6 a 9 Meses (Rotación Baja / Riesgo)']['capital_total'].sum()
pct_critico = (v_critico / v_total * 100) if v_total > 0 else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Capital Total Filtrado</div>
        <div class='kpi-value'>S/. {v_total:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Inmovilizado Crítico (> 9 Meses)</div>
        <div class='kpi-value' style='color:#b91c1c;'>S/. {v_critico:,.2f}</div>
        <div style='font-size:0.8rem; color:#e11d48;'>{pct_critico:.1f}% del Capital Actual</div>
    </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Riesgo Próximo (6 a 9 Meses)</div>
        <div class='kpi-value' style='color:#f97316;'>S/. {v_riesgo:,.2f}</div>
        <div style='font-size:0.8rem; color:#d97706;'>Futuro inmovilizado si no se liquida</div>
    </div>
    """, unsafe_allow_html=True)
with k4:
    v_activa = df_filtrado[df_filtrado['tramo_rotacion'] == '1 a 3 Meses (Rotación Activa)']['capital_total'].sum()
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Rotación Activa (1-3 Meses)</div>
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
# TAB 1: MATRIZ CONSOLIDADA POR ALMACÉN (SKUS + MONTO S/.)
# ------------------------------------------------------------------------------
with tab_alm:
    st.markdown("<div class='section-header'>ROTACIÓN DE CAPITAL POR ALMACÉN</div>", unsafe_allow_html=True)
    
    df_chart_alm = df_filtrado.groupby(['Almacen', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    
    if not df_chart_alm.empty:
        fig_alm_stacked = px.bar(
            df_chart_alm, 
            y='Almacen', 
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
    
    st.markdown("<div class='section-header'>MATRIZ DETALLA DE INMOVILIZADOS</div>", unsafe_allow_html=True)
    
    # Pivots
    pivot_capital = df_filtrado.pivot_table(
        index='Almacen', columns='tramo_rotacion', values='capital_total', aggfunc='sum', fill_value=0
    ).reindex(columns=orden_tramos, fill_value=0)
    
    pivot_skus = df_filtrado.pivot_table(
        index='Almacen', columns='tramo_rotacion', values='Codigo', aggfunc='nunique', fill_value=0
    ).reindex(columns=orden_tramos, fill_value=0)
    
    skus_totales = df_filtrado.groupby('Almacen')['Codigo'].nunique().rename('SKUs Con Stock (>0)')
    capital_tot = df_filtrado.groupby('Almacen')['capital_total'].sum().rename('Capital Total (S/.)')
    
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
    
    # Porcentajes
    df_matriz_alm['% Inmovilizado (>9M)'] = np.where(
        df_matriz_alm['Capital Total (S/.)'] > 0,
        (df_matriz_alm['Capital Inmovilizado (S/.)'] / df_matriz_alm['Capital Total (S/.)']) * 100, 0
    )
    df_matriz_alm['% En Riesgo (6-9M)'] = np.where(
        df_matriz_alm['Capital Total (S/.)'] > 0,
        (df_matriz_alm['Capital Riesgo (S/.)'] / df_matriz_alm['Capital Total (S/.)']) * 100, 0
    )
    
    df_matriz_alm = df_matriz_alm.sort_values(by='Capital Total (S/.)', ascending=False)
    
    # Formateo eficiente
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
    
    # 1. TOP 15 SKUs
    st.markdown("<div class='section-header'>TOP 15 SKUs con Mayor Capital Valorizado</div>", unsafe_allow_html=True)
    df_top_sku = df_filtrado.sort_values(by='capital_total', ascending=False).head(15)
    
    if not df_top_sku.empty:
        fig_skus = px.bar(
            df_top_sku, 
            x='capital_total', 
            y='Descripcion', 
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

    # 2. TOP 15 FAMILIAS
    st.markdown("<div class='section-header'>TOP 15 Familias por Capital</div>", unsafe_allow_html=True)
    df_top_fam = df_filtrado.groupby(['Familia', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    top_fam_list = df_filtrado.groupby('Familia')['capital_total'].sum().nlargest(15).index
    df_top_fam = df_top_fam[df_top_fam['Familia'].isin(top_fam_list)]
    
    if not df_top_fam.empty:
        fig_fam = px.bar(
            df_top_fam, 
            x='capital_total', 
            y='Familia', 
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

    # 3. TOP 15 SUBFAMILIAS
    st.markdown("<div class='section-header'>TOP 15 Subfamilias por Capital</div>", unsafe_allow_html=True)
    df_top_sub = df_filtrado.groupby(['SubFamilia', 'tramo_rotacion'])['capital_total'].sum().reset_index()
    top_sub_list = df_filtrado.groupby('SubFamilia')['capital_total'].sum().nlargest(15).index
    df_top_sub = df_top_sub[df_top_sub['SubFamilia'].isin(top_sub_list)]
    
    if not df_top_sub.empty:
        fig_sub = px.bar(
            df_top_sub, 
            x='capital_total', 
            y='SubFamilia', 
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
        'Codigo', 'Descripcion', 'Almacen', 'Familia', 'SubFamilia', 
        'Stock', 'Costo', 'capital_total', 'tramo_rotacion', 'dias_inactivo_hoy', 'max_gap_historico'
    ]].rename(columns={
        'Codigo': 'SKU / Código',
        'Descripcion': 'Descripción del Producto',
        'Almacen': 'Almacén',
        'Familia': 'Familia',
        'SubFamilia': 'Subfamilia',
        'Stock': 'Stock Físico',
        'Costo': 'Costo U. (S/.)',
        'capital_total': 'Capital Total (S/.)',
        'tramo_rotacion': 'Roración',
        'dias_inactivo_hoy': 'Días Inactivo',
        'max_gap_historico': 'Dias Maximos sin Salidas'
    }).sort_values(by='Capital Total (S/.)', ascending=False)
    
    # Formateo directo seguro
    df_tabla_view['Stock Físico'] = df_tabla_view['Stock Físico'].map('{:,.2f}'.format)
    df_tabla_view['Costo U. (S/.)'] = df_tabla_view['Costo U. (S/.)'].map('S/. {:,.2f}'.format)
    df_tabla_view['Capital Total (S/.)'] = df_tabla_view['Capital Total (S/.)'].map('S/. {:,.2f}'.format)
    
    st.dataframe(df_tabla_view, use_container_width=True, hide_index=True)