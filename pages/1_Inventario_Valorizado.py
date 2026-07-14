import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(layout="wide")

if 'df_stock' not in st.session_state:
    st.warning("Debe cargar los datos en el portal de inicio para acceder a este módulo.")
    st.stop()

df_stock = st.session_state['df_stock']

st.title("Distribución de Capital Inmovilizado y Estructura Patrimonial")
st.markdown("---")

# Filtros dinámicos en cascada en la barra lateral
st.sidebar.header("Filtros de Segmentación")
list_alm = ["TODOS"] + sorted(df_stock['Almacen'].unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtro de Almacenamiento Sede", list_alm)

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

# KPIs
total_capital = df_f['Valor_Total'].sum()
total_unidades = df_f['Stock'].sum()

metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("Capital Total Inmovilizado", f"S/. {total_capital / 1000:,.2f} K")
metric_col2.metric("Volumen Físico Total en Custodia", f"{total_unidades:,.0f} UM")

st.write("---")

cg1, cg2 = st.columns(2)

with cg1:
    st.subheader("Participación de Capital por Almacén")
    df_g_alm = df_f.groupby('Almacen')['Valor_Total'].sum().reset_index()
    # Colores de alto contraste alternados
    fig_alm = px.pie(df_g_alm, values='Valor_Total', names='Almacen', hole=0.5,
                     color_discrete_sequence=px.colors.qualitative.Bold)
    fig_alm.update_traces(textinfo='percent+label', hovertemplate="Monto: S/. %{value:,.2f}<br>Participación: %{percent}")
    st.plotly_chart(fig_alm, use_container_width=True)

with cg2:
    st.subheader("Estructura de Capital por Familias de Inventario")
    df_g_fam = df_f.groupby('Familia')['Valor_Total'].sum().reset_index().sort_values(by='Valor_Total', ascending=False)
    
    fig_fam = px.bar(
        df_g_fam, 
        x='Valor_Total', 
        y='Familia', 
        orientation='h',
        color='Familia', 
        color_discrete_sequence=px.colors.qualitative.Vivid, 
        labels={'Valor_Total':'Monto Total (S/.)'}
    )
    
    # MODIFICACIÓN CLAVE: dtick=1 fuerza la visualización obligatoria de cada fila, y aumentamos la altura (height)
    fig_fam.update_layout(
        yaxis=dict(
            categoryorder='total ascending',
            type='category',
            dtick=1  # Le dice a Plotly que marque cada categoría sin saltarse ninguna
        ),
        showlegend=False,
        height=550,  # Expandimos el lienzo vertical para albergar cómodamente todas las filas
        margin=dict(l=180, r=20, t=20, b=20)  # Ampliamos margen izquierdo para que textos largos no se corten
    )
    st.plotly_chart(fig_fam, use_container_width=True)

# Tabla Estructurada con campo SubFamilia
st.write("---")
st.subheader("Matriz Estructurada de Almacenamiento Global")

df_matriz = df_f.groupby(['Almacen', 'Familia', 'SubFamilia']).agg(
    Stock_Actual=('Stock', 'sum'),
    Valor_Total_Soles=('Valor_Total', 'sum')
).reset_index()

df_matriz['Representacion_Porcentaje'] = (df_matriz['Valor_Total_Soles'] / total_capital) * 100 if total_capital > 0 else 0
df_matriz = df_matriz.sort_values(by='Valor_Total_Soles', ascending=False)

st.dataframe(
    df_matriz.style.format({
        'Stock_Actual': '{:,.0f}',
        'Valor_Total_Soles': 'S/. {:,.2f}',
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
    label="Descargar Matriz de Almacenamiento Completa a Excel",
    data=processed_data,
    file_name="Matriz_Estructura_Inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)