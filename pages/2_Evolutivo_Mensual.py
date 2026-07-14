import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

st.title("Evolutivo de Cierres Mensuales Valorizados y Auditoría de Variaciones")
st.markdown("---")

# Estandarización rápida de tipos
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()

# ==============================================================================
# 1. CONSTRUCCIÓN DE UNIVERSO MAESTRO DE CÓDIGOS
# ==============================================================================
df_codigos_stock = df_stock[['Codigo', 'Descripcion', 'Costo', 'Um', 'Familia', 'SubFamilia', 'Almacen', 'Stock']].copy()
df_codigos_mov = df_mov[['Codigo', 'Descripcion', 'Um', 'Almacen']].drop_duplicates(subset=['Codigo'])

df_maestro_skus = pd.merge(df_codigos_stock, df_codigos_mov, on='Codigo', how='outer', suffixes=('', '_mov'))
df_maestro_skus['Descripcion'] = df_maestro_skus['Descripcion'].fillna(df_maestro_skus['Descripcion_mov'])
df_maestro_skus['Um'] = df_maestro_skus['Um'].fillna(df_maestro_skus['Um_mov'])
df_maestro_skus['Almacen'] = df_maestro_skus['Almacen'].fillna(df_maestro_skus['Almacen_mov'])
df_maestro_skus['Familia'] = df_maestro_skus['Familia'].fillna('SIN CLASIFICAR')
df_maestro_skus['SubFamilia'] = df_maestro_skus['SubFamilia'].fillna('GENERAL')
df_maestro_skus['Costo'] = df_maestro_skus['Costo'].fillna(0)
df_maestro_skus['Stock'] = df_maestro_skus['Stock'].fillna(0)

# ==============================================================================
# 2. FILTROS JERÁRQUICOS EN LA BARRA LATERAL
# ==============================================================================
st.sidebar.header("Parámetros del Histórico")
list_alm = ["TODOS"] + sorted(df_maestro_skus['Almacen'].dropna().unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtrar Evolución por Almacén", list_alm)

df_m_f = df_maestro_skus.copy()
df_mov_f = df_mov.copy()

if filtro_alm != "TODOS":
    df_m_f = df_m_f[df_m_f['Almacen'] == filtro_alm]
    df_mov_f = df_mov_f[df_mov_f['Almacen'] == filtro_alm]

list_fam = ["TODOS"] + sorted(df_m_f['Familia'].dropna().unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtrar por Familia", list_fam)

if filtro_fam != "TODOS":
    df_m_f = df_m_f[df_m_f['Familia'] == filtro_fam]
    codigos_familia = df_m_f['Codigo'].unique()
    df_mov_f = df_mov_f[df_mov_f['Codigo'].isin(codigos_familia)]

list_subfam = ["TODOS"] + sorted(df_m_f['SubFamilia'].dropna().unique().tolist())
filtro_subfam = st.sidebar.selectbox("Filtrar por Subfamilia", list_subfam)

if filtro_subfam != "TODOS":
    df_m_f = df_m_f[df_m_f['SubFamilia'] == filtro_subfam]
    codigos_subfamilia = df_m_f['Codigo'].unique()
    df_mov_f = df_mov_f[df_mov_f['Codigo'].isin(codigos_subfamilia)]

# ⚡ OPTIMIZACIÓN VECTORIAL: Eliminamos .apply(axis=1) lento por asignaciones nativas de Pandas
df_mov_f['Entradas'] = 0.0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NI', 'Entradas'] = df_mov_f['Cantidad']

df_mov_f['Salidas'] = 0.0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NS', 'Salidas'] = df_mov_f['Cantidad']

df_mov_f['Es_Salida'] = 0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NS', 'Es_Salida'] = 1

# Rango temporal
meses_historicos = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]

costo_map = df_m_f.set_index('Codigo')['Costo'].to_dict()
desc_map = df_m_f.set_index('Codigo')['Descripcion'].to_dict()
um_map = df_m_f.set_index('Codigo')['Um'].to_dict()

# ==============================================================================
# 🚀 MOTOR ULTRA-RÁPIDO: RECONSTRUCCIÓN HISTÓRICA VECTORIZADA INTERNA
# ==============================================================================
# Mapeo del Stock Actual agrupado por SKU y Almacén (Para evitar iterrows)
stock_actual_agrupado = df_m_f.groupby(['Codigo', 'Almacen'])['Stock'].sum().to_dict()

# Generamos matrices pivotadas de movimientos futuros para resolver todo con un solo comando matricial
pivot_movs = df_mov_f.groupby(['Mes_Mov', 'Codigo', 'Almacen'])[['Entradas', 'Salidas']].sum().reset_index()

# Tablas cruzadas rápidas indexadas por Mes y Combinación única (Codigo, Almacen)
entradas_pivot = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Entradas', aggfunc='sum').fillna(0)
salidas_pivot = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Salidas', aggfunc='sum').fillna(0)

# Asegurar que todas las columnas de meses existan en los pivots para evitar KeyErrors
for mes in meses_historicos:
    if mes not in entradas_pivot.columns: entradas_pivot[mes] = 0.0
    if mes not in salidas_pivot.columns: salidas_pivot[mes] = 0.0

# Precalcular agrupaciones mensuales de consumo para evitar .groupby dentro del bucle
movs_actuales_g = df_mov_f.groupby(['Mes_Mov', 'Codigo']).agg(
    Salidas_Mes=('Salidas', 'sum'),
    Frecuencia_Mes=('Es_Salida', 'sum')
).to_dict('index')

evolutivo_data = []
saldos_por_mes_sku = {mes: {} for mes in meses_historicos}

# Lista de llaves únicas (Codigo, Almacen) del maestro filtrado
combinaciones_maestro = df_m_f.groupby(['Codigo', 'Almacen']).size().index

# Iteramos de forma segura únicamente sobre la lista de meses cronológicos
for mes in meses_historicos:
    # Filtramos dinámicamente columnas que pertenecen al futuro relativo a este mes
    meses_futuros = [m for m in meses_historicos if m > mes]
    
    # Sumamos flujos netos futuros matricialmente de forma instantánea
    ef_totales = entradas_pivot[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}
    sf_totales = salidas_pivot[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}
    
    total_valor_mes = 0.0
    total_unidades_mes = 0.0
    
    # Temporal para consolidar stock a nivel SKU
    stock_sku_acumulado = {}
    
    for c_idx in combinaciones_maestro:
        sku, alm = c_idx
        stk_act = stock_actual_agrupado.get((sku, alm), 0.0)
        ef = ef_totales.get((sku, alm), 0.0)
        sf = sf_totales.get((sku, alm), 0.0)
        
        stk_mes_alm = max(0.0, stk_act - ef + sf)
        stock_sku_acumulado[sku] = stock_sku_acumulado.get(sku, 0.0) + stk_mes_alm

    # Consolidar datos finales de la foto mensual
    for sku in costo_map.keys():
        stk_final_sku = stock_sku_acumulado.get(sku, 0.0)
        costo_sku = costo_map.get(sku, 0.0)
        
        # Recuperamos datos de consumo precalculados
        info_mov_mes = movs_actuales_g.get((mes, sku), {'Salidas_Mes': 0.0, 'Frecuencia_Mes': 0})
        
        saldos_por_mes_sku[mes][sku] = {
            'Stock': stk_final_sku,
            'Salidas_Mes': info_mov_mes['Salidas_Mes'],
            'Frecuencia_Mes': info_mov_mes['Frecuencia_Mes'],
            'Costo': costo_sku
        }
        
        total_unidades_mes += stk_final_sku
        total_valor_mes += (stk_final_sku * costo_sku)
        
    evolutivo_data.append({
        "Mes": mes,
        "Valorizado_Soles": total_valor_mes,
        "Volumen_Unidades": total_unidades_mes
    })

df_evolutivo = pd.DataFrame(evolutivo_data)
df_evolutivo['Variacion_Absoluta'] = df_evolutivo['Valorizado_Soles'].diff().fillna(0)
df_evolutivo['Variacion_Porcentual'] = df_evolutivo['Valorizado_Soles'].pct_change().fillna(0) * 100

# ==============================================================================
# SECCIÓN 1: TENDENCIA HISTÓRICA ABSOLUTA DE CIERRE DE MES
# ==============================================================================
st.subheader("Tendencia Histórica Absoluta de Cierre de Mes")

fig_cierre_puro = go.Figure()
fig_cierre_puro.add_trace(go.Scatter(
    x=df_evolutivo['Mes'],
    y=df_evolutivo['Valorizado_Soles'],
    mode='lines+markers',
    line=dict(color="#0d9488", width=4, shape="spline"),
    marker=dict(size=10, color="#0d9488", line=dict(width=2, color="white")),
    hoverinfo="x+y",
    showlegend=False
))

for idx, row in df_evolutivo.iterrows():
    fig_cierre_puro.add_annotation(
        x=row['Mes'],
        y=row['Valorizado_Soles'],
        text=f"<b>S/. {row['Valorizado_Soles']/1000:,.0f}K</b>",
        showarrow=False,
        yshift=24,
        font=dict(color="#0f172a", size=11, family="Arial"),
        bordercolor="#cbd5e1",
        borderwidth=1,
        borderpad=5,
        bgcolor="white",
        opacity=0.95
    )

fig_cierre_puro.update_layout(
    yaxis=dict(title=dict(text="Capital Neto Custodia (S/.)"), gridcolor="#f1f5f9"),
    xaxis=dict(gridcolor="#f1f5f9"),
    plot_bgcolor="white",
    margin=dict(t=60, b=40, l=40, r=40)
)
st.plotly_chart(fig_cierre_puro, use_container_width=True)

# ==============================================================================
# SECCIÓN 2: VARIACIÓN PORCENTUAL DE MES A MES (MOM)
# ==============================================================================
st.subheader("📈 Variación Porcentual de Capital Inmovilizado Mes a Mes (MoM)")

fig_var_pct = go.Figure()
fig_var_pct.add_trace(go.Bar(
    x=df_evolutivo['Mes'],
    y=df_evolutivo['Variacion_Porcentual'],
    marker_color=df_evolutivo['Variacion_Porcentual'].apply(lambda x: '#ef4444' if x < 0 else '#10b981'),
    text=df_evolutivo['Variacion_Porcentual'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "-"),
    textposition="outside",
    showlegend=False
))

fig_var_pct.update_layout(
    yaxis=dict(title="Variación (%)", gridcolor="#f1f5f9"),
    xaxis=dict(gridcolor="#f1f5f9"),
    plot_bgcolor="white",
    margin=dict(t=50, b=40, l=40, r=40)
)
st.plotly_chart(fig_var_pct, use_container_width=True)

# ==============================================================================
# SECCIÓN 3: TABLA DE TRAZABILIDAD FINANCIERA Y VARIACIONES MENSUALES
# ==============================================================================
st.subheader("📋 Trazabilidad Financiera y Variaciones Mensuales (MOM)")

df_trazabilidad = df_evolutivo.copy()
df_trazabilidad['Var_Fisica_Abs'] = df_trazabilidad['Volumen_Unidades'].diff().fillna(0)
df_trazabilidad['Var_Fisica_Pct'] = df_trazabilidad['Volumen_Unidades'].pct_change().fillna(0) * 100

tabla_mom_data = []
for i, row in df_trazabilidad.iterrows():
    if i == 0:
        var_monetaria = "-"
        var_volumetrica = "-"
    else:
        flecha_m = "↗" if row['Variacion_Absoluta'] >= 0 else "↘"
        var_monetaria = f"{flecha_m} S/. {row['Variacion_Absoluta']:,.2f} ({row['Variacion_Porcentual']:+.1f}%)"
        
        flecha_v = "↗" if row['Var_Fisica_Abs'] >= 0 else "↘"
        var_volumetrica = f"{flecha_v} {row['Var_Fisica_Abs']:,.2f} UM ({row['Var_Fisica_Pct']:+.1f}%)"

    tabla_mom_data.append({
        "PERIODO MES": row['Mes'],
        "CIERRE MONETARIO": f"S/. {row['Valorizado_Soles']:,.2f}",
        "VARIACIÓN MONETARIA (MOM)": var_monetaria,
        "CIERRE FÍSICO (UM)": f"{row['Volumen_Unidades']:,.2f} UM",
        "VARIACIÓN VOLUMÉTRICA (MOM)": var_volumetrica
    })

df_tabla_mom = pd.DataFrame(tabla_mom_data)
st.dataframe(df_tabla_mom, use_container_width=True, hide_index=True)

# ==============================================================================
# SECCIÓN 4: TENDENCIA INTEGRADA: VOLUMEN FÍSICO VS CAPITAL
# ==============================================================================
st.write("---")
col_analisis_1, col_analisis_2 = st.columns([2, 1])

with col_analisis_1:
    st.subheader("Tendencia Integrada: Volumen Físico vs Capital")
    fig_mix = go.Figure()
    fig_mix.add_trace(go.Scatter(
        x=df_evolutivo['Mes'], y=df_evolutivo['Valorizado_Soles'], 
        name="Valorizado (S/.)", yaxis="y1", 
        line=dict(color="#2563eb", width=3)
    ))
    fig_mix.add_trace(go.Bar(
        x=df_evolutivo['Mes'], y=df_evolutivo['Volumen_Unidades'], 
        name="Volumen Físico", yaxis="y2", 
        marker_color="rgba(245, 158, 11, 0.25)"
    ))
    
    fig_mix.update_layout(
        yaxis=dict(title=dict(text="Eje Monetario (S/.)", font=dict(color="#2563eb")), tickfont=dict(color="#2563eb")),
        yaxis2=dict(title=dict(text="Eje Volumen Unidades", font=dict(color="#d97706")), tickfont=dict(color="#d97706"), overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        plot_bgcolor="white"
    )
    st.plotly_chart(fig_mix, use_container_width=True)

with col_analisis_2:
    st.subheader("Análisis Concurrente")
    correlacion = df_evolutivo['Valorizado_Soles'].corr(df_evolutivo['Volumen_Unidades'])
    st.metric("Coeficiente de Correlación R", f"{correlacion:.4f}")
    st.markdown(f"Un coeficiente de `{correlacion:.2f}` evalúa la correlación contable de volumen físico frente al valor de tus activos.")

# ==============================================================================
# SECCIÓN 5: DESGLOSE Y AUDITORÍA DE SKUS POR CIERRE DE MES
# ==============================================================================
st.write("---")
st.subheader("🔍 Desglose Específico y Auditoría de SKUs por Cierre de Mes")
mes_auditoria = st.selectbox("Seleccione el Mes para Auditar las Cunas de Variación y Consumo:", meses_historicos, index=len(meses_historicos)-1)

auditoria_skus = []
datos_mes_sel = saldos_por_mes_sku[mes_auditoria]
total_valor_mes_sel = sum(d['Stock'] * d['Costo'] for d in datos_mes_sel.values())

for sku, datos in datos_mes_sel.items():
    stock = datos['Stock']
    costo = datos['Costo']
    val_total = stock * costo
    salidas = datos['Salidas_Mes']
    frecuencia = datos.get('Frecuencia_Mes', 0)
    
    if stock > 0 or salidas > 0:
        auditoria_skus.append({
            "Codigo": sku,
            "Descripcion": desc_map.get(sku, "DESCRIPCIÓN DESCONOCIDA"),
            "UM": um_map.get(sku, "-"),  
            "Stock_Cierre": stock,
            "Costo_Unitario": costo,
            "Valorizado_Cierre": val_total,
            "Cantidad_Salidas_Mes": salidas,
            "Frecuencia_Pedidos_Mes": frecuencia,  
            "Participacion_Capital": (val_total / total_valor_mes_sel * 100) if total_valor_mes_sel > 0 else 0
        })

df_auditoria = pd.DataFrame(auditoria_skus).sort_values(by='Valorizado_Cierre', ascending=False)

st.dataframe(
    df_auditoria.style.format({
        'Stock_Cierre': '{:,.0f}',
        'Costo_Unitario': 'S/. {:,.4f}',
        'Valorizado_Cierre': 'S/. {:,.2f}',
        'Cantidad_Salidas_Mes': '{:,.0f}',
        'Frecuencia_Pedidos_Mes': '{:,.0f} veces',
        'Participacion_Capital': '{:.2f}%'
    }),
    use_container_width=True,
    hide_index=True
)

# ==============================================================================
# SECCIÓN 6: BUSCADOR DINÁMICO DE TRAZABILIDAD POR SKU
# ==============================================================================
st.write("---")
st.subheader("🎯 Buscador Dinámico de Trazabilidad por SKU / Código")

codigos_disponibles = sorted(df_m_f['Codigo'].unique().tolist())
descripciones_disponibles = df_m_f.set_index('Codigo')['Descripcion'].to_dict()

opciones_buscador = [f"{cod} - {descripciones_disponibles.get(cod, '')}" for cod in codigos_disponibles]

if opciones_buscador:
    seleccion_sku_str = st.selectbox("Escriba o seleccione un Código/Descripción para analizar:", opciones_buscador)
    sku_seleccionado = seleccion_sku_str.split(" - ")[0]
    desc_seleccionada = descripciones_disponibles.get(sku_seleccionado, "")
    um_seleccionada = um_map.get(sku_seleccionado, "UM")
    
    historial_sku = []
    
    for mes in meses_historicos:
        datos_mes_hist = saldos_por_mes_sku[mes].get(sku_seleccionado, {'Stock': 0.0, 'Costo': 0.0})
        stk_mes_consolidado = datos_mes_hist['Stock']
        costo_sku = datos_mes_hist['Costo']
        
        historial_sku.append({
            "Mes": mes,
            "Stock Cierre": stk_mes_consolidado,
            "Valorizado Total (S/.)": stk_mes_consolidado * costo_sku,
        })
        
    df_historial_sku = pd.DataFrame(historial_sku)
    
    c_sku1, c_sku2, c_sku3 = st.columns(3)
    c_sku1.metric("SKU Evaluado", sku_seleccionado)
    c_sku2.markdown(f"**Descripción y Medida:**\n*{desc_seleccionada}* \n\n**Unidad:** `{um_seleccionada}`")
    
    df_dist_almacenes = df_stock[df_stock['Codigo'] == sku_seleccionado][['Almacen', 'Stock']]
    total_stock_agrupado = df_dist_almacenes['Stock'].sum()
    
    c_sku3.metric("Último Stock Disp. Consolidado", f"{total_stock_agrupado:,.0f} {um_seleccionada}")
    
    with st.container():
        st.markdown("**📍 Ubicación y Stock actual por Almacén:**")
        if not df_dist_almacenes.empty and total_stock_agrupado > 0:
            cols_almacenes = st.columns(min(len(df_dist_almacenes), 4))
            for idx, r_alm in df_dist_almacenes.reset_index().iterrows():
                col_target = cols_almacenes[idx % 4]
                col_target.info(f"**{r_alm['Almacen']}**\n\n{r_alm['Stock']:,.0f} {um_seleccionada}")
        else:
            st.warning("Este SKU no cuenta con existencias vigentes en ningún almacén en el último cierre.")
    
    fig_sku_line = go.Figure()
    fig_sku_line.add_trace(go.Scatter(
        x=df_historial_sku['Mes'], y=df_historial_sku['Valorizado Total (S/.)'],
        mode='lines+markers+text',
        name="Valorizado S/.",
        text=df_historial_sku['Valorizado Total (S/.)'].apply(lambda x: f"S/. {x:,.0f}" if x > 0 else "S/. 0"),
        textposition="top center",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=8)
    ))
    fig_sku_line.update_layout(
        title=f"Evolución de Capital Inmovilizado Consolidado (Todos los Almacenes): {sku_seleccionado}",
        plot_bgcolor="white", 
        yaxis=dict(gridcolor="#f1f5f9"), 
        xaxis=dict(gridcolor="#f1f5f9"),
        height=350,
        margin=dict(t=80, b=40, l=40, r=40)
    )
    st.plotly_chart(fig_sku_line, use_container_width=True)
else:
    st.info("No hay códigos específicos que coincidan con la segmentación de la barra lateral.")