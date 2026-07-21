import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(layout="wide")

if 'df_stock' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock']

st.title("Inventario Valorizado")
st.markdown("Análisis ejecutivo de concentración de capital y distribución jerárquica de inventario.")
st.markdown("---")

# ==============================================================================
# FILTROS EN CASCADA
# ==============================================================================
st.sidebar.header("Filtros de Segmentación")
list_alm = ["TODOS"] + sorted(df_stock['Almacen'].unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtro de Almacen", list_alm)

df_f = df_stock.copy()
if filtro_alm != "TODOS":
    df_f = df_f[df_f['Almacen'] == filtro_alm]

list_fam = ["TODOS"] + sorted(df_f['Familia'].unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtro de Familia", list_fam)

if filtro_fam != "TODOS":
    df_f = df_f[df_f['Familia'] == filtro_fam]

list_subfam = ["TODOS"] + sorted(df_f['SubFamilia'].unique().tolist())
filtro_subfam = st.sidebar.selectbox("Filtro de Subfamilia", list_subfam)

if filtro_subfam != "TODOS":
    df_f = df_f[df_f['SubFamilia'] == filtro_subfam]

# ==============================================================================
# KPIS PRINCIPALES
# ==============================================================================
total_capital = df_f['Valor_Total'].sum()
total_unidades = df_f['Stock'].sum()
total_skus = df_f['Codigo'].nunique() if 'Codigo' in df_f.columns else len(df_f)
costo_promedio_unidad = total_capital / total_unidades if total_unidades > 0 else 0

if not df_f.empty and 'Valor_Total' in df_f.columns:
    col_sku_name = 'Descripcion' if 'Descripcion' in df_f.columns else 'Codigo'
    top_sku_row = df_f.sort_values(by='Valor_Total', ascending=False).iloc[0]
    top_sku_nombre = str(top_sku_row[col_sku_name])[:22] + "..." if len(str(top_sku_row[col_sku_name])) > 22 else str(top_sku_row[col_sku_name])
    top_sku_val = top_sku_row['Valor_Total']
    pct_top_sku = (top_sku_val / total_capital) * 100 if total_capital > 0 else 0
else:
    top_sku_nombre, top_sku_val, pct_top_sku = "N/A", 0, 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Capital Inmovilizado", f"S/. {total_capital / 1000:,.2f} K", f"S/. {total_capital:,.2f}")
kpi2.metric("Unidades en Custodia", f"{total_unidades:,.0f} UM", f"{total_skus:,.0f} SKUs Únicos")
kpi3.metric("Valor Promedio / Unidad", f"S/. {costo_promedio_unidad:,.2f}", "Costo Unitario Medio")
kpi4.metric("SKU Lider de Concentración", f"S/. {top_sku_val / 1000:,.1f} K", f"{pct_top_sku:.1f}% del capital ({top_sku_nombre})")

st.markdown("---")

# ==============================================================================
# BLOQUE 1: PARTICIPACIÓN POR ALMACÉN Y TOP 10 SKUS (FILA 1)
# ==============================================================================
cg1, cg2 = st.columns([4, 6])

with cg1:
    st.subheader("Inventario Valorizado por Almacén")
    df_g_alm = df_f.groupby('Almacen')['Valor_Total'].sum().reset_index()
    
    fig_alm = px.pie(
        df_g_alm, 
        values='Valor_Total', 
        names='Almacen', 
        hole=0.45,
        color_discrete_sequence=['#1e3a8a', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd']
    )
    fig_alm.update_traces(
        textinfo='percent+label', 
        hovertemplate="<b>%{label}</b><br>Monto: S/. %{value:,.2f}<br>Participación: %{percent}<extra></extra>"
    )
    fig_alm.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=380)
    st.plotly_chart(fig_alm, use_container_width=True)

with cg2:
    st.subheader("Top 10 SKUs de Mayor Concentración de Capital")
    col_prod = 'Descripcion' if 'Descripcion' in df_f.columns else ('Codigo' if 'Codigo' in df_f.columns else 'Familia')
    
    df_top10 = df_f.groupby([col_prod, 'Familia'])['Valor_Total'].sum().reset_index()
    df_top10 = df_top10.sort_values(by='Valor_Total', ascending=False).head(10)
    df_top10 = df_top10.sort_values(by='Valor_Total', ascending=True)

    fig_top10 = px.bar(
        df_top10,
        x='Valor_Total',
        y=col_prod,
        orientation='h',
        text=df_top10['Valor_Total'].apply(lambda x: f"S/. {x:,.2f}"),
        color='Valor_Total',
        color_continuous_scale='Blues',
        labels={'Valor_Total': 'Valor Total (S/.)', col_prod: 'Producto'}
    )
    fig_top10.update_traces(
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Monto Inmovilizado: S/. %{x:,.2f}<extra></extra>"
    )
    fig_top10.update_layout(
        coloraxis_showscale=False,
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(dtick=1),
        height=380,
        margin=dict(t=10, b=10, l=180, r=80)
    )
    st.plotly_chart(fig_top10, use_container_width=True)

# ==============================================================================
# BLOQUE 2: TREEMAP A ANCHO COMPLETO (FILA 2 SOLITARIO)
# ==============================================================================
st.markdown("---")
st.subheader("Mapa Jerárquico Global de Capital (Treemap)")
st.caption("Estructura completa a ancho extendido: Almacén > Familia > SubFamilia.")

df_tree_data = df_f.groupby(['Almacen', 'Familia', 'SubFamilia']).agg(
    Valor_Total=('Valor_Total', 'sum'),
    Stock=('Stock', 'sum')
).reset_index()

fig_tree = px.treemap(
    df_tree_data,
    path=['Almacen', 'Familia', 'SubFamilia'],
    values='Valor_Total',
    color='Valor_Total',
    color_continuous_scale=['#e2e8f0', '#94a3b8', '#3b82f6', '#1d4ed8', '#0f172a']
)

fig_tree.update_traces(
    hovertemplate="<b>Nivel: %{label}</b><br>" +
                  "Rama Superior: %{parent}<br>" +
                  "Monto Inmovilizado: <b>S/. %{value:,.2f}</b><br>" +
                  "Aporte al Total: <b>%{percentRoot:.2%}</b><extra></extra>",
    marker=dict(cornerradius=3)
)

fig_tree.update_layout(
    coloraxis_showscale=False,
    margin=dict(t=15, b=15, l=10, r=10), 
    height=500  # Altura amplia para desplegar todo con espacio holgado
)
st.plotly_chart(fig_tree, use_container_width=True)

# ==============================================================================
# BLOQUE 3: FAMILIAS VS SUBFAMILIAS LADO A LADO (FILA 3)
# ==============================================================================
st.markdown("---")
st.subheader("Estructura Desglosada: Familias vs Subfamilias")

col_fam, col_subfam = st.columns(2)

with col_fam:
    st.markdown("##### Concentración por Familia")
    df_g_fam = df_f.groupby('Familia')['Valor_Total'].sum().reset_index().sort_values(by='Valor_Total', ascending=True)

    fig_fam = px.bar(
        df_g_fam, 
        x='Valor_Total', 
        y='Familia', 
        orientation='h',
        text=df_g_fam['Valor_Total'].apply(lambda x: f"S/. {x:,.2f}"),
        color='Valor_Total', 
        color_continuous_scale='Blues'
    )
    fig_fam.update_traces(
        textposition='outside',
        hovertemplate="<b>Familia: %{y}</b><br>Monto: S/. %{x:,.2f}<extra></extra>"
    )
    fig_fam.update_layout(
        coloraxis_showscale=False,
        yaxis=dict(categoryorder='total ascending', type='category', dtick=1),
        showlegend=False,
        height=450,
        margin=dict(l=140, r=80, t=10, b=20),
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    st.plotly_chart(fig_fam, use_container_width=True)

with col_subfam:
    st.markdown("##### Top 10 Subfamilias de Mayor Capital")
    df_g_subfam = df_f.groupby('SubFamilia')['Valor_Total'].sum().reset_index()
    df_g_subfam = df_g_subfam.sort_values(by='Valor_Total', ascending=False).head(10).sort_values(by='Valor_Total', ascending=True)

    fig_subfam = px.bar(
        df_g_subfam, 
        x='Valor_Total', 
        y='SubFamilia', 
        orientation='h',
        text=df_g_subfam['Valor_Total'].apply(lambda x: f"S/. {x:,.2f}"),
        color='Valor_Total', 
        color_continuous_scale='Teal'
    )
    fig_subfam.update_traces(
        textposition='outside',
        hovertemplate="<b>Subfamilia: %{y}</b><br>Monto: S/. %{x:,.2f}<extra></extra>"
    )
    fig_subfam.update_layout(
        coloraxis_showscale=False,
        yaxis=dict(categoryorder='total ascending', type='category', dtick=1),
        showlegend=False,
        height=450,
        margin=dict(l=140, r=80, t=10, b=20),
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    st.plotly_chart(fig_subfam, use_container_width=True)

# ==============================================================================
# MATRIZ TABULAR AVANZADA
# ==============================================================================
st.markdown("---")
st.subheader("Matriz Estructurada de Almacenamiento Global")

df_matriz = df_f.groupby(['Almacen', 'Familia', 'SubFamilia']).agg(
    SKUs_Distintos=('Valor_Total', 'count'),
    Stock_Actual=('Stock', 'sum'),
    Valor_Total_Soles=('Valor_Total', 'sum')
).reset_index()

df_matriz['Precio_Promedio_Unitario'] = df_matriz['Valor_Total_Soles'] / df_matriz['Stock_Actual']
df_matriz['Representacion_Porcentaje'] = (df_matriz['Valor_Total_Soles'] / total_capital) * 100 if total_capital > 0 else 0
df_matriz = df_matriz.sort_values(by='Valor_Total_Soles', ascending=False)

st.dataframe(
    df_matriz.style.format({
        'SKUs_Distintos': '{:,.0f}',
        'Stock_Actual': '{:,.0f}',
        'Valor_Total_Soles': 'S/. {:,.2f}',
        'Precio_Promedio_Unitario': 'S/. {:,.2f}',
        'Representacion_Porcentaje': '{:.2f}%'
    }),
    use_container_width=True,
    hide_index=True
)

# Exportación a Excel
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_matriz.to_excel(writer, index=False, sheet_name='Matriz_Inventario')
processed_data = output.getvalue()

st.download_button(
    label="Descargar Matriz de Almacenamiento Completa a Excel",
    data=processed_data,
    file_name="Matriz_Estructura_Inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)