import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(layout="wide", page_title="KPI 6 - ERI", page_icon="🎯")

st.title("KPI 6 - EXACTITUD DE REGISTRO DE INVENTARIOS (ERI)")
st.markdown("---")

# ==============================================================================
# 1. COMPROBACIÓN DEL MAESTRO DE STOCK EN MEMORIA
# ==============================================================================
if 'df_stock' not in st.session_state:
    st.warning("⚠️ Primero debe cargar el archivo de Stock en el portal de inicio (app.py) para realizar los cruces de costos y familias.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()

# Mapas maestros
costo_map = df_stock.set_index('Codigo')['Costo'].to_dict()
familia_map = df_stock.set_index('Codigo')['Familia'].to_dict()

# ==============================================================================
# 2. GESTIÓN Y PERSISTENCIA DE DATOS EN SESSION STATE
# ==============================================================================
# Botón lateral para re-subir o limpiar datos si es necesario
if 'df_eri_base' in st.session_state:
    if st.sidebar.button("Cargar un archivo ERI diferente"):
        del st.session_state['df_eri_base']
        st.rerun()

if 'df_eri_base' not in st.session_state:
    st.subheader("Subir Archivo de Conteo")
    archivo_eri = st.file_uploader(
        "Cargue el reporte Excel o CSV. Estructura requerida: FECHA, CODIGO, DESCRIPCION, STOCK, CONTEO, DIFERENCIA, ALMACEN, OBSERVACIONES", 
        type=["xlsx", "csv", "xls"],
        key="uploader_eri_persiste"
    )

    if archivo_eri is not None:
        try:
            if archivo_eri.name.endswith('.csv'):
                df_in = pd.read_csv(archivo_eri)
            else:
                df_in = pd.read_excel(archivo_eri)
                
            df_in.columns = df_in.columns.str.strip().str.upper()
            
            columnas_requeridas = ['FECHA', 'CODIGO', 'DESCRIPCION', 'STOCK', 'CONTEO', 'DIFERENCIA', 'ALMACEN', 'OBSERVACIONES']
            missing_cols = [col for col in columnas_requeridas if col not in df_in.columns]
            
            if missing_cols:
                st.error(f"El archivo no contiene las columnas necesarias. Faltan: {missing_cols}")
                st.stop()
                
            df_proc = df_in[columnas_requeridas].copy()
            df_proc['CODIGO'] = df_proc['CODIGO'].astype(str).str.strip()
            df_proc['ALMACEN'] = df_proc['ALMACEN'].astype(str).str.strip()
            df_proc['STOCK'] = pd.to_numeric(df_proc['STOCK'], errors='coerce').fillna(0)
            df_proc['CONTEO'] = pd.to_numeric(df_proc['CONTEO'], errors='coerce').fillna(0)
            df_proc['DIFERENCIA'] = pd.to_numeric(df_proc['DIFERENCIA'], errors='coerce').fillna(0)
            
            # Parseo cronológico del mes dinámico
            df_proc['FECHA_DT'] = pd.to_datetime(df_proc['FECHA'], errors='coerce')
            df_proc['MES_MOV'] = df_proc['FECHA_DT'].dt.strftime('%Y-%m')
            
            # Cruces con maestro de stock
            df_proc['FAMILIA'] = df_proc['CODIGO'].map(familia_map).fillna("SIN FAMILIA")
            df_proc['COSTO_UNITARIO'] = df_proc['CODIGO'].map(costo_map).fillna(0.0)
            
            # 💰 Columnas financieras
            df_proc['MONTO_AUDITADO'] = df_proc['STOCK'] * df_proc['COSTO_UNITARIO']
            
            # Diferencia en costo (Solo si hay pérdidas / Diferencia negativa)
            df_proc['DIFERENCIA_EN_COSTO'] = df_proc.apply(
                lambda r: abs(r['DIFERENCIA']) * r['COSTO_UNITARIO'] if r['DIFERENCIA'] < 0 else 0.0, axis=1
            )
            
            # Aumento en costo (Solo si hay ingresos / Diferencia positiva)
            df_proc['AUMENTO_EN_COSTO'] = df_proc.apply(
                lambda r: r['DIFERENCIA'] * r['COSTO_UNITARIO'] if r['DIFERENCIA'] > 0 else 0.0, axis=1
            )
            
            # Columna de control para porcentaje de acierto
            df_proc['ES_EXACTO'] = (df_proc['DIFERENCIA'] == 0).astype(int)

            # GUARDAR EN MEMORIA DE SESIÓN (PERSISTENCIA TOTAL)
            st.session_state['df_eri_base'] = df_proc
            st.rerun()

        except Exception as e:
            st.error(f"Error procesando la consistencia de los datos del ERI: {e}")
            st.stop()
    else:
        st.info("Cargue su plantilla de auditoría para activar el dashboard del ERI.")
        st.stop()

# ==============================================================================
# 3. LECTURA DE DATOS DESDE SESSION STATE
# ==============================================================================
df_eri_base = st.session_state['df_eri_base'].copy()

# ==============================================================================
# 4. FILTROS DINÁMICOS
# ==============================================================================
st.sidebar.header("Filtros de Segmentación")

list_alm = ["TODOS"] + sorted(df_eri_base['ALMACEN'].dropna().unique().tolist())
filtro_alm = st.sidebar.selectbox("Filtrar por Almacén", list_alm)

df_eri_f = df_eri_base.copy()
if filtro_alm != "TODOS":
    df_eri_f = df_eri_f[df_eri_f['ALMACEN'] == filtro_alm]
    
list_fam = ["TODOS"] + sorted(df_eri_f['FAMILIA'].dropna().unique().tolist())
filtro_fam = st.sidebar.selectbox("Filtrar por Familia", list_fam)
if filtro_fam != "TODOS":
    df_eri_f = df_eri_f[df_eri_f['FAMILIA'] == filtro_fam]
    
meses_existentes = sorted(df_eri_f['MES_MOV'].dropna().unique().tolist())
list_mes = ["TODOS"] + meses_existentes
filtro_mes = st.sidebar.selectbox("Filtrar por Mes de Auditoría", list_mes)
if filtro_mes != "TODOS":
    df_eri_f = df_eri_f[df_eri_f['MES_MOV'] == filtro_mes]

# ==============================================================================
# 5. PANELS DE CONTROL KPI
# ==============================================================================
total_skus = len(df_eri_f)
skus_exactos = df_eri_f['ES_EXACTO'].sum()
porcentaje_eri = (skus_exactos / total_skus) * 100 if total_skus > 0 else 0

total_auditado = df_eri_f['MONTO_AUDITADO'].sum()
total_diferencia_costo = df_eri_f['DIFERENCIA_EN_COSTO'].sum()
total_aumento_costo = df_eri_f['AUMENTO_EN_COSTO'].sum()

st.write("### Indicadores del Segmento Seleccionado")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Indicador ERI (Exactitud)", f"{porcentaje_eri:.2f}%", "Objetivo ≥ 95%", delta_color="normal" if porcentaje_eri >= 95 else "inverse")
kpi2.metric("Total Monto Auditado", f"S/. {total_auditado:,.2f}")
kpi3.metric("Faltantes (Pérdida en Costo)", f"S/. {total_diferencia_costo:,.2f}", delta_color="inverse")
kpi4.metric("Sobrantes (Ingreso en Costo)", f"S/. {total_aumento_costo:,.2f}")
    
st.markdown("---")

# ==============================================================================
# 6. ESTRUCTURA GRÁFICA DESPLEGADA EN FILAS INDEPENDIENTES
# ==============================================================================
st.subheader("Análisis y Comportamiento del ERI")

# ------------------------------------------------------------------------------
# FILA 1: EVOLUCIÓN HISTÓRICA MES A MES (ANCHO COMPLETO)
# ------------------------------------------------------------------------------
st.write("#### 1. Evolución del ERI Mes a Mes (Tendencia Histórica)")

df_mes_eri = df_eri_f.dropna(subset=['MES_MOV']).groupby('MES_MOV').agg(
    Total=('ES_EXACTO', 'count'),
    Exactos=('ES_EXACTO', 'sum')
).reset_index()

if not df_mes_eri.empty:
    df_mes_eri['ERI'] = (df_mes_eri['Exactos'] / df_mes_eri['Total']) * 100
    df_mes_eri = df_mes_eri.sort_values(by='MES_MOV')

    fig_trend = px.line(
        df_mes_eri, x='MES_MOV', y='ERI', markers=True, 
        text=df_mes_eri['ERI'].map('{:.1f}%'.format),
        color_discrete_sequence=["#10b981"]
    )
    
    fig_trend.update_traces(
        line=dict(width=4), 
        marker=dict(size=10),
        textposition="top center",
        textfont=dict(size=13, color="black", weight="bold")
    )
    
    # Línea de Meta Gerencial al 95%
    fig_trend.add_shape(
        type="line", x0=df_mes_eri['MES_MOV'].iloc[0], x1=df_mes_eri['MES_MOV'].iloc[-1],
        y0=95, y1=95, line=dict(color="Red", width=2, dash="dash")
    )
    
    fig_trend.update_layout(
        plot_bgcolor='white', 
        yaxis=dict(range=[0, 110], title="ERI (%)", gridcolor="#e5e7eb"),
        xaxis=dict(type='category', title="Mes de Auditoría", gridcolor="#e5e7eb"),
        height=380,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No hay suficiente información mensual para graficar la tendencia con los filtros aplicados.")

st.markdown("---")

# ------------------------------------------------------------------------------
# FILA 2: COMPARATIVO POR ALMACÉN Y POR FAMILIA (2 COLUMNAS AMPLIAS)
# ------------------------------------------------------------------------------
col_g2, col_g3 = st.columns(2)

with col_g2:
    st.write("#### 2. Precisión ERI por Almacén")
    df_alm_eri = df_eri_f.groupby('ALMACEN').agg(
        Total=('ES_EXACTO', 'count'),
        Exactos=('ES_EXACTO', 'sum')
    ).reset_index()
    
    if not df_alm_eri.empty:
        df_alm_eri['ERI'] = (df_alm_eri['Exactos'] / df_alm_eri['Total']) * 100
        df_alm_eri = df_alm_eri.sort_values(by='ERI', ascending=False)
        
        fig_alm = px.bar(
            df_alm_eri, x='ALMACEN', y='ERI', 
            text=df_alm_eri['ERI'].map('{:.1f}%'.format),
            color='ERI', color_continuous_scale="Viridis"
        )
        fig_alm.update_traces(textposition="outside", textfont=dict(size=12, weight="bold"))
        fig_alm.update_layout(
            plot_bgcolor='white', 
            yaxis=dict(range=[0, 115], title="ERI (%)"),
            xaxis_title="Almacén",
            height=420
        )
        st.plotly_chart(fig_alm, use_container_width=True)

with col_g3:
    st.write("#### 3. Nivel de ERI por Familia")
    df_fam_eri = df_eri_f.groupby('FAMILIA').agg(
        Total=('ES_EXACTO', 'count'),
        Exactos=('ES_EXACTO', 'sum')
    ).reset_index()
    
    if not df_fam_eri.empty:
        df_fam_eri['ERI'] = (df_fam_eri['Exactos'] / df_fam_eri['Total']) * 100
        df_fam_eri = df_fam_eri.sort_values(by='ERI', ascending=True) # Ascendente para que en barras horizontales el más alto quede arriba
        
        fig_fam = px.bar(
            df_fam_eri, y='FAMILIA', x='ERI', 
            text=df_fam_eri['ERI'].map('{:.1f}%'.format),
            orientation='h', color_discrete_sequence=["#3b82f6"]
        )
        fig_fam.update_traces(textposition="outside", textfont=dict(size=11, weight="bold"))
        fig_fam.update_layout(
            plot_bgcolor='white', 
            xaxis=dict(range=[0, 118], title="ERI (%)"),
            yaxis_title="Familia de Producto",
            height=420
        )
        st.plotly_chart(fig_fam, use_container_width=True)

# ==============================================================================
# 7. MATRIZ DE DESPLIEGUE FINAL EXACTO
# ==============================================================================
st.markdown("---")
st.write("### Tabla Analítica Integral de Control ERI")

columnas_despliegue = [
    'FECHA', 'MES_MOV', 'ALMACEN', 'CODIGO', 'FAMILIA', 'DESCRIPCION', 
    'STOCK', 'CONTEO', 'DIFERENCIA', 'MONTO_AUDITADO', 'DIFERENCIA_EN_COSTO', 'AUMENTO_EN_COSTO', 'OBSERVACIONES'
]

cols_existentes = [c for c in columnas_despliegue if c in df_eri_f.columns]

st.dataframe(
    df_eri_f[cols_existentes].style.format({
        'STOCK': '{:,.0f}',
        'CONTEO': '{:,.0f}',
        'DIFERENCIA': '{:,.0f}',
        'MONTO_AUDITADO': 'S/. {:,.2f}',
        'DIFERENCIA_EN_COSTO': 'S/. {:,.2f}',
        'AUMENTO_EN_COSTO': 'S/. {:,.2f}'
    }),
    use_container_width=True,
    hide_index=True
)

# Exportador a Excel
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_eri_f[cols_existentes].to_excel(writer, index=False, sheet_name='Matriz_ERI_Auditoria')

st.download_button(
    label="Descargar Auditoría de Ajustes a Excel",
    data=output.getvalue(),
    file_name="Auditoria_ERI_Historico.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)