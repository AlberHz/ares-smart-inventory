import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io

st.set_page_config(
    layout="wide", 
    page_title="KPI 2 - EVOLUTIVO MENSUAL",
    page_icon="📦"
)

# Validar datos en session_state
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

# ==============================================================================
# ESTANDARIZACIÓN DE COLUMNAS ROBUSTA
# ==============================================================================
def estandarizar_columnas(df):
    df = df.copy()
    mapeo = {}
    for col in df.columns:
        col_clean = str(col).strip().upper()
        col_clean_sin_tilde = col_clean.replace('Ó', 'O').replace('Í', 'I').replace('Á', 'A').replace('É', 'E').replace('Ú', 'U')
        
        if col_clean_sin_tilde in ['CODIGO', 'SKU', 'MATERIAL', 'ARTICULO', 'CODIGO_MATERIAL', 'CODIGO MATERIAL']:
            mapeo[col] = 'Codigo'
        elif col_clean_sin_tilde in ['DESCRIPCION', 'PRODUCTO', 'DETALLE', 'MATERIAL_DESCRIPCION', 'DESCRIPCION MATERIAL']:
            mapeo[col] = 'Descripcion'
        elif col_clean_sin_tilde in ['ALMACEN', 'ALM', 'CENTRO', 'BODEGA']:
            mapeo[col] = 'Almacen'
        elif col_clean_sin_tilde in ['FAMILIA', 'CATEGORIA', 'LINEA']:
            mapeo[col] = 'Familia'
        elif col_clean_sin_tilde in ['SUBFAMILIA', 'SUBCATEGORIA', 'SUBLINEA']:
            mapeo[col] = 'SubFamilia'
        elif col_clean_sin_tilde in ['COSTO', 'COSTO_UNITARIO', 'COSTO UNITARIO', 'PRECIO']:
            mapeo[col] = 'Costo'
        elif col_clean_sin_tilde in ['STOCK', 'CANTIDAD_STOCK', 'STOCK_ACTUAL', 'CANTIDAD_ACTUAL']:
            mapeo[col] = 'Stock'
        elif col_clean_sin_tilde in ['UM', 'UNIDAD', 'UNIDAD_MEDIDA', 'UOM']:
            mapeo[col] = 'Um'
        elif col_clean_sin_tilde in ['CANTIDAD', 'CANT', 'CANTIDAD_MOVIMIENTO']:
            mapeo[col] = 'Cantidad'
        elif col_clean_sin_tilde in ['TIPO_MOVIMIENTO', 'TIPO_MOV', 'TIPO', 'TIPO_OPERACION']:
            mapeo[col] = 'Tipo_Movimiento'
        elif col_clean_sin_tilde in ['FECHA', 'FECHA_MOVIMIENTO', 'DATE']:
            mapeo[col] = 'Fecha'
        elif col_clean_sin_tilde in ['MES_MOV', 'MES', 'PERIODO', 'FECHA_MES']:
            mapeo[col] = 'Mes_Mov'
            
    return df.rename(columns=mapeo)

df_stock = estandarizar_columnas(st.session_state['df_stock'])
df_mov = estandarizar_columnas(st.session_state['df_mov'])

st.title("KPI 2 - Valorización del Inventario Mes a Mes - Cierres Mensuales")
st.markdown("---")

if 'Codigo' not in df_stock.columns or 'Codigo' not in df_mov.columns:
    st.error("No se detectó la columna 'Codigo' o 'SKU' en uno de los archivos cargados.")
    st.stop()

# Formateo seguro
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip().str.upper()
df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip().str.upper()

# Derivar Mes_Mov desde Fecha si está disponible
if 'Fecha' in df_mov.columns:
    df_mov['Fecha_dt'] = pd.to_datetime(df_mov['Fecha'], errors='coerce')
    df_mov['Mes_Mov'] = df_mov['Fecha_dt'].dt.strftime('%Y-%m')

for col, val_default in [('Descripcion', 'SIN DESCRIPCIÓN'), ('Familia', 'SIN CLASIFICAR'), ('SubFamilia', 'GENERAL'), ('Almacen', 'GENERAL'), ('Um', 'UM'), ('Costo', 0.0), ('Stock', 0.0)]:
    if col not in df_stock.columns: df_stock[col] = val_default
    if col not in df_mov.columns: df_mov[col] = val_default

for col, val_default in [('Cantidad', 0.0), ('Tipo_Movimiento', 'NI'), ('Mes_Mov', '2026-08')]:
    if col not in df_mov.columns: df_mov[col] = val_default

df_stock['Costo'] = pd.to_numeric(df_stock['Costo'], errors='coerce').fillna(0.0)
df_stock['Stock'] = pd.to_numeric(df_stock['Stock'], errors='coerce').fillna(0.0)
df_mov['Cantidad'] = pd.to_numeric(df_mov['Cantidad'], errors='coerce').fillna(0.0)

# ==============================================================================
# 1. MAESTRO GENERAL
# ==============================================================================
df_codigos_stock = df_stock[['Codigo', 'Descripcion', 'Costo', 'Um', 'Familia', 'SubFamilia', 'Almacen', 'Stock']].copy()
df_codigos_mov = df_mov[['Codigo', 'Descripcion', 'Um', 'Almacen']].drop_duplicates()

df_maestro_skus = pd.merge(df_codigos_stock, df_codigos_mov, on=['Codigo', 'Almacen'], how='outer', suffixes=('', '_mov'))
df_maestro_skus['Descripcion'] = df_maestro_skus['Descripcion'].fillna(df_maestro_skus['Descripcion_mov'])
df_maestro_skus['Um'] = df_maestro_skus['Um'].fillna(df_maestro_skus['Um_mov'])
df_maestro_skus['Familia'] = df_maestro_skus['Familia'].fillna('SIN CLASIFICAR')
df_maestro_skus['SubFamilia'] = df_maestro_skus['SubFamilia'].fillna('GENERAL')
df_maestro_skus['Costo'] = df_maestro_skus['Costo'].fillna(0.0)
df_maestro_skus['Stock'] = df_maestro_skus['Stock'].fillna(0.0)

# ==============================================================================
# 2. FILTROS
# ==============================================================================
st.sidebar.header("Parámetros")

list_alm = ["TODOS"] + sorted(df_maestro_skus['Almacen'].dropna().unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtros Almacén", list_alm)

df_m_f = df_maestro_skus.copy()
df_mov_f = df_mov.copy()

if filtro_alm != "TODOS":
    df_m_f = df_m_f[df_m_f['Almacen'] == filtro_alm]
    df_mov_f = df_mov_f[df_mov_f['Almacen'] == filtro_alm]

list_fam = ["TODOS"] + sorted(df_m_f['Familia'].dropna().unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtrar por Familia", list_fam)

if filtro_fam != "TODOS" and filtro_fam in list_fam:
    df_m_f = df_m_f[df_m_f['Familia'] == filtro_fam]
    codigos_familia = df_m_f['Codigo'].unique()
    df_mov_f = df_mov_f[df_mov_f['Codigo'].isin(codigos_familia)]

list_subfam = ["TODOS"] + sorted(df_m_f['SubFamilia'].dropna().unique().tolist())
filtro_subfam = st.sidebar.selectbox("Filtrar por Subfamilia", list_subfam)

if filtro_subfam != "TODOS" and filtro_subfam in list_subfam:
    df_m_f = df_m_f[df_m_f['SubFamilia'] == filtro_subfam]
    codigos_subfamilia = df_m_f['Codigo'].unique()
    df_mov_f = df_mov_f[df_mov_f['Codigo'].isin(codigos_subfamilia)]

df_mov_f['Entradas'] = 0.0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NI', 'Entradas'] = df_mov_f['Cantidad']

df_mov_f['Salidas'] = 0.0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NS', 'Salidas'] = df_mov_f['Cantidad']

df_mov_f['Es_Salida'] = 0
df_mov_f.loc[df_mov_f['Tipo_Movimiento'] == 'NS', 'Es_Salida'] = 1

# DETERMINACIÓN DINÁMICA DE MESES HISTÓRICOS
meses_historicos = sorted(df_mov_f['Mes_Mov'].dropna().unique().tolist())

costo_map = df_m_f.groupby('Codigo')['Costo'].mean().to_dict()
desc_map = df_m_f.groupby('Codigo')['Descripcion'].first().to_dict()
um_map = df_m_f.groupby('Codigo')['Um'].first().to_dict()

# ==============================================================================
# 3. RECONSTRUCCIÓN HISTÓRICA VECTORIZADA
# ==============================================================================
stock_actual_agrupado = df_m_f.groupby(['Codigo', 'Almacen'])['Stock'].sum().to_dict()
pivot_movs = df_mov_f.groupby(['Mes_Mov', 'Codigo', 'Almacen'])[['Entradas', 'Salidas']].sum().reset_index()

entradas_pivot = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Entradas', aggfunc='sum').fillna(0)
salidas_pivot = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Salidas', aggfunc='sum').fillna(0)

for mes in meses_historicos:
    if mes not in entradas_pivot.columns: entradas_pivot[mes] = 0.0
    if mes not in salidas_pivot.columns: salidas_pivot[mes] = 0.0

movs_actuales_g = df_mov_f.groupby(['Mes_Mov', 'Codigo']).agg(
    Salidas_Mes=('Salidas', 'sum'),
    Frecuencia_Mes=('Es_Salida', 'sum')
).to_dict('index')

evolutivo_data = []
saldos_por_mes_sku = {mes: {} for mes in meses_historicos}
combinaciones_maestro = df_m_f.groupby(['Codigo', 'Almacen']).size().index

for mes in meses_historicos:
    meses_futuros = [m for m in meses_historicos if m > mes]
    
    ef_totales = entradas_pivot[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}
    sf_totales = salidas_pivot[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}
    
    total_valor_mes = 0.0
    total_unidades_mes = 0.0
    stock_sku_acumulado = {}
    
    for c_idx in combinaciones_maestro:
        sku, alm = c_idx
        stk_act = stock_actual_agrupado.get((sku, alm), 0.0)
        ef = ef_totales.get((sku, alm), 0.0)
        sf = sf_totales.get((sku, alm), 0.0)
        
        stk_mes_alm = max(0.0, stk_act - ef + sf)
        stock_sku_acumulado[sku] = stock_sku_acumulado.get(sku, 0.0) + stk_mes_alm

    for sku in costo_map.keys():
        stk_final_sku = stock_sku_acumulado.get(sku, 0.0)
        costo_sku = costo_map.get(sku, 0.0)
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

# FUNCIÓN AUXILIAR DE FORMATO DE MONEDA (M / K)
def formatear_monto(valor):
    if abs(valor) >= 1_000_000:
        return f"S/. {valor / 1_000_000:,.1f} M"
    else:
        return f"S/. {valor / 1_000:,.1f} K"

# ==============================================================================
# TARJETAS KPIS DE GERENCIA
# ==============================================================================
idx_max_cap = df_evolutivo['Valorizado_Soles'].idxmax()
mes_max_cap = df_evolutivo.loc[idx_max_cap, 'Mes']
val_max_cap = df_evolutivo.loc[idx_max_cap, 'Valorizado_Soles']

idx_min_cap = df_evolutivo['Valorizado_Soles'].idxmin()
mes_min_cap = df_evolutivo.loc[idx_min_cap, 'Mes']
val_min_cap = df_evolutivo.loc[idx_min_cap, 'Valorizado_Soles']

# Lógica YoY (Año Anterior) para Crecimiento Acumulado
ultimo_mes = df_evolutivo.iloc[-1]['Mes']
ultimo_cierre = df_evolutivo.iloc[-1]['Valorizado_Soles']

# Buscar el mismo mes del año anterior
partes = ultimo_mes.split('-')
anio_ant = str(int(partes[0]) - 1)
mes_ant_target = f"{anio_ant}-{partes[1]}"

df_ano_ant = df_evolutivo[df_evolutivo['Mes'] == mes_ant_target]

if not df_ano_ant.empty:
    cierre_ref = df_ano_ant.iloc[0]['Valorizado_Soles']
    etiqueta_ref = f"vs. {mes_ant_target} (YoY)"
else:
    # Si no existe el mes del año anterior exacto, compara con el primer mes disponible
    cierre_ref = df_evolutivo.iloc[0]['Valorizado_Soles']
    etiqueta_ref = f"vs. {df_evolutivo.iloc[0]['Mes']}"

var_acumulada_periodo = ((ultimo_cierre - cierre_ref) / cierre_ref * 100) if cierre_ref > 0 else 0

k1, k2, k3 = st.columns(3)
k1.metric("Pico Mínimo Capital", formatear_monto(val_min_cap), f"Mes: {mes_min_cap}")
k2.metric("Pico Máximo Capital", formatear_monto(val_max_cap), f"Mes: {mes_max_cap}")
k3.metric("Crecimiento Acumulado", f"{var_acumulada_periodo:+.2f}%", etiqueta_ref)

st.markdown("---")

# ==============================================================================
# GRÁFICO 1: TENDENCIA HISTÓRICA DE CAPITAL CON FORMATO EN M/K
# ==============================================================================
st.subheader("Tendencia de Cierre de Mes a Mes del Valor del Inventario Valorizado")

fig_cierre_puro = go.Figure()
fig_cierre_puro.add_trace(go.Scatter(
    x=df_evolutivo['Mes'],
    y=df_evolutivo['Valorizado_Soles'],
    mode='lines+markers',
    name="Capital Inmovilizado",
    line=dict(color="#0d9488", width=4, shape="spline"),
    marker=dict(size=10, color="#0d9488", line=dict(width=2, color="white")),
    hoverinfo="x+y"
))

for idx, row in df_evolutivo.iterrows():
    monto_fmt = formatear_monto(row['Valorizado_Soles'])
    fig_cierre_puro.add_annotation(
        x=row['Mes'],
        y=row['Valorizado_Soles'],
        text=f"<b>{monto_fmt}</b>",
        showarrow=False,
        yshift=24,
        font=dict(color="#0f172a", size=11),
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
    height=400,
    margin=dict(t=40, b=40, l=40, r=40)
)
st.plotly_chart(fig_cierre_puro, use_container_width=True)

# ==============================================================================
# GRÁFICO 2: VARIACIÓN PORCENTUAL CON PROMEDIO MÓVIL
# ==============================================================================
st.subheader("Variación Porcentual Mes a Mes del Valor del Inventario Valorizado")

df_evolutivo['Tendencia_Suavizada'] = df_evolutivo['Variacion_Porcentual'].rolling(window=3, min_periods=1).mean()
mediana_var = df_evolutivo['Variacion_Porcentual'].iloc[1:].median()

if mediana_var > 0.5:
    evaluacion_tendencia = "INCREMENTO CONSTANTE (Acumulativo)"
    detalle_eval = "La mayoría de meses presentan variaciones positivas sostenidas, indicando acumulación o aumento del valor del inventario."
elif mediana_var < -0.5:
    evaluacion_tendencia = "DISMINUCIÓN PROGRESIVA (Optimización)"
    detalle_eval = "La tendencia general apunta a la reducción del inventario y por lo tanto a la reducción de capital inmovilizado."
else:
    evaluacion_tendencia = "ESTABLE / NEUTRO"
    detalle_eval = "Las variaciones fluctuantes se compensan entre sí, manteniendo el stock en niveles estables."

fig_var_pct = go.Figure()

fig_var_pct.add_trace(go.Bar(
    x=df_evolutivo['Mes'],
    y=df_evolutivo['Variacion_Porcentual'],
    name="Variación Mensual (%)",
    marker_color=df_evolutivo['Variacion_Porcentual'].apply(lambda x: '#ef4444' if x < 0 else '#10b981'),
    text=df_evolutivo['Variacion_Porcentual'].apply(lambda x: f"{x:+.1f}%" if x != 0 else "-"),
    textposition="outside"
))

fig_var_pct.add_trace(go.Scatter(
    x=df_evolutivo['Mes'],
    y=df_evolutivo['Tendencia_Suavizada'],
    mode='lines+markers',
    name="Tendencia Suavizada",
    line=dict(color="#1e40af", width=3, dash='dot'),
    marker=dict(size=6)
))

fig_var_pct.update_layout(
    yaxis=dict(title="Variación (%)", gridcolor="#f1f5f9"),
    xaxis=dict(gridcolor="#f1f5f9"),
    plot_bgcolor="white",
    height=380,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=40, b=40, l=40, r=40)
)
st.plotly_chart(fig_var_pct, use_container_width=True)

st.info(f"💡 **Análisis de Tendencia:** Se detecta una conducta **{evaluacion_tendencia}**. {detalle_eval}")

# ==============================================================================
# AUDITORÍA DE SKUS POR MES
# ==============================================================================
st.markdown("---")
st.subheader("Desglose por SKU por Cierre de Mes del Valor del Inventario Valorizado")
mes_auditoria = st.selectbox("Seleccione el Mes para Auditar los códigos con Variación y Consumo:", meses_historicos, index=len(meses_historicos)-1)

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
        'Costo_Unitario': 'S/. {:,.2f}',
        'Valorizado_Cierre': 'S/. {:,.2f}',
        'Cantidad_Salidas_Mes': '{:,.0f}',
        'Frecuencia_Pedidos_Mes': '{:,.0f} veces',
        'Participacion_Capital': '{:.2f}%'
    }),
    use_container_width=True,
    hide_index=True
)

# ==============================================================================
# 4. BUSCADOR DINÁMICO BLINDADO
# ==============================================================================
st.markdown("---")
st.subheader("Buscador Dinámico de Trazabilidad y Ubicación por SKU")

lista_codigos = sorted(df_m_f['Codigo'].unique().tolist())
mapa_skus = {}
opciones_combobox = []

for cod in lista_codigos:
    d = desc_map.get(cod, "SIN DESCRIPCION")
    etiqueta = f"{cod} | {d}"
    mapa_skus[etiqueta] = cod
    opciones_combobox.append(etiqueta)

if opciones_combobox:
    opcion_elegida = st.selectbox("Escriba o busque un Código o Descripción de Producto:", opciones_combobox)
    sku_seleccionado = mapa_skus[opcion_elegida]
    
    desc_seleccionada = desc_map.get(sku_seleccionado, "SIN DESCRIPCIÓN")
    um_seleccionada = um_map.get(sku_seleccionado, "UM")
    
    df_almacenes_sku = df_stock[df_stock['Codigo'] == sku_seleccionado].groupby('Almacen').agg(
        Stock_Almacen=('Stock', 'sum'),
        Costo_Promedio=('Costo', 'mean')
    ).reset_index()
    
    df_almacenes_sku['Valorizado_Almacen'] = df_almacenes_sku['Stock_Almacen'] * df_almacenes_sku['Costo_Promedio']
    
    col_info1, col_info2 = st.columns([1, 2])
    
    with col_info1:
        st.markdown(f"**SKU:** `{sku_seleccionado}`")
        st.markdown(f"**Descripción:** {desc_seleccionada}")
        st.markdown(f"**Unidad de Medida:** `{um_seleccionada}`")
        st.metric("Stock Total Consolidado", f"{df_almacenes_sku['Stock_Almacen'].sum():,.0f} {um_seleccionada}")

    with col_info2:
        st.markdown("##### Ubicación y Distribución por Almacén")
        if not df_almacenes_sku.empty:
            st.dataframe(
                df_almacenes_sku.style.format({
                    'Stock_Almacen': '{:,.0f}',
                    'Costo_Promedio': 'S/. {:,.2f}',
                    'Valorizado_Almacen': 'S/. {:,.2f}'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("El código seleccionado no presenta stock activo en la foto del maestro.")

    historial_sku = []
    for mes in meses_historicos:
        datos_mes_hist = saldos_por_mes_sku[mes].get(sku_seleccionado, {'Stock': 0.0, 'Costo': 0.0})
        stk_mes_consolidado = float(datos_mes_hist['Stock'])
        costo_sku = float(datos_mes_hist['Costo'])
        
        historial_sku.append({
            "Mes": mes,
            "Stock Cierre": stk_mes_consolidado,
            "Valorizado Total (S/.)": stk_mes_consolidado * costo_sku,
        })
        
    df_historial_sku = pd.DataFrame(historial_sku)
    
    fig_sku_line = go.Figure()
    fig_sku_line.add_trace(go.Scatter(
        x=df_historial_sku['Mes'], 
        y=df_historial_sku['Valorizado Total (S/.)'],
        mode='lines+markers',
        name="Valorizado (S/.)",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=8, color="#1d4ed8"),
        hovertemplate="<b>Mes:</b> %{x}<br><b>Valorizado:</b> S/. %{y:,.2f}<extra></extra>"
    ))
    
    fig_sku_line.update_layout(
        title=f"Evolución Histórica de Capital Inmovilizado: {sku_seleccionado}",
        plot_bgcolor="white", 
        yaxis=dict(title="Soles (S/.)", gridcolor="#f1f5f9"), 
        xaxis=dict(gridcolor="#f1f5f9"),
        height=350,
        margin=dict(t=50, b=40, l=40, r=40)
    )
    st.plotly_chart(fig_sku_line, use_container_width=True)

# Descarga de Excel
st.markdown("---")
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_evolutivo.to_excel(writer, index=False, sheet_name='Evolutivo_Mensual')
    df_auditoria.to_excel(writer, index=False, sheet_name='Auditoria_Mes')

processed_data = output.getvalue()

st.download_button(
    label="Descargar Reporte Evolutivo en Excel",
    data=processed_data,
    file_name="Reporte_Evolucion_Mensual_Inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)