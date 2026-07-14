import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(layout="wide")

# 🔥 SOLUCIÓN AL BUG DE RENDIMIENTO: Incrementar el límite máximo de celdas configuradas para Pandas Styler
pd.set_option("styler.render.max_elements", 500000)

# ==============================================================================
# 1. VALIDACIÓN DE CONTENEDORES EN MEMORIA
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

# Copias limpias de los DataFrames en session_state
df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

st.title("Módulo de Kardex Analítico Dinámico y Auditoría de Balances")
st.markdown("---")

# ==============================================================================
# 2. ESTANDARIZACIÓN INICIAL Y BLINDAJE DE COLUMNAS (Alineado con tus módulos)
# ==============================================================================
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()

# Detectar dinámicamente si es 'Descripcion' o 'Item'
nombre_col_desc = 'Descripcion' if 'Descripcion' in df_stock.columns else ('Item' if 'Item' in df_stock.columns else 'Descripcion')
if nombre_col_desc not in df_stock.columns:
    df_stock['Descripcion'] = 'PRODUCTO SIN DETALLE'
    nombre_col_desc = 'Descripcion'

if 'SubFamilia' not in df_stock.columns:
    df_stock['SubFamilia'] = 'GENERAL'

# Vectorización de ingresos (NI) y salidas (NS) en movimientos
df_mov['Tipo_Movimiento'] = df_mov['Tipo_Movimiento'].astype(str).str.strip().str.upper()
df_mov['Entradas'] = 0.0
df_mov.loc[df_mov['Tipo_Movimiento'] == 'NI', 'Entradas'] = df_mov['Cantidad']

df_mov['Salidas'] = 0.0
df_mov.loc[df_mov['Tipo_Movimiento'] == 'NS', 'Salidas'] = df_mov['Cantidad']

# Mapeos maestros rápidos desde df_stock para enriquecer el Kardex
desc_map = df_stock.set_index('Codigo')[nombre_col_desc].to_dict()
costo_map = df_stock.set_index('Codigo')['Costo'].to_dict()
fam_map = df_stock.set_index('Codigo')['Familia'].to_dict()
subfam_map = df_stock.set_index('Codigo')['SubFamilia'].to_dict()

# Línea de tiempo estricta solicitada (Desde Octubre)
meses_historicos = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]

# ==============================================================================
# 3. FILTROS JERÁRQUICOS EN LA BARRA LATERAL
# ==============================================================================
st.sidebar.header("Filtros de Segmentación Kardex")

list_alm = ["TODOS"] + sorted(df_stock['Almacen'].unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtro de Almacenamiento", list_alm)

df_s_f = df_stock.copy()
df_m_f = df_mov.copy()

if filtro_alm != "TODOS":
    df_s_f = df_s_f[df_s_f['Almacen'] == filtro_alm]
    df_m_f = df_m_f[df_m_f['Almacen'] == filtro_alm]

list_fam = ["TODOS"] + sorted(df_s_f['Familia'].unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtro de Familia", list_fam)

if filtro_fam != "TODOS":
    df_s_f = df_s_f[df_s_f['Familia'] == filtro_fam]
    codigos_filtrados = df_s_f['Codigo'].unique()
    df_m_f = df_m_f[df_m_f['Codigo'].isin(codigos_filtrados)]

list_subfam = ["TODOS"] + sorted(df_s_f['SubFamilia'].unique().tolist())
filtro_subfam = st.sidebar.selectbox("Filtro de Subfamilia", list_subfam)

if filtro_subfam != "TODOS":
    df_s_f = df_s_f[df_s_f['SubFamilia'] == filtro_subfam]
    codigos_filtrados = df_s_f['Codigo'].unique()
    df_m_f = df_m_f[df_m_f['Codigo'].isin(codigos_filtrados)]

# ==============================================================================
# 4. PROCESAMIENTO VECTORIZADO DEL KARDEX INTEGRADO (Restringido cronológicamente)
# ==============================================================================
df_kardex_base = df_m_f[df_m_f['Tipo_Movimiento'].isin(['NI', 'NS'])].copy()
df_kardex_base = df_kardex_base[df_kardex_base['Mes_Mov'].isin(meses_historicos)].copy()

# Enriquecer columnas usando los mapas del maestro de stock
df_kardex_base['Descripcion'] = df_kardex_base['Codigo'].map(desc_map).fillna("ARTÍCULO DESCONOCIDO")
df_kardex_base['Costo_Unitario'] = df_kardex_base['Codigo'].map(costo_map).fillna(0.0)
df_kardex_base['Familia'] = df_kardex_base['Codigo'].map(fam_map).fillna("SIN FAMILIA")
df_kardex_base['SubFamilia'] = df_kardex_base['Codigo'].map(subfam_map).fillna("GENERAL")

df_kardex_base['Valor_Ingreso_Soles'] = df_kardex_base['Entradas'] * df_kardex_base['Costo_Unitario']
df_kardex_base['Valor_Salida_Soles'] = df_kardex_base['Salidas'] * df_kardex_base['Costo_Unitario']

if 'Fecha' in df_kardex_base.columns:
    df_kardex_base['Fecha'] = pd.to_datetime(df_kardex_base['Fecha'], errors='coerce')
    df_kardex_base = df_kardex_base.sort_values(by='Fecha', ascending=False)

# ==============================================================================
# 5. CONSULTOR INDIVIDUAL POR SKU / DESCRIPCIÓN REQUERIDO
# ==============================================================================
st.subheader("🎯 Buscador Avanzado de Trazabilidad por SKU / Código")
codigos_disponibles = sorted(df_s_f['Codigo'].unique().tolist())
opciones_buscador = [f"{cod} - {desc_map.get(cod, '')}" for cod in codigos_disponibles]

if opciones_buscador:
    seleccion_sku_str = st.selectbox("Escriba o seleccione un artículo para ver su Kardex detallado:", opciones_buscador)
    sku_seleccionado = seleccion_sku_str.split(" - ")[0]
    
    # Filtrar datos exclusivos para la auditoría de este SKU
    df_kardex_sku = df_kardex_base[df_kardex_base['Codigo'] == sku_seleccionado].copy()
    stock_actual_sku = df_s_f[df_s_f['Codigo'] == sku_seleccionado]['Stock'].sum()
    costo_sku = costo_map.get(sku_seleccionado, 0.0)
    
    # ---- Reconstrucción Inversa de Saldos Mensuales ----
    saldos_cronologicos = []
    stock_iterativo = stock_actual_sku
    
    # Iterar en reversa desde el mes más nuevo al más antiguo
    for mes in reversed(meses_historicos):
        df_mes_sku = df_kardex_sku[df_kardex_sku['Mes_Mov'] == mes]
        entradas_mes = df_mes_sku['Entradas'].sum()
        salidas_mes = df_mes_sku['Salidas'].sum()
        
        # Al ir hacia atrás: el stock inicial del mes es el final menos entradas más salidas
        val_cierre = stock_iterativo * costo_sku
        
        saldos_cronologicos.append({
            "Mes": mes,
            "Ingresos (Cant)": entradas_mes,
            "Salidas (Cant)": salidas_mes,
            "Stock Cierre": stock_iterativo,
            "Valor Cierre": val_cierre
        })
        stock_iterativo = max(0.0, stock_iterativo - entradas_mes + salidas_mes)
    
    # Volver a ordenar cronológicamente de Octubre a Julio
    df_balances_mes = pd.DataFrame(saldos_cronologicos)[::-1].reset_index(drop=True)
    df_balances_mes['Variación Absoluta'] = df_balances_mes['Valor Cierre'].diff().fillna(0)
    
    # Render de Variaciones y Flechas Dinámicas
    tabla_variacion_data = []
    for i, r in df_balances_mes.iterrows():
        if i == 0:
            var_texto = "-"
        else:
            flecha = "↗" if r['Variación Absoluta'] >= 0 else "↘"
            color_f = "Monto Mayor" if r['Variación Absoluta'] >= 0 else "Disminuyó"
            var_texto = f"{flecha} S/. {abs(r['Variación Absoluta']):,.2f} ({color_f})"
            
        tabla_variacion_data.append({
            "MES PERIODO": r['Mes'],
            "INGRESOS NI (UM)": f"{r['Ingresos (Cant)']:,.0f}",
            "SALIDAS NS (UM)": f"{r['Salidas (Cant)']:,.0f}",
            "STOCK CIERRE (UM)": f"{r['Stock Cierre']:,.0f}",
            "CIERRE MONETARIO (S/.)": f"S/. {r['Valor Cierre']:,.2f}",
            "COMPORTAMIENTO CAPITAL (MoM)": var_texto
        })
    
    # Despliegue de la Auditoría Financiera del SKU
    st.markdown(f"**Análisis de Maduración y Cierres Mensuales para el SKU:** `{sku_seleccionado}`")
    st.dataframe(pd.DataFrame(tabla_variacion_data), use_container_width=True, hide_index=True)

st.write("---")

# ==============================================================================
# 6. GRÁFICOS ANALÍTICOS DE COMPORTAMIENTO MENSUAL GLOBAL (Desde Octubre)
# ==============================================================================
st.subheader("📊 Análisis de Flujos Consolidados del Sistema")
cg1, cg2 = st.columns(2)

with cg1:
    st.subheader("Flujo Mensual de Movimientos Físicos (UM)")
    if not df_kardex_base.empty:
        df_g_mes = df_kardex_base.groupby('Mes_Mov')[['Entradas', 'Salidas']].sum().reindex(meses_historicos).fillna(0).reset_index()
        fig_cronologico = go.Figure()
        fig_cronologico.add_trace(go.Bar(x=df_g_mes['Mes_Mov'], y=df_g_mes['Entradas'], name="Ingresos (NI)", marker_color="#10b981"))
        fig_cronologico.add_trace(go.Bar(x=df_g_mes['Mes_Mov'], y=df_g_mes['Salidas'], name="Salidas (NS)", marker_color="#ef4444"))
        fig_cronologico.update_layout(barmode='group', plot_bgcolor='white', margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_cronologico, use_container_width=True)

with cg2:
    st.subheader("Balance Valorizado Mensual (S/.)")
    if not df_kardex_base.empty:
        df_g_mes_val = df_kardex_base.groupby('Mes_Mov')[['Valor_Ingreso_Soles', 'Valor_Salida_Soles']].sum().reindex(meses_historicos).fillna(0).reset_index()
        fig_alm_bal = go.Figure()
        fig_alm_bal.add_trace(go.Bar(x=df_g_mes_val['Mes_Mov'], y=df_g_mes_val['Valor_Ingreso_Soles'], name="S/. Ingresos (NI)", marker_color="#0d9488"))
        fig_alm_bal.add_trace(go.Bar(x=df_g_mes_val['Mes_Mov'], y=df_g_mes_val['Valor_Salida_Soles'], name="S/. Salidas (NS)", marker_color="#f59e0b"))
        fig_alm_bal.update_layout(barmode='group', plot_bgcolor='white', margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_alm_bal, use_container_width=True)

# ==============================================================================
# 7. MATRIZ DE TRAZABILIDAD DETALLADA (TABLA KARDEX COMPLETA)
# ==============================================================================
st.write("---")
st.subheader("📋 Registro Histórico General de Transacciones")

columnas_vista = [
    'Fecha', 'Mes_Mov', 'Almacen', 'Codigo', 'Descripcion', 'Familia',
    'Tipo_Movimiento', 'Entradas', 'Salidas', 'Costo_Unitario', 'Valor_Ingreso_Soles', 'Valor_Salida_Soles'
]

columnas_validas = [c for c in columnas_vista if c in df_kardex_base.columns]
df_tabla_kardex = df_kardex_base[columnas_validas].copy()

# Renderizado seguro: Usamos el dataframe directo sin .style para evitar el desborde de memoria de Styler en grandes volúmenes
st.dataframe(df_tabla_kardex, use_container_width=True, hide_index=True)

# Exportador táctico a Excel
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_tabla_kardex.to_excel(writer, index=False, sheet_name='Kardex_Analitico')
processed_data = output.getvalue()

st.download_button(
    label="📥 Descargar Reporte de Kardex Completo a Excel",
    data=processed_data,
    file_name="Kardex_Analitico_General.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)