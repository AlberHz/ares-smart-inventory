import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(
    layout="wide", 
    page_title="KPI 1 - INVENTARIO VALORIZADO",
    page_icon="📦"
)

if 'df_stock' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()

st.title("KPI 1 - Inventario Valorizado - Foto Actual")
st.markdown("---")

# ==============================================================================
# FILTROS EN CASCADA ESTRICTOS Y DINÁMICOS EN BARRA LATERAL
# ==============================================================================
st.sidebar.header("Filtros")

# 1. Filtro Almacén
list_alm = ["TODOS"] + sorted(df_stock['ALMACEN'].dropna().unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtro de Almacén", list_alm)

# Filtrado inicial por Almacén
df_step1 = df_stock.copy()
if filtro_alm != "TODOS":
    df_step1 = df_step1[df_step1['ALMACEN'] == filtro_alm]

# 2. Filtro Familia (Solo familias del Almacén seleccionado)
list_fam = ["TODOS"] + sorted(df_step1['FAMILIA'].dropna().unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtro de Familia", list_fam)

# DataFrame Final
df_f = df_step1.copy()
if filtro_fam != "TODOS" and filtro_fam in list_fam:
    df_f = df_f[df_f['FAMILIA'] == filtro_fam]

# ==============================================================================
# KPIS PRINCIPALES
# ==============================================================================
total_capital = df_f['Valor_Total'].sum()
total_unidades = df_f['STOCK'].sum()
total_skus = df_f['CODIGO'].nunique() if 'CODIGO' in df_f.columns else len(df_f)
costo_promedio_unidad = total_capital / total_unidades if total_unidades > 0 else 0

if not df_f.empty and 'Valor_Total' in df_f.columns:
    col_sku_name = 'DESCRIPCIÓN' if 'DESCRIPCIÓN' in df_f.columns else ('DESCRIPCION' if 'DESCRIPCION' in df_f.columns else 'CODIGO')
    top_sku_row = df_f.sort_values(by='Valor_Total', ascending=False).iloc[0]
    top_sku_nombre = str(top_sku_row[col_sku_name])[:22] + "..." if len(str(top_sku_row[col_sku_name])) > 22 else str(top_sku_row[col_sku_name])
    top_sku_val = top_sku_row['Valor_Total']
    pct_top_sku = (top_sku_val / total_capital) * 100 if total_capital > 0 else 0
else:
    top_sku_nombre, top_sku_val, pct_top_sku = "N/A", 0, 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Capital Total", f"S/. {total_capital / 1000:,.2f} K", f"S/. {total_capital:,.2f}")
kpi2.metric("Cantidad de Unidades", f"{total_unidades:,.0f} UM", f"{total_skus:,.0f} SKUs Únicos")
kpi3.metric("Valor Promedio / Unidad", f"S/. {costo_promedio_unidad:,.2f}", "Costo Unitario Medio")
kpi4.metric("SKU con Mayor Concentración", f"S/. {top_sku_val / 1000:,.1f} K", f"{pct_top_sku:.1f}% del capital ({top_sku_nombre})")

st.markdown("---")

# ==============================================================================
# BLOQUE 1: DONA Y TOP 10 CON ESPACIOS AMPLIOS (FILA 1)
# ==============================================================================
cg1, cg2 = st.columns([4, 6])

with cg1:
    st.subheader("Inventario Valorizado por Almacén")
    df_g_alm = df_f.groupby('ALMACEN')['Valor_Total'].sum().reset_index()
    
    paleta_almacen = px.colors.qualitative.Dark24
    
    fig_alm = px.pie(
        df_g_alm, 
        values='Valor_Total', 
        names='ALMACEN', 
        hole=0.5,
        color_discrete_sequence=paleta_almacen
    )
    fig_alm.update_traces(
        textposition='inside',
        textinfo='percent', 
        hovertemplate="<b>%{label}</b><br>Monto: S/. %{value:,.2f}<br>Participación: %{percent}<extra></extra>"
    )
    fig_alm.update_layout(
        margin=dict(t=20, b=20, l=10, r=10), 
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_alm, use_container_width=True)

with cg2:
    st.subheader("Top 10 SKUs de Mayor Concentración de Capital")
    col_prod = 'DESCRIPCIÓN' if 'DESCRIPCIÓN' in df_f.columns else ('DESCRIPCION' if 'DESCRIPCION' in df_f.columns else 'CODIGO')
    
    df_top10 = df_f.groupby([col_prod, 'FAMILIA'])['Valor_Total'].sum().reset_index()
    df_top10 = df_top10.sort_values(by='Valor_Total', ascending=False).head(10)
    df_top10 = df_top10.sort_values(by='Valor_Total', ascending=True)

    df_top10['Monto_Formateado'] = df_top10['Valor_Total'].apply(lambda x: f"S/. {x/1000:,.1f}K")

    fig_top10 = px.bar(
        df_top10,
        x='Valor_Total',
        y=col_prod,
        orientation='h',
        text='Monto_Formateado',
        color='Valor_Total',
        color_continuous_scale='sunsetdark',
        labels={'Valor_Total': 'Valor Total (S/.)', col_prod: ''}
    )
    fig_top10.update_traces(
        textposition='outside',
        textfont=dict(size=11, color='black'),
        hovertemplate="<b>%{y}</b><br>Monto Inmovilizado: S/. %{x:,.2f}<extra></extra>"
    )
    
    max_val_top10 = df_top10['Valor_Total'].max() * 1.25 if not df_top10.empty else 100
    
    fig_top10.update_layout(
        coloraxis_showscale=False,
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9', range=[0, max_val_top10]),
        yaxis=dict(dtick=1, tickfont=dict(size=11)),
        height=400,
        margin=dict(t=10, b=10, l=10, r=120)
    )
    st.plotly_chart(fig_top10, use_container_width=True)

# ==============================================================================
# BLOQUE 2: TREEMAP DE CAPITAL POR ALMACÉN Y FAMILIA
# ==============================================================================
st.markdown("---")
st.subheader("Desglose de Capital por Almacén y Familia")

path_tree = ['ALMACEN', 'FAMILIA']

df_tree_data = df_f.groupby(path_tree).agg(
    Valor_Total=('Valor_Total', 'sum'),
    Stock=('STOCK', 'sum')
).reset_index()

fig_tree = px.treemap(
    df_tree_data,
    path=path_tree,
    values='Valor_Total',
    color='Valor_Total',
    color_continuous_scale='viridis'
)

fig_tree.update_traces(
    hovertemplate="<b>Nivel: %{label}</b><br>" +
                  "Estructura Padre: %{parent}<br>" +
                  "Monto Inmovilizado: <b>S/. %{value:,.2f}</b><br>" +
                  "Aporte al Total: <b>%{percentRoot:.2%}</b><extra></extra>",
    marker=dict(cornerradius=4)
)

fig_tree.update_layout(
    coloraxis_showscale=False,
    margin=dict(t=15, b=15, l=10, r=10), 
    height=520
)
st.plotly_chart(fig_tree, use_container_width=True)

# ==============================================================================
# BLOQUE 3: CONCENTRACIÓN POR FAMILIA
# ==============================================================================
st.markdown("---")
st.subheader("Concentración del Capital por Familia")

df_g_fam = df_f.groupby('FAMILIA')['Valor_Total'].sum().reset_index().sort_values(by='Valor_Total', ascending=True)
df_g_fam['Monto_Formateado'] = df_g_fam['Valor_Total'].apply(lambda x: f"S/. {x/1000:,.1f}K" if x>=1000 else f"S/. {x:,.0f}")

num_familias = len(df_g_fam)
altura_fam = max(450, num_familias * 24)
max_val_fam = df_g_fam['Valor_Total'].max() * 1.30 if not df_g_fam.empty else 100

fig_fam = px.bar(
    df_g_fam, 
    x='Valor_Total', 
    y='FAMILIA', 
    orientation='h',
    text='Monto_Formateado',
    color='Valor_Total', 
    color_continuous_scale='emrld',
    labels={'Valor_Total':''}
)
fig_fam.update_traces(
    textposition='outside',
    textfont=dict(size=11, color='black'),
    hovertemplate="<b>Familia: %{y}</b><br>Monto: S/. %{x:,.2f}<extra></extra>"
)
fig_fam.update_layout(
    coloraxis_showscale=False,
    yaxis=dict(categoryorder='total ascending', type='category', dtick=1, tickfont=dict(size=10)),
    xaxis=dict(showgrid=True, gridcolor='#f1f5f9', range=[0, max_val_fam]),
    showlegend=False,
    height=altura_fam,
    margin=dict(l=150, r=110, t=10, b=20),
    plot_bgcolor='white'
)
st.plotly_chart(fig_fam, use_container_width=True)

# ==============================================================================
# MATRIZ TABULAR AVANZADA
# ==============================================================================
st.markdown("---")
st.subheader("Matriz de Inversión Total")

df_matriz = df_f.groupby(['ALMACEN', 'FAMILIA']).agg(
    Cant_SKUs=('Valor_Total', 'count'),
    Stock_Actual=('STOCK', 'sum'),
    Valor_Total_Soles=('Valor_Total', 'sum')
).reset_index()

df_matriz['Costo_Promedio_Unitario'] = df_matriz['Valor_Total_Soles'] / df_matriz['Stock_Actual']
df_matriz['Representacion_Porcentaje'] = (df_matriz['Valor_Total_Soles'] / total_capital) * 100 if total_capital > 0 else 0
df_matriz = df_matriz.sort_values(by='Valor_Total_Soles', ascending=False)

st.dataframe(
    df_matriz.style.format({
        'Cant_SKUs': '{:,.0f}',
        'Stock_Actual': '{:,.0f}',
        'Valor_Total_Soles': 'S/. {:,.2f}',
        'Costo_Promedio_Unitario': 'S/. {:,.2f}',
        'Representacion_Porcentaje': '{:.2f}%'
    }),
    use_container_width=True,
    hide_index=True
)

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_matriz.to_excel(writer, index=False, sheet_name='Matriz_Inventario')
processed_data = output.getvalue()

st.download_button(
    label="Descargar Matriz de Inversión Total a Excel",
    data=processed_data,
    file_name="Matriz_Estructura_Inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)