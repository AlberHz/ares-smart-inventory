import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(
    layout="wide", 
    page_title="KPI 3 - ANÁLISIS ABC",
    page_icon="📦"
)

# ==============================================================================
# ESTILOS GLOBALES CSS
# ==============================================================================
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 900;
        color: #0f172a;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-card {
        background-color: white; 
        border: 1px solid #e2e8f0; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease-in-out;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .section-header {
        font-size: 18px; 
        font-weight: 800; 
        color: #1e293b; 
        margin-bottom: 8px;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# VALIDACIÓN Y PREPARACIÓN DE DATOS
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio (app.py) para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

# Garantizar existencia de columnas clave
for col in ['Almacen', 'Familia']:
    if col not in df_stock.columns:
        df_stock[col] = 'GENERAL'
    if col not in df_mov.columns:
        df_mov[col] = 'GENERAL'

# Limpieza estandarizada de textos
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_stock['Almacen'] = df_stock['Almacen'].astype(str).str.strip()
df_stock['Familia'] = df_stock['Familia'].astype(str).str.strip()
df_stock['Descripcion'] = df_stock.get('Descripcion', df_stock.get('Item', 'PRODUCTO SIN DETALLE')).astype(str).str.strip()

df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()
df_mov['Almacen'] = df_mov['Almacen'].astype(str).str.strip()

# ==============================================================================
# MOTOR ABC: FRECUENCIA CRUZADA POR [CÓDIGO Y ALMACÉN]
# ==============================================================================
df_ns = df_mov[df_mov['Tipo_Movimiento'].astype(str).str.strip().str.upper() == 'NS']
conteo_frecuencia = df_ns.groupby(['Codigo', 'Almacen']).size().reset_index(name='frecuencia_pedidos')

# Cruce exacto de Stock y Frecuencia
df_abc = df_stock[df_stock['Stock'] > 0].copy()
df_abc = pd.merge(df_abc, conteo_frecuencia, on=['Codigo', 'Almacen'], how='left')
df_abc['frecuencia_pedidos'] = df_abc['frecuencia_pedidos'].fillna(0).astype(int)
df_abc['valor_total'] = df_abc['Stock'] * df_abc['Costo']

# Ordenamiento descendente y cálculo Pareto
df_abc = df_abc.sort_values(by='frecuencia_pedidos', ascending=False).reset_index(drop=True)
total_pedidos_global = df_abc['frecuencia_pedidos'].sum()

if total_pedidos_global > 0:
    df_abc['porcentaje_frecuencia'] = (df_abc['frecuencia_pedidos'] / total_pedidos_global) * 100
    df_abc['frecuencia_acumulada'] = df_abc['frecuencia_pedidos'].cumsum() / total_pedidos_global * 100
else:
    df_abc['porcentaje_frecuencia'] = 0
    df_abc['frecuencia_acumulada'] = 0

def clasificar_abc(acum):
    if acum <= 80.001: return 'A'
    elif acum <= 95.001: return 'B'
    else: return 'C'

df_abc['clasificacion_abc'] = df_abc['frecuencia_acumulada'].apply(clasificar_abc)

def perfil_estrategico(row):
    if row['clasificacion_abc'] == 'A' and row['valor_total'] > 15000:
        return 'Crítico: Alta Rotación y Alta Inversión. Requiere JIT.'
    elif row['clasificacion_abc'] == 'A' and row['valor_total'] <= 15000:
        return 'Operativo Alto: Mucho movimiento físico, bajo costo unitario.'
    elif row['clasificacion_abc'] == 'C' and row['valor_total'] > 25000:
        return 'Riesgo Inmovilizado: Poca rotación pero mucho dinero estancado.'
    else:
        return 'Estándar: Control mensual de existencias.'

df_abc['perfil_estrategico'] = df_abc.apply(perfil_estrategico, axis=1)

# ==============================================================================
# ENCABEZADO Y FILTROS GLOBALES SUPERIORES (ESTILO UNIFICADO)
# ==============================================================================
st.markdown("<h1 style='color: #1e293b; font-weight: 800; font-size: 60px; margin-bottom: 2px;'>KPI 3 - CLASIFICACION ABC-(PARETO)</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 20px;'>Filtra y analiza la carga operativa y valorización de tu inventario.</p>", unsafe_allow_html=True)

lista_almacenes = sorted(df_abc['Almacen'].unique().tolist())
lista_familias = sorted(df_abc['Familia'].unique().tolist())

with st.container():
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        almacen_filtro = st.selectbox("FILTRO ALMACÉN", ["TODOS LOS ALMACENES"] + lista_almacenes)
    with col_f2:
        familia_filtro = st.selectbox("FILTRO FAMILIA", ["TODAS LAS FAMILIAS"] + lista_familias)
    with col_f3:
        abc_filtro = st.selectbox(" BLOQUE ABC", ["TODAS LAS CLASES", "🟥 CLASE A (80% Pedidos)", "🟨 CLASE B (15% Pedidos)", "🟩 CLASE C (5% Pedidos)"])

# Aplicación de filtros interactivos
df_filtrado = df_abc.copy()

if almacen_filtro != "TODOS LOS ALMACENES":
    df_filtrado = df_filtrado[df_filtrado['Almacen'] == almacen_filtro]

if familia_filtro != "TODAS LAS FAMILIAS":
    df_filtrado = df_filtrado[df_filtrado['Familia'] == familia_filtro]

if "CLASE A" in abc_filtro:
    df_filtrado = df_filtrado[df_filtrado['clasificacion_abc'] == 'A']
elif "CLASE B" in abc_filtro:
    df_filtrado = df_filtrado[df_filtrado['clasificacion_abc'] == 'B']
elif "CLASE C" in abc_filtro:
    df_filtrado = df_filtrado[df_filtrado['clasificacion_abc'] == 'C']

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# TARJETAS DE CONCENTRACIÓN ABC POR ALMACÉN
# ==============================================================================
st.markdown("<div class='section-header'>Concentración de Inventario ABC por Tipo de Almacén</div>", unsafe_allow_html=True)

cols_cards = st.columns(len(lista_almacenes) if len(lista_almacenes) > 0 else 1)

for idx, nom_almacen in enumerate(lista_almacenes):
    df_alm_kpi = df_abc[df_abc['Almacen'] == nom_almacen]
    if familia_filtro != "TODAS LAS FAMILIAS":
        df_alm_kpi = df_alm_kpi[df_alm_kpi['Familia'] == familia_filtro]
        
    total_skus = len(df_alm_kpi)
    total_valor = df_alm_kpi['valor_total'].sum()
    cA = len(df_alm_kpi[df_alm_kpi['clasificacion_abc'] == 'A'])
    cB = len(df_alm_kpi[df_alm_kpi['clasificacion_abc'] == 'B'])
    cC = len(df_alm_kpi[df_alm_kpi['clasificacion_abc'] == 'C'])
    
    es_seleccionado = (almacen_filtro == "TODOS LOS ALMACENES" or almacen_filtro == nom_almacen)
    opacity = "1.0" if es_seleccionado else "0.5"
    border_left = "5px solid #3b82f6" if (almacen_filtro == nom_almacen) else "1px solid #e2e8f0"
    
    with cols_cards[idx]:
        card_html = f"""
        <div class="kpi-card" style="border-left: {border_left}; opacity: {opacity}; min-height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
                <span style="font-weight: 900; font-size: 13px; color: #0f172a; text-transform: uppercase;">{nom_almacen.replace('_',' ')}</span>
                <span style="font-size: 11px; font-family: monospace; color: #64748b; background-color: #f8fafc; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{total_skus} SKUs</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center; margin-top: 10px; margin-bottom: 10px;">
                <div style="background-color: #fef2f2; padding: 6px; border-radius: 8px; border: 1px solid #fee2e2;">
                    <span style="font-size: 10px; font-weight: 800; color: #ef4444; display: block; margin-bottom: 2px;">CLASE A</span>
                    <span style="font-size: 14px; font-weight: 900; color: #991b1b;">{cA}</span>
                </div>
                <div style="background-color: #fffbeb; padding: 6px; border-radius: 8px; border: 1px solid #fef3c7;">
                    <span style="font-size: 10px; font-weight: 800; color: #d97706; display: block; margin-bottom: 2px;">CLASE B</span>
                    <span style="font-size: 14px; font-weight: 900; color: #92400e;">{cB}</span>
                </div>
                <div style="background-color: #f0fdf4; padding: 6px; border-radius: 8px; border: 1px solid #dcfce3;">
                    <span style="font-size: 10px; font-weight: 800; color: #16a34a; display: block; margin-bottom: 2px;">CLASE C</span>
                    <span style="font-size: 14px; font-weight: 900; color: #166534;">{cC}</span>
                </div>
            </div>
            <div style="text-align: right; border-top: 1px dashed #e2e8f0; padding-top: 6px;">
                <span style="font-size: 10px; color: #94a3b8; display: block; font-weight: 600;">INVERSIÓN STOCK VINCULADO</span>
                <span style="font-size: 13px; font-weight: 900; color: #334155;">S/. {total_valor:,.0f}</span>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# ==============================================================================
# PESTAÑAS PRINCIPALES (3 PESTAÑAS)
# ==============================================================================
tabs = st.tabs([
    "CUADRO PARETO OPERATIVO", 
    "RESUMEN POR FAMILIAS", 
    f"LISTA DE PRODUCTOS ({len(df_filtrado)})"
])

total_pedidos_universo = df_filtrado['frecuencia_pedidos'].sum()
valor_total_inventario = df_filtrado['valor_total'].sum()

# ------------------------------------------------------------------------------
# PESTAÑA 1: CUADRO PARETO OPERATIVO Y VALORIZACIÓN
# ------------------------------------------------------------------------------
with tabs[0]:
    k1, k2, k3 = st.columns(3)
    k1.metric("CARGA OPERATIVA TOTAL", f"{total_pedidos_universo:,} Pedidos")
    k2.metric("VALORIZACIÓN DE STOCK", f"S/. {valor_total_inventario:,.2f}")
    
    df_clase_a = df_filtrado[df_filtrado['clasificacion_abc'] == 'A']
    porc_mov_a = (df_clase_a['frecuencia_pedidos'].sum() / total_pedidos_universo * 100) if total_pedidos_universo > 0 else 0
    k3.metric("CONCENTRACIÓN DE CARGA (CLASE A)", f"{porc_mov_a:.1f}% del Movimiento")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    resumen_abc_list = []
    colores_map = {'A': '#ef4444', 'B': '#eab308', 'C': '#10b981'}
    
    for cat in ['A', 'B', 'C']:
        df_cat = df_filtrado[df_filtrado['clasificacion_abc'] == cat]
        skus_cat = len(df_cat)
        pedidos_cat = df_cat['frecuencia_pedidos'].sum()
        valor_cat = df_cat['valor_total'].sum()
        
        resumen_abc_list.append({
            "Zona Pareto": f"Clase {cat}",
            "N° SKUs": skus_cat,
            "% SKUs": (skus_cat / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0,
            "Volumen Pedidos": pedidos_cat,
            "% Frecuencia (Rotación)": (pedidos_cat / total_pedidos_universo * 100) if total_pedidos_universo > 0 else 0,
            "Valorización del Inventario": valor_cat
        })
        
    df_res_table = pd.DataFrame(resumen_abc_list)
    
    st.dataframe(
        df_res_table.style.format({
            'N° SKUs': '{:,}',
            '% SKUs': '{:.1f}%',
            'Volumen Pedidos': '{:,.0f}',
            '% Frecuencia (Rotación)': '{:.2f}%',
            'Valorización del Inventario': 'S/. {:,.2f}'
        }).set_properties(**{'background-color': '#fafafa', 'color': '#1e293b', 'border-color': '#e2e8f0'})
          .map(lambda x: 'background-color: #fef2f2; font-weight: bold; color: #ef4444;' if 'A' in str(x) else ('background-color: #fffbeb; font-weight: bold; color: #d97706;' if 'B' in str(x) else ('background-color: #f0fdf4; font-weight: bold; color: #16a34a;' if 'C' in str(x) else '')), subset=['Zona Pareto']),
        use_container_width=True, hide_index=True
    )
    
    st.markdown("<br><hr style='border-color: #f1f5f9; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # 1. PARETO POR CARGA OPERATIVA (DESPACHOS)
    st.markdown("<div class='section-header'>Top 20 SKUs por Despachos</div>", unsafe_allow_html=True)
    
    top_20_ops = df_filtrado.sort_values(by='frecuencia_pedidos', ascending=False).head(20).copy()
    
    if not top_20_ops.empty:
        top_20_ops['Codigo_Str'] = top_20_ops['Codigo'].astype(str)
        colores_barras_ops = [colores_map.get(x, '#64748b') for x in top_20_ops['clasificacion_abc']]
        
        fig_pareto_ops = go.Figure()
        fig_pareto_ops.add_trace(go.Bar(
            x=top_20_ops['Codigo_Str'], 
            y=top_20_ops['frecuencia_pedidos'],
            name="Despachos",
            marker_color=colores_barras_ops,
            text=top_20_ops['frecuencia_pedidos'].apply(lambda x: f"<b>{x:,} desp.</b>"),
            textposition='outside',
            textfont=dict(size=10, color="#0f172a"),
            customdata=top_20_ops[['Codigo', 'Descripcion', 'Almacen', 'clasificacion_abc', 'valor_total']].values.tolist(),
            hovertemplate="<b>SKU:</b> %{customdata[0]}<br><b>Descripción:</b> %{customdata[1]}<br><b>Almacén:</b> %{customdata[2]}<br><b>Clase:</b> %{customdata[3]}<br><b>Despachos:</b> %{y:,}<br><b>Valor Total:</b> S/. %{customdata[4]:,.2f}<extra></extra>"
        ))
        
        fig_pareto_ops.update_layout(
            plot_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=50),
            height=430,
            showlegend=False
        )
        fig_pareto_ops.update_xaxes(type='category', tickangle=-45, tickfont=dict(size=11, color="#334155"))
        fig_pareto_ops.update_yaxes(title_text="Cantidad de Pedidos", gridcolor="#f1f5f9")
        st.plotly_chart(fig_pareto_ops, use_container_width=True)

    st.markdown("<br><hr style='border-color: #f1f5f9; margin: 20px 0;'>", unsafe_allow_html=True)

    # 2. PARETO POR VALORIZACIÓN TOTAL DEL INVENTARIO
    st.markdown("<div class='section-header'>Top 20 SKUs por Valor Total</div>", unsafe_allow_html=True)
    
    top_20_val = df_filtrado.sort_values(by='valor_total', ascending=False).head(20).copy()
    
    if not top_20_val.empty:
        top_20_val['Codigo_Str'] = top_20_val['Codigo'].astype(str)
        colores_barras_val = [colores_map.get(x, '#64748b') for x in top_20_val['clasificacion_abc']]
        
        fig_pareto_val = go.Figure()
        fig_pareto_val.add_trace(go.Bar(
            x=top_20_val['Codigo_Str'], 
            y=top_20_val['valor_total'],
            name="Valor Total",
            marker_color=colores_barras_val,
            text=top_20_val['valor_total'].apply(lambda x: f"<b>S/. {x:,.0f}</b>"),
            textposition='outside',
            textfont=dict(size=10, color="#0f172a"),
            customdata=top_20_val[['Codigo', 'Descripcion', 'Almacen', 'clasificacion_abc', 'frecuencia_pedidos']].values.tolist(),
            hovertemplate="<b>SKU:</b> %{customdata[0]}<br><b>Descripción:</b> %{customdata[1]}<br><b>Almacén:</b> %{customdata[2]}<br><b>Clase:</b> %{customdata[3]}<br><b>Valor Total:</b> S/. %{y:,.2f}<br><b>Despachos:</b> %{customdata[4]:,}<extra></extra>"
        ))
        
        fig_pareto_val.update_layout(
            plot_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=50),
            height=430,
            showlegend=False
        )
        fig_pareto_val.update_xaxes(type='category', tickangle=-45, tickfont=dict(size=11, color="#334155"))
        fig_pareto_val.update_yaxes(title_text="Valor Total del Stock (S/.)", gridcolor="#f1f5f9")
        st.plotly_chart(fig_pareto_val, use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: RESUMEN POR FAMILIAS
# ------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("<div class='section-header'>Análisis de Pareto por Familias</div>", unsafe_allow_html=True)
    
    mapa_familias = df_filtrado.groupby('Familia').agg(
        skus=('Codigo', 'count'),
        total_pedidos=('frecuencia_pedidos', 'sum'),
        valorizacion=('valor_total', 'sum'),
        conteoA=('clasificacion_abc', lambda x: (x == 'A').sum()),
        conteoB=('clasificacion_abc', lambda x: (x == 'B').sum()),
        conteoC=('clasificacion_abc', lambda x: (x == 'C').sum())
    ).reset_index().sort_values(by='total_pedidos', ascending=False)
    
    if not mapa_familias.empty:
        fig_fam = go.Figure()
        fig_fam.add_trace(go.Bar(
            x=mapa_familias['Familia'],
            y=mapa_familias['total_pedidos'],
            name="Despachos por Familia",
            marker_color="#6366f1",
            text=mapa_familias['total_pedidos'],
            textposition='outside',
            textfont=dict(size=11, color="#4338ca", weight="bold"),
            hovertemplate="<b>Familia:</b> %{x}<br><b>Despachos:</b> %{y}<extra></extra>"
        ))
        fig_fam.update_layout(plot_bgcolor="white", height=400, margin=dict(l=40, r=40, t=30, b=80), showlegend=False)
        fig_fam.update_xaxes(tickangle=-35, tickfont=dict(size=11))
        fig_fam.update_yaxes(gridcolor="#f1f5f9")
        st.plotly_chart(fig_fam, use_container_width=True)
        
    st.markdown("<br><div class='section-header'>Resumen por Familias</div>", unsafe_allow_html=True)
    
    st.dataframe(
        mapa_familias.rename(columns={
            'Familia': 'Familia Contable / Comercial',
            'skus': 'Cant SKUs',
            'total_pedidos': 'Frecuencia Total Pedidos',
            'valorizacion': 'Capital Invertido (Stock)',
            'conteoA': 'SKUs Clase A',
            'conteoB': 'SKUs Clase B',
            'conteoC': 'SKUs Clase C'
        }).style.format({
            'Cant SKUs': '{:,}',
            'Frecuencia Total Pedidos': '{:,.0f}',
            'Capital Invertido (Stock)': 'S/. {:,.2f}',
            'SKUs Clase A': '{:,}',
            'SKUs Clase B': '{:,}',
            'SKUs Clase C': '{:,}'
        }),
        use_container_width=True, hide_index=True
    )

# ------------------------------------------------------------------------------
# PESTAÑA 3: LISTA DE PRODUCTOS
# ------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("<div class='section-header'>Catalogo de Codigos con Rotación</div>", unsafe_allow_html=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name='REPORTE_ABC_PARETO')
    processed_data = output.getvalue()
    
    st.download_button(
        label="Descargar Base ABC Frecuencia (.XLSX)",
        data=processed_data,
        file_name="REPORTE_ABC_FRECUENCIA_PARETO.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_maestro_visual = df_filtrado[[
        'clasificacion_abc', 'Codigo', 'Descripcion', 'Familia', 'Almacen', 'frecuencia_pedidos', 'valor_total', 'frecuencia_acumulada', 'perfil_estrategico'
    ]].rename(columns={
        'clasificacion_abc': 'Clase',
        'frecuencia_pedidos': 'Frec. Pedidos',
        'valor_total': 'Valor Stock',
        'frecuencia_acumulada': '% Acum. Pedidos',
        'perfil_estrategico': 'Observaciones'
    })
    
    def color_clase(val):
        if val == 'A': return 'background-color: #ef4444; color: white; font-weight: bold; text-align: center;'
        elif val == 'B': return 'background-color: #f59e0b; color: white; font-weight: bold; text-align: center;'
        elif val == 'C': return 'background-color: #10b981; color: white; font-weight: bold; text-align: center;'
        return ''

    st.dataframe(
        df_maestro_visual.style.format({
            'Frec. Pedidos': '{:,}',
            'Valor Stock': 'S/. {:,.2f}',
            '% Acum. Pedidos': '{:.2f}%'
        }).map(color_clase, subset=['Clase']),
        use_container_width=True, hide_index=True, height=500
    )