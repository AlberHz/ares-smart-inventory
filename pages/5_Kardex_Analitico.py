import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="KPI 5 - Kardex",
    page_icon="📜",
    layout="wide"
)

# Límite de rendimiento para evitar desbordes
pd.set_option("styler.render.max_elements", 500000)

# ==============================================================================
# 1. VALIDACIÓN Y CARGA DE DATOS
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos en el portal de inicio (app.py) para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

st.title(" KPI 5 -  KARDEX ANALITICO")
st.markdown("---")

# ==============================================================================
# 2. ESTANDARIZACIÓN Y MAPEOS MAESTROS
# ==============================================================================
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()

if 'Familia' not in df_stock.columns:
    df_stock['Familia'] = 'GENERAL'
if 'SubFamilia' not in df_stock.columns:
    df_stock['SubFamilia'] = 'GENERAL'

nombre_col_desc = 'Descripcion' if 'Descripcion' in df_stock.columns else ('Item' if 'Item' in df_stock.columns else 'Descripcion')
if nombre_col_desc not in df_stock.columns:
    df_stock['Descripcion'] = 'PRODUCTO SIN DETALLE'
    nombre_col_desc = 'Descripcion'

# Procesamiento de Movimientos
df_mov['Tipo_Movimiento'] = df_mov['Tipo_Movimiento'].astype(str).str.strip().str.upper()
df_mov['Entradas'] = 0.0
df_mov.loc[df_mov['Tipo_Movimiento'] == 'NI', 'Entradas'] = pd.to_numeric(df_mov['Cantidad'], errors='coerce').fillna(0)

df_mov['Salidas'] = 0.0
df_mov.loc[df_mov['Tipo_Movimiento'] == 'NS', 'Salidas'] = pd.to_numeric(df_mov['Cantidad'], errors='coerce').fillna(0)

# Mapeos por código
desc_map = df_stock.set_index('Codigo')[nombre_col_desc].to_dict()
costo_map = df_stock.set_index('Codigo')['Costo'].to_dict()
fam_map = df_stock.set_index('Codigo')['Familia'].to_dict()
subfam_map = df_stock.set_index('Codigo')['SubFamilia'].to_dict()

# Ventana Temporal
meses_historicos = ["2025-06","2025-07","2025-08","2025-09","2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]

# ==============================================================================
# 3. FILTROS EN BARRA LATERAL
# ==============================================================================
st.sidebar.header("Filtros")

list_alm = ["TODOS"] + sorted(list(df_stock['Almacen'].dropna().unique()))
filtro_alm = st.sidebar.selectbox("Almacén:", list_alm)

df_s_f = df_stock.copy()
df_m_f = df_mov.copy()

if filtro_alm != "TODOS":
    df_s_f = df_s_f[df_s_f['Almacen'] == filtro_alm]
    df_m_f = df_m_f[df_m_f['Almacen'] == filtro_alm]

list_fam = ["TODOS"] + sorted(list(df_s_f['Familia'].dropna().unique()))
filtro_fam = st.sidebar.selectbox("Familia:", list_fam)

if filtro_fam != "TODOS":
    df_s_f = df_s_f[df_s_f['Familia'] == filtro_fam]
    cods = df_s_f['Codigo'].unique()
    df_m_f = df_m_f[df_m_f['Codigo'].isin(cods)]

list_subfam = ["TODOS"] + sorted(list(df_s_f['SubFamilia'].dropna().unique()))
filtro_subfam = st.sidebar.selectbox("SubFamilia:", list_subfam)

if filtro_subfam != "TODOS":
    df_s_f = df_s_f[df_s_f['SubFamilia'] == filtro_subfam]
    cods = df_s_f['Codigo'].unique()
    df_m_f = df_m_f[df_m_f['Codigo'].isin(cods)]

# Base Kardex Filtrada
df_kardex_base = df_m_f[df_m_f['Tipo_Movimiento'].isin(['NI', 'NS'])].copy()
if 'Mes_Mov' in df_kardex_base.columns:
    df_kardex_base = df_kardex_base[df_kardex_base['Mes_Mov'].isin(meses_historicos)].copy()

df_kardex_base['Descripcion'] = df_kardex_base['Codigo'].map(desc_map).fillna("DESCONOCIDO")
df_kardex_base['Costo_Unitario'] = df_kardex_base['Codigo'].map(costo_map).fillna(0.0)
df_kardex_base['Familia'] = df_kardex_base['Codigo'].map(fam_map).fillna("SIN FAMILIA")

df_kardex_base['Valor_Ingreso_Soles'] = df_kardex_base['Entradas'] * df_kardex_base['Costo_Unitario']
df_kardex_base['Valor_Salida_Soles'] = df_kardex_base['Salidas'] * df_kardex_base['Costo_Unitario']

# Valorización del Stock Físico Actual
df_s_f['Valor_Stock_Soles'] = df_s_f['Stock'] * df_s_f['Costo']

# ==============================================================================
# 4. DASHBOARD DE KPIS GENERALES
# ==============================================================================
st.subheader("Métricas Globales")

stock_actual_u = df_s_f['Stock'].sum()
stock_actual_soles = df_s_f['Valor_Stock_Soles'].sum()

tot_entradas_u = df_kardex_base['Entradas'].sum()
tot_entradas_soles = df_kardex_base['Valor_Ingreso_Soles'].sum()

tot_salidas_u = df_kardex_base['Salidas'].sum()
tot_salidas_soles = df_kardex_base['Valor_Salida_Soles'].sum()

# Cálculos de quemado VALORIZADO EN SOLES
ratio_quemado_soles = (tot_salidas_soles / tot_entradas_soles * 100) if tot_entradas_soles > 0 else 0.0
pct_vaciado_soles = (tot_salidas_soles / (stock_actual_soles + tot_salidas_soles) * 100) if (stock_actual_soles + tot_salidas_soles) > 0 else 0.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Stock Actual (Por Quemar)", f"S/. {stock_actual_soles:,.2f}", f"{stock_actual_u:,.0f} U")
k2.metric("Entradas(NI)", f"S/. {tot_entradas_soles:,.2f}", f"{tot_entradas_u:,.0f} U")
k3.metric("Salidas(NS)", f"S/. {tot_salidas_soles:,.2f}", f"{tot_salidas_u:,.0f} U")
k4.metric("Ratio (Salidas / Entradas)", f"{ratio_quemado_soles:.1f}%", "Ideal > 100% (Quema Efectiva)", delta_color="normal" if ratio_quemado_soles >= 100 else "inverse")
k5.metric("% Inventario Quemado", f"{pct_vaciado_soles:.1f}%", "Vaciado del Total Manejado")

st.markdown("---")

# ==============================================================================
# 5. PESTAÑAS DE ANÁLISIS
# ==============================================================================
tab_fam, tab_sku, tab_general = st.tabs([
    "Control de Quemado por Familia", 
    "Kardex Detallado por SKU", 
    "Matriz General de Movimientos"
])

# ------------------------------------------------------------------------------
# TAB 1: CONTROL POR FAMILIA
# ------------------------------------------------------------------------------
with tab_fam:
    st.subheader("Balance de Inventario por Familia (Valorizado en S/. y Unidades)")
    
    # Movimientos agrupados
    df_fam_k = df_kardex_base.groupby('Familia').agg(
        Entradas_U=('Entradas', 'sum'),
        Salidas_U=('Salidas', 'sum'),
        Entradas_Soles=('Valor_Ingreso_Soles', 'sum'),
        Salidas_Soles=('Valor_Salida_Soles', 'sum')
    ).reset_index()
    
    # Stock Maestro agrupado
    df_fam_s = df_s_f.groupby('Familia').agg(
        Stock_Actual_Por_Quemar_U=('Stock', 'sum'),
        Stock_Actual_Por_Quemar_Soles=('Valor_Stock_Soles', 'sum')
    ).reset_index()
    
    df_fam = pd.merge(df_fam_s, df_fam_k, on='Familia', how='outer').fillna(0)
    
    # CORRECCIÓN CLAVE: Fórmulas de Quemado basadas estrictamente en SOLES (S/.)
    df_fam['Ratio_Salida_Entrada_%'] = (df_fam['Salidas_Soles'] / df_fam['Entradas_Soles'] * 100).fillna(0)
    # Evitar infinitos en caso de Entradas = 0 con Salidas > 0
    df_fam.loc[df_fam['Entradas_Soles'] == 0, 'Ratio_Salida_Entrada_%'] = 0.0
    
    df_fam['%_Inventario_Quemado'] = (df_fam['Salidas_Soles'] / (df_fam['Stock_Actual_Por_Quemar_Soles'] + df_fam['Salidas_Soles']) * 100).fillna(0)
    
    cols_order = [
        'Familia', 
        'Stock_Actual_Por_Quemar_U', 'Stock_Actual_Por_Quemar_Soles',
        'Entradas_U', 'Entradas_Soles',
        'Salidas_U', 'Salidas_Soles',
        'Ratio_Salida_Entrada_%', '%_Inventario_Quemado'
    ]
    
    st.write("#### Tabla Consolidada por Familia")
    st.dataframe(
        df_fam[cols_order].sort_values(by='Stock_Actual_Por_Quemar_Soles', ascending=False).style.format({
            'Stock_Actual_Por_Quemar_U': "{:,.0f}",
            'Stock_Actual_Por_Quemar_Soles': "S/. {:,.2f}",
            'Entradas_U': "{:,.0f}",
            'Entradas_Soles': "S/. {:,.2f}",
            'Salidas_U': "{:,.0f}",
            'Salidas_Soles': "S/. {:,.2f}",
            'Ratio_Salida_Entrada_%': "{:.1f}%",
            '%_Inventario_Quemado': "{:.1f}%"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # FILA 1: Ordenado por Stock Actual Retenido (S/.)
    df_fam_g1 = df_fam.sort_values(by='Stock_Actual_Por_Quemar_Soles', ascending=False).copy()
    
    fig_fam_val = px.bar(
        df_fam_g1,
        x='Familia',
        y=['Stock_Actual_Por_Quemar_Soles', 'Entradas_Soles', 'Salidas_Soles'],
        title="1. Balance Valorizado",
        barmode='group',
        color_discrete_sequence=['#f59e0b', '#10b981', '#ef4444'],
        height=450
    )
    fig_fam_val.update_layout(
        xaxis={'categoryorder': 'array', 'categoryarray': df_fam_g1['Familia'].tolist()},
        yaxis_title="Monto en Soles (S/.)",
        xaxis_title="Familia"
    )
    st.plotly_chart(fig_fam_val, use_container_width=True)
    
    # FILA 2: Ordenado de mayor a menor % de Inventario Quemado
    df_fam_g2 = df_fam.sort_values(by='%_Inventario_Quemado', ascending=False).copy()
    
    fig_fam_pct = px.bar(
        df_fam_g2,
        x='Familia',
        y='%_Inventario_Quemado',
        title="2. Porcentaje (%) de Inventario Quemado",
        color='%_Inventario_Quemado',
        color_continuous_scale='Blues',
        height=450
    )
    fig_fam_pct.update_layout(
        xaxis={'categoryorder': 'array', 'categoryarray': df_fam_g2['Familia'].tolist()},
        yaxis_title="% de Inventario Vaciado",
        xaxis_title="Familia"
    )
    st.plotly_chart(fig_fam_pct, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: KARDEX POR SKU Y SU TRAZABILIDAD
# ------------------------------------------------------------------------------
with tab_sku:
    st.subheader("Trazabilidad por SKU ")
    
    codigos_disponibles = sorted(df_s_f['Codigo'].unique().tolist())
    opciones_buscador = [f"{cod} - {desc_map.get(cod, '')}" for cod in codigos_disponibles]
    
    if opciones_buscador:
        seleccion_str = st.selectbox("Escriba o seleccione un artículo:", opciones_buscador)
        sku_sel = seleccion_str.split(" - ")[0]
        
        df_k_sku = df_kardex_base[df_kardex_base['Codigo'] == sku_sel].copy()
        stock_sku_u = df_s_f[df_s_f['Codigo'] == sku_sel]['Stock'].sum()
        costo_sku = costo_map.get(sku_sel, 0.0)
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Stock Actual Fisico", f"{stock_sku_u:,.0f} U")
        col_s2.metric("Costo Unitario", f"S/. {costo_sku:,.2f}")
        col_s3.metric("Stock Actual Valorizado", f"S/. {stock_sku_u * costo_sku:,.2f}")
        
        # Reconstrucción Cronológica Reversa
        saldos_cronologicos = []
        stock_iterativo = stock_sku_u
        
        for mes in reversed(meses_historicos):
            df_mes = df_k_sku[df_k_sku['Mes_Mov'] == mes]
            ent_m = df_mes['Entradas'].sum()
            sal_m = df_mes['Salidas'].sum()
            val_cierre = stock_iterativo * costo_sku
            
            saldos_cronologicos.append({
                "Mes": mes,
                "Entradas (U)": ent_m,
                "Salidas (U)": sal_m,
                "Stock Cierre (U)": stock_iterativo,
                "Stock Cierre (S/.)": val_cierre
            })
            stock_iterativo = max(0.0, stock_iterativo - ent_m + sal_m)
            
        df_bal_sku = pd.DataFrame(saldos_cronologicos)[::-1].reset_index(drop=True)
        
        fig_sku = go.Figure()
        fig_sku.add_trace(go.Bar(x=df_bal_sku['Mes'], y=df_bal_sku['Entradas (U)'], name="Entradas (NI)", marker_color="#10b981"))
        fig_sku.add_trace(go.Bar(x=df_bal_sku['Mes'], y=df_bal_sku['Salidas (U)'], name="Salidas (NS)", marker_color="#ef4444"))
        fig_sku.add_trace(go.Scatter(x=df_bal_sku['Mes'], y=df_bal_sku['Stock Cierre (U)'], name="Stock Cierre", line=dict(color='#3b82f6', width=3), yaxis="y2"))
        
        fig_sku.update_layout(
            title=f"Evolución Mensual de Stock y Flujos para el Código: {sku_sel}",
            barmode='group',
            xaxis_title="Mes",
            yaxis_title="Movimientos (Unidades)",
            yaxis2=dict(title="Stock Cierre (Unidades)", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        st.plotly_chart(fig_sku, use_container_width=True)
        
        st.write("#### Balance Mensual")
        st.dataframe(
            df_bal_sku.style.format({
                "Entradas (U)": "{:,.0f}",
                "Salidas (U)": "{:,.0f}",
                "Stock Cierre (U)": "{:,.0f}",
                "Stock Cierre (S/.)": "S/. {:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )

# ------------------------------------------------------------------------------
# TAB 3: MATRIZ HISTÓRICA GENERAL
# ------------------------------------------------------------------------------
with tab_general:
    st.subheader("Registro Histórico de Transacciones")
    
    cols_vista = [
        'Fecha', 'Mes_Mov', 'Almacen', 'Codigo', 'Descripcion', 'Familia',
        'Tipo_Movimiento', 'Entradas', 'Salidas', 'Costo_Unitario', 'Valor_Ingreso_Soles', 'Valor_Salida_Soles'
    ]
    
    cols_existentes = [c for c in cols_vista if c in df_kardex_base.columns]
    df_export = df_kardex_base[cols_existentes].copy()
    
    st.dataframe(df_export, use_container_width=True, hide_index=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Kardex_Detallado')
        df_fam.to_excel(writer, index=False, sheet_name='Resumen_Familia')
        
    st.download_button(
        label="📥 Descargar Kardex Completo y Balance a Excel",
        data=output.getvalue(),
        file_name="Kardex_y_Quemado_Inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )