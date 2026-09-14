import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import unicodedata
import io

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS UI/UX
# ==============================================================================
st.set_page_config(
    layout="wide", 
    page_title="KPI 5 - DÍAS DE COBERTURA / INVENTARIO",
    page_icon="⏱️"
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
# 1. LECTURA Y DESCENTUACIÓN COMPLETA DE COLUMNAS
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

def desacentuar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")

df_stock.columns = [desacentuar_texto(c) for c in df_stock.columns]
df_mov.columns = [desacentuar_texto(c) for c in df_mov.columns]

# Verificación de columnas esenciales
if 'DESCRIPCION' not in df_stock.columns:
    cols_desc = [c for c in df_stock.columns if 'DESC' in c or 'MAT' in c or 'PROD' in c]
    df_stock['DESCRIPCION'] = df_stock[cols_desc[0]] if cols_desc else 'SIN DESCRIPCION'

if 'CODIGO' not in df_stock.columns: df_stock['CODIGO'] = 'SIN CODIGO'
if 'ALMACEN' not in df_stock.columns: df_stock['ALMACEN'] = 'GENERAL'
if 'FAMILIA' not in df_stock.columns: df_stock['FAMILIA'] = 'SIN CLASIFICAR'
if 'STOCK' not in df_stock.columns: df_stock['STOCK'] = 0.0
if 'COSTO' not in df_stock.columns: df_stock['COSTO'] = 0.0

df_stock['STOCK'] = pd.to_numeric(df_stock['STOCK'], errors='coerce').fillna(0.0)
df_stock = df_stock[df_stock['STOCK'] > 0].copy()

# ==============================================================================
# 2. CONTROLES Y FILTROS EN INTERFAZ
# ==============================================================================
st.title("KPI 5 - DÍAS DE COBERTURA DE INVENTARIO (DIO)")
st.markdown("---")

tramos_ordenados = [
    "Bajo Stock (< 30d / 1m)",
    "Óptimo Importación (30-180d / 1-6m)",
    "Sobrestock (181-270d / 6-9m)",
    "Exceso Crítico (> 270d / > 9m)",
    "Sin Consumo (Infinita)"
]

c_fil1, c_fil2, c_fil3, c_fil4 = st.columns(4)

lista_almacenes = ["TODOS"] + sorted([str(x) for x in df_stock['ALMACEN'].unique() if pd.notna(x) and str(x) != 'NAN'])
lista_familias = ["TODAS"] + sorted([str(x) for x in df_stock['FAMILIA'].unique() if pd.notna(x) and str(x) != 'NAN'])

with c_fil1: almacen_filtro = st.selectbox("Almacén", lista_almacenes)
with c_fil2: familia_filtro = st.selectbox("Familia", lista_familias)
with c_fil3: ventana_dias = st.selectbox("Ventana Consumo Histórico", [30, 60, 90, 180, 365], index=4)
with c_fil4: tramo_cobertura_filtro = st.selectbox("Tramo Cobertura", ["TODOS"] + tramos_ordenados)

# ==============================================================================
# 3. LÓGICA DE DÍAS DE COBERTURA
# ==============================================================================
df_mov['es_salida'] = df_mov['TIPO_MOVIMIENTO'].astype(str).str.contains('NS|SALIDA|CONSUMO', regex=True, na=False)

fecha_max_mov = df_mov['FECHA'].max() if not df_mov['FECHA'].dropna().empty else pd.Timestamp(datetime.date.today())
fecha_inicio_ventana = fecha_max_mov - pd.Timedelta(days=ventana_dias)

df_salidas_vent = df_mov[
    df_mov['es_salida'] & 
    (df_mov['FECHA'] >= fecha_inicio_ventana) & 
    (df_mov['FECHA'] <= fecha_max_mov)
].copy()

consumo_agrupado = df_salidas_vent.groupby(['CODIGO', 'ALMACEN'])['CANTIDAD'].sum().reset_index()
consumo_agrupado.rename(columns={'CANTIDAD': 'CANTIDAD_CONSUMIDA'}, inplace=True)

df_cob = pd.merge(
    df_stock, 
    consumo_agrupado, 
    on=['CODIGO', 'ALMACEN'], 
    how='left'
)

df_cob['CANTIDAD_CONSUMIDA'] = df_cob['CANTIDAD_CONSUMIDA'].fillna(0.0)
df_cob['CONSUMO_DIARIO_UNID'] = df_cob['CANTIDAD_CONSUMIDA'] / ventana_dias

df_cob['DIAS_COBERTURA'] = np.where(
    df_cob['CONSUMO_DIARIO_UNID'] > 0,
    df_cob['STOCK'] / df_cob['CONSUMO_DIARIO_UNID'],
    9999.0
)

# Clasificación con nueva escala (6 a 9 meses = 181 a 270 días)
condiciones = [
    df_cob['DIAS_COBERTURA'] < 30,
    (df_cob['DIAS_COBERTURA'] >= 30) & (df_cob['DIAS_COBERTURA'] <= 180),
    (df_cob['DIAS_COBERTURA'] > 180) & (df_cob['DIAS_COBERTURA'] <= 270),
    (df_cob['DIAS_COBERTURA'] > 270) & (df_cob['DIAS_COBERTURA'] < 9999)
]
elecciones = [
    "Bajo Stock (< 30d / 1m)",
    "Óptimo Importación (30-180d / 1-6m)",
    "Sobrestock (181-270d / 6-9m)",
    "Exceso Crítico (> 270d / > 9m)"
]
df_cob['tramo_cobertura'] = np.select(condiciones, elecciones, default="Sin Consumo (Infinita)")
df_cob['CAPITAL_TOTAL'] = df_cob['STOCK'] * df_cob['COSTO']
df_cob['CONSUMO_VALORIZADO'] = df_cob['CANTIDAD_CONSUMIDA'] * df_cob['COSTO']

# Filtros dinámicos
df_filtrado = df_cob.copy()
if almacen_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['ALMACEN'] == almacen_filtro]
if familia_filtro != "TODAS": 
    df_filtrado = df_filtrado[df_filtrado['FAMILIA'] == familia_filtro]
if tramo_cobertura_filtro != "TODOS": 
    df_filtrado = df_filtrado[df_filtrado['tramo_cobertura'] == tramo_cobertura_filtro]

# ==============================================================================
# 4. METRICAS / KPIS
# ==============================================================================
v_capital_tot = df_filtrado['CAPITAL_TOTAL'].sum()
v_consumo_tot = df_filtrado['CONSUMO_VALORIZADO'].sum()
v_consumo_diario_tot = v_consumo_tot / ventana_dias

dias_cobertura_global = (v_capital_tot / v_consumo_diario_tot) if v_consumo_diario_tot > 0 else 9999

v_critico = df_filtrado[df_filtrado['tramo_cobertura'].isin(["Exceso Crítico (> 270d / > 9m)", "Sin Consumo (Infinita)"])]['CAPITAL_TOTAL'].sum()
v_bajo_stock = df_filtrado[df_filtrado['tramo_cobertura'] == "Bajo Stock (< 30d / 1m)"]['CAPITAL_TOTAL'].sum()

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Capital Filtrado</div>
        <div class='kpi-value'>S/. {v_capital_tot:,.2f}</div>
        <div style='font-size:0.8rem; color:#64748b;'>{len(df_filtrado):,} SKUs</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    cob_text = f"{dias_cobertura_global:.0f} Días" if dias_cobertura_global < 9999 else "Sin Consumo"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Cobertura Global Promedio</div>
        <div class='kpi-value' style='color:#0284c7;'>{cob_text}</div>
        <div style='font-size:0.8rem; color:#64748b;'>Base ventana {ventana_dias} días</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Bajo Stock (< 30d)</div>
        <div class='kpi-value' style='color:#dc2626;'>S/. {v_bajo_stock:,.2f}</div>
        <div style='font-size:0.8rem; color:#991b1b;'>Riesgo de quiebre (< 1 mes)</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Exceso Crítico (> 9m)</div>
        <div class='kpi-value' style='color:#b91c1c;'>S/. {v_critico:,.2f}</div>
        <div style='font-size:0.8rem; color:#be123c;'>Sobre 9 meses o sin consumo</div>
    </div>
    """, unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Consumo Diario Valorizado</div>
        <div class='kpi-value' style='color:#10b981;'>S/. {v_consumo_diario_tot:,.2f}</div>
        <div style='font-size:0.8rem; color:#047857;'>Salida media diaria</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 5. TABLAS Y RESULTADOS
# ==============================================================================
colores_cobertura = {
    "Bajo Stock (< 30d / 1m)": "#dc2626",
    "Óptimo Importación (30-180d / 1-6m)": "#10b981",
    "Sobrestock (181-270d / 6-9m)": "#f59e0b",
    "Exceso Crítico (> 270d / > 9m)": "#f97316",
    "Sin Consumo (Infinita)": "#7f1d1d"
}

tab_graf, tab_matriz, tab_detalle = st.tabs([
    "DISTRIBUCIÓN DE COBERTURA", 
    "RESUMEN POR FAMILIA", 
    "DETALLE COMPLETO POR SKU"
])

with tab_graf:
    st.markdown("<div class='section-header'>CAPITAL VALORIZADO POR TRAMO DE COBERTURA</div>", unsafe_allow_html=True)
    df_chart = df_filtrado.groupby('tramo_cobertura')['CAPITAL_TOTAL'].sum().reset_index()
    
    if not df_chart.empty:
        fig_bar = px.bar(
            df_chart, 
            x='tramo_cobertura', 
            y='CAPITAL_TOTAL', 
            color='tramo_cobertura',
            text_auto='.2s',
            color_discrete_map=colores_cobertura,
            category_orders={'tramo_cobertura': tramos_ordenados}
        )
        fig_bar.update_layout(xaxis_title="", yaxis_title="Capital Valorizado (S/.)", height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

with tab_matriz:
    st.markdown("<div class='section-header'>MATRIZ DE COBERTURA POR FAMILIA</div>", unsafe_allow_html=True)
    
    df_fam = df_filtrado.groupby('FAMILIA').agg(
        Capital_Total=('CAPITAL_TOTAL', 'sum'),
        SKUs=('CODIGO', 'nunique'),
        Consumo_Diario=('CONSUMO_VALORIZADO', lambda x: x.sum() / ventana_dias)
    ).reset_index()
    
    df_fam['Dias_Cobertura_Promedio'] = np.where(
        df_fam['Consumo_Diario'] > 0,
        df_fam['Capital_Total'] / df_fam['Consumo_Diario'],
        9999.0
    )
    
    df_fam['Dias_Cobertura_Promedio_View'] = df_fam['Dias_Cobertura_Promedio'].map(
        lambda x: f"{x:.0f} Días" if x < 9999 else "Sin Consumo"
    )
    df_fam['Capital_Total'] = df_fam['Capital_Total'].map('S/. {:,.2f}'.format)
    df_fam['Consumo_Diario'] = df_fam['Consumo_Diario'].map('S/. {:,.2f}'.format)
    
    st.dataframe(
        df_fam[['FAMILIA', 'SKUs', 'Capital_Total', 'Consumo_Diario', 'Dias_Cobertura_Promedio_View']]
        .rename(columns={'Dias_Cobertura_Promedio_View': 'Días de Cobertura Ponderado'}),
        use_container_width=True, 
        hide_index=True
    )

with tab_detalle:
    st.markdown("<div class='section-header'>LISTADO DETALLADO DE COBERTURA POR SKU</div>", unsafe_allow_html=True)
    
    if not df_filtrado.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='COBERTURA_DETALLE')
        
        st.download_button(
            label="📥 Descargar Reporte Completo de Cobertura (.XLSX)",
            data=output.getvalue(),
            file_name=f"Reporte_Dias_Cobertura_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_view = df_filtrado[[
        'CODIGO', 'DESCRIPCION', 'ALMACEN', 'FAMILIA', 'STOCK', 'COSTO', 
        'CAPITAL_TOTAL', 'CANTIDAD_CONSUMIDA', 'CONSUMO_DIARIO_UNID', 'DIAS_COBERTURA', 'tramo_cobertura'
    ]].copy()
    
    df_view['Días Cobertura'] = df_view['DIAS_COBERTURA'].map(lambda x: f"{x:.1f}" if x < 9999 else "Sin Consumo")
    df_view['Stock Físico'] = df_view['STOCK'].map('{:,.2f}'.format)
    df_view['Costo U. (S/.)'] = df_view['COSTO'].map('S/. {:,.2f}'.format)
    df_view['Capital Total (S/.)'] = df_view['CAPITAL_TOTAL'].map('S/. {:,.2f}'.format)
    df_view['Consumo Diario (U)'] = df_view['CONSUMO_DIARIO_UNID'].map('{:,.2f}'.format)
    
    df_view_final = df_view[[
        'CODIGO', 'DESCRIPCION', 'ALMACEN', 'FAMILIA', 'Stock Físico', 
        'Costo U. (S/.)', 'Capital Total (S/.)', 'Consumo Diario (U)', 'Días Cobertura', 'tramo_cobertura'
    ]].rename(columns={
        'CODIGO': 'SKU', 'DESCRIPCION': 'Descripción', 'tramo_cobertura': 'Estado Cobertura'
    }).sort_values(by='Capital Total (S/.)', ascending=False)
    
    st.dataframe(df_view_final, use_container_width=True, hide_index=True)