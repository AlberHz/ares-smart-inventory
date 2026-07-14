import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(layout="wide")

# ==============================================================================
# VALIDACIÓN DE CONTENEDORES EN MEMORIA
# ==============================================================================
if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio (app.py) para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_mov = st.session_state['df_mov'].copy()

# Limpieza estandarizada de columnas comunes
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()
df_stock['Descripcion'] = df_stock.get('Descripcion', df_stock.get('Item', 'PRODUCTO SIN DETALLE')).astype(str).str.strip()
df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip()

# ==============================================================================
# MOTOR OPTIMIZADO: CACHÉ DE FRECUENCIA PARA EVITAR LENTITUD
# ==============================================================================
if 'conteo_frecuencia_cache' not in st.session_state:
    df_ns = df_mov[df_mov['Tipo_Movimiento'].astype(str).str.strip().str.upper() == 'NS']
    st.session_state['conteo_frecuencia_cache'] = df_ns.groupby('Codigo').size().reset_index(name='frecuencia_pedidos')

conteo_frecuencia = st.session_state['conteo_frecuencia_cache']

# LEFT JOIN e indicadores operativos básicos
df_abc = df_stock[df_stock['Stock'] > 0].copy()
df_abc = pd.merge(df_abc, conteo_frecuencia, on='Codigo', how='left')
df_abc['frecuencia_pedidos'] = df_abc['frecuencia_pedidos'].fillna(0).astype(int)
df_abc['valor_total'] = df_abc['Stock'] * df_abc['Costo']

# Clasificación y ordenamiento secuencial descendente
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
        return '🔥 Crítico: Alta Rotación y Alta Inversión. Requiere JIT.'
    elif row['clasificacion_abc'] == 'A' and row['valor_total'] <= 15000:
        return '⚡ Operativo Alto: Mucho movimiento físico, bajo costo unitario.'
    elif row['clasificacion_abc'] == 'C' and row['valor_total'] > 25000:
        return '⚠️ Riesgo Inmovilizado: Poca rotación pero mucho dinero estancado.'
    else:
        return '📦 Estándar: Control mensual de existencias.'

df_abc['perfil_estrategico'] = df_abc.apply(perfil_estrategico, axis=1)

# ==============================================================================
# FILTROS GLOBALES SUPERIORES
# ==============================================================================
lista_almacenes = sorted(df_abc['Almacen'].unique().tolist())
lista_familias = sorted(df_abc['Familia'].unique().tolist())

with st.container():
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        almacen_filtro = st.selectbox("FILTRO ALMACÉN", ["TODOS LOS ALMACENES"] + lista_almacenes)
    with col_f2:
        familia_filtro = st.selectbox("FILTRO FAMILIA", ["TODAS LAS FAMILIAS"] + lista_familias)
    with col_f3:
        abc_filtro = st.selectbox("BLOQUE ABC", ["CLASIFICACION", "🟥 CLASE A (80% Pedidos)", "🟨 CLASE B (15% Pedidos)", "🟩 CLASE C (5% Pedidos)"])

# Aplicación reactiva de los filtros cruzados
df_filtrado = df_abc.copy()
if almacen_filtro != "TODOS LOS ALMACENES":
    df_filtrado = df_filtrado[df_filtrado['Almacen'] == almacen_filtro]
if familia_filtro != "TODAS LAS FAMILIAS":
    df_filtrado = df_filtrado[df_filtrado['Familia'] == familia_filtro]
if abc_filtro != "CLASIFICACION":
    letra_abc = abc_filtro[2]
    df_filtrado = df_filtrado[df_filtrado['clasificacion_abc'] == letra_abc]

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# TARJETAS DE CONCENTRACIÓN ABC POR ALMACÉN
# ==============================================================================
st.markdown("<h5 style='color: #94a3b8; font-weight: bold; font-size: 13px; text-transform: uppercase;'>Concentración de Inventario ABC por Tipo de Almacén Real</h5>", unsafe_allow_html=True)

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
    opacity = "1.0" if es_seleccionado else "0.4"
    border_left = "4px solid #2563eb" if (almacen_filtro == nom_almacen) else "1px solid #e2e8f0"
    
    with cols_cards[idx]:
        card_html = f"""
        <div style="background-color: white; border: 1px solid #e2e8f0; border-left: {border_left}; padding: 15px; border-radius: 16px; opacity: {opacity}; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); min-height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                <span style="font-weight: 900; font-size: 12px; color: #0f172a; text-transform: uppercase;">{nom_almacen.replace('_',' ')}</span>
                <span style="font-size: 11px; font-family: monospace; color: #94a3b8; font-weight: bold;">{total_skus} SKUs</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; text-align: center; margin-top: 8px; margin-bottom: 8px;">
                <div style="background-color: #fef2f2; padding: 4px; border-radius: 8px;">
                    <span style="font-size: 10px; font-weight: bold; color: #ef4444; display: block;">CLASE A</span>
                    <span style="font-size: 12px; font-weight: 900; color: #991b1b;">{cA}</span>
                </div>
                <div style="background-color: #fffbeb; padding: 4px; border-radius: 8px;">
                    <span style="font-size: 10px; font-weight: bold; color: #d97706; display: block;">CLASE B</span>
                    <span style="font-size: 12px; font-weight: 900; color: #92400e;">{cB}</span>
                </div>
                <div style="background-color: #f0fdf4; padding: 4px; border-radius: 8px;">
                    <span style="font-size: 10px; font-weight: bold; color: #16a34a; display: block;">CLASE C</span>
                    <span style="font-size: 12px; font-weight: 900; color: #166534;">{cC}</span>
                </div>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 10px; color: #94a3b8; display: block; font-weight: 500;">Inversión Stock Vinculado</span>
                <span style="font-size: 12px; font-weight: bold; color: #334155;">S/. {total_valor:,.0f}</span>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# PESTAÑAS INTERACTIVAS
# ==============================================================================
tabs = st.tabs([
    "📊 CUADRO PARETO OPERATIVO", 
    "📂 RESUMEN POR FAMILIAS", 
    f"📝 LISTA DE PRODUCTOS ({len(df_filtrado)})", 
    "🔍 CONSULTOR DE CÓDIGO"
])

total_pedidos_universo = df_filtrado['frecuencia_pedidos'].sum()
valor_total_inventario = df_filtrado['valor_total'].sum()

# ------------------------------------------------------------------------------
# PESTAÑA 1: CUADRO PARETO OPERATIVO
# ------------------------------------------------------------------------------
with tabs[0]:
    k1, k2, k3 = st.columns(3)
    k1.metric("CARGA OPERATIVA TOTAL", f"{total_pedidos_universo:,} Pedidos")
    k2.metric("VALORIZACIÓN DE STOCK VINCULADO", f"S/. {valor_total_inventario:,.2f}")
    
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
            '% Frecuencia (Rotación)': '{:.1f}%',
            'Valorización del Inventario': 'S/. {:,.2f}'
        }),
        use_container_width=True, hide_index=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Curva de Carga Operativa Pareto (Top 20 SKUs)</h6>", unsafe_allow_html=True)
    top_20 = df_filtrado.head(20).copy()
    
    if not top_20.empty:
        top_20['Codigo_Str'] = top_20['Codigo'].astype(str)
        
        fig_pareto = go.Figure()
        colores_barras = [colores_map[x] for x in top_20['clasificacion_abc']]
        
        fig_pareto.add_trace(go.Bar(
            x=top_20['Codigo_Str'], 
            y=top_20['frecuencia_pedidos'],
            name="Despachos (Frecuencia)",
            marker_color=colores_barras,
            text=top_20['frecuencia_pedidos'],
            textposition='outside',
            textfont=dict(size=10, color="#334155", weight="bold"),
            hovertemplate="SKU: %{x}<br>Despachos: %{y}<extra></extra>"
        ))
        
        fig_pareto.update_layout(
            plot_bgcolor="white",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=30, b=50),
            height=380,
            showlegend=False
        )
        # 🛠️ CORRECCIÓN AQUÍ: Cambiado 'fontfamily' por 'family' para solucionar el Bug
        fig_pareto.update_xaxes(type='category', tickangle=-45, tickfont=dict(size=10, family="monospace"))
        fig_pareto.update_yaxes(title_text="ped", gridcolor="#f1f5f9")
        st.plotly_chart(fig_pareto, use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: RESUMEN POR FAMILIAS
# ------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Análisis de Pareto por Familias Comerciales / Contables</h6>", unsafe_allow_html=True)
    
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
            marker_color="#7c3aed",
            text=mapa_familias['total_pedidos'],
            textposition='outside',
            textfont=dict(size=10, color="#4c1d95", weight="bold"),
            hovertemplate="Familia: %{x}<br>Despachos: %{y}<extra></extra>"
        ))
        fig_fam.update_layout(plot_bgcolor="white", height=360, margin=dict(l=40, r=40, t=30, b=60), showlegend=False)
        fig_fam.update_xaxes(tickangle=-30, tickfont=dict(size=10))
        fig_fam.update_yaxes(gridcolor="#f1f5f9")
        st.plotly_chart(fig_fam, use_container_width=True)
        
    st.markdown("<br><h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Resumen Estratégico Concentrado por Familias</h6>", unsafe_allow_html=True)
    
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
    st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Maestro General de Rotación</h6>", unsafe_allow_html=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name='REPORTE_ABC_PARETO')
    processed_data = output.getvalue()
    
    st.download_button(
        label="📥 Descargar Base ABC Frecuencia (.XLSX)",
        data=processed_data,
        file_name="REPORTE_ABC_FRECUENCIA_PARETO.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_maestro_visual = df_filtrado[[
        'clasificacion_abc', 'Codigo', 'Descripcion', 'Familia', 'Almacen', 'frecuencia_pedidos', 'valor_total', 'frecuencia_acumulada', 'perfil_estrategico'
    ]].rename(columns={
        'clasificacion_abc': 'Clase',
        'frecuencia_pedidos': 'Frec. Pedidos',
        'valor_total': 'Valor Stock',
        'frecuencia_acumulada': '% Acum. Pedidos',
        'perfil_estrategico': 'Perfil Estratégico Gerencial'
    })
    
    st.dataframe(
        df_maestro_visual.style.format({
            'Frec. Pedidos': '{:,}',
            'Valor Stock': 'S/. {:,.2f}',
            '% Acum. Pedidos': '{:.2f}%'
        }),
        use_container_width=True, hide_index=True
    )

# ------------------------------------------------------------------------------
# PESTAÑA 4: CONSULTOR DE CÓDIGO
# ------------------------------------------------------------------------------
with tabs[3]:
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.markdown("<h6 style='font-size:14px; font-weight:bold; color:#0f172a;'>Auditoría de Código Específico</h6>", unsafe_allow_html=True)
        st.write("Busca cualquier SKU activo para auditar su nivel de rotación.")
        
        busqueda_codigo = st.text_input("INGRESE CÓDIGO DEL SKU").strip()
        consultar_clicked = st.button("Consultar Indicadores", use_container_width=True)
        
    with c_right:
        if busqueda_codigo or consultar_clicked:
            sku_encontrado = df_abc[df_abc['Codigo'].str.lower() == busqueda_codigo.lower()]
            
            if not sku_encontrado.empty:
                prod = sku_encontrado.iloc[0]
                
                st.markdown(f"""
                <div style="border-bottom: 1px solid #e2e8f0; padding-bottom:12px; margin-bottom:15px;">
                    <span style="font-family:monospace; font-weight:900; color:#b45309; background-color:#fffbeb; padding:4px 8px; border-radius:6px; font-size:12px;">SKU: {prod['Codigo']}</span>
                    <h3 style="font-weight:900; color:#0f172a; margin-top:8px; font-size:18px;">{prod['Descripcion']}</h3>
                    <div style="margin-top: 8px;"><span style="background-color: #ef4444; color:white; font-weight:900; font-size:11px; padding:6px 12px; border-radius:10px;">Clase {prod['clasificacion_abc']} por Frecuencia</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Frecuencia Pedidos", f"{int(prod['frecuencia_pedidos'])} despachos")
                m2.metric("Stock Actual", f"{int(prod['Stock']):,} und")
                m3.metric("Costo Unitario", f"S/. {prod['Costo']:.2f}")
                m4.metric("Valorizado Total", f"S/. {prod['valor_total']:,.2f}")
                
                st.markdown(f"""
                <div style="border: 1px solid #e2e8f0; padding:15px; border-radius:12px; background-color:#fafafa; margin-top:15px;">
                    <h5 style="margin:0 0 8px 0; font-size:12px; font-weight:bold; color:#1e293b;">Diagnóstico Logístico:</h5>
                    <p style="margin:4px 0; font-size:12px; color:#475569;"><strong style="color:#0f172a;">Ubicación Actual:</strong> Almacén {prod['Almacen']} - Línea de {prod['Familia']}.</p>
                    <p style="margin:4px 0; font-size:12px; color:#475569;"><strong style="color:#0f172a;">Estrategia Gerencial Sugerida:</strong> {prod['perfil_estrategico']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("El código de producto ingresado no existe en el catálogo actual de existencias.")
        else:
            st.write("Ingrese un código de SKU válido a la izquierda (ej. 31800113) para cargar la auditoría instantánea.")