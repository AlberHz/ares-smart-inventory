import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(layout="wide")

st.title("🎯 Módulo de Exactitud de Registro de Inventario (ERI)")
st.markdown("Cargue el reporte de auditoría física para evaluar de forma automatizada la fiabilidad por Almacén, Familia y Mes.")
st.markdown("---")

# ==============================================================================
# 1. COMPROBACIÓN DEL MAESTRO DE STOCK EN MEMORIA
# ==============================================================================
if 'df_stock' not in st.session_state:
    st.warning("⚠️ Primero debe cargar el archivo de Stock en el portal de inicio para realizar los cruces de costos y familias.")
    st.stop()

df_stock = st.session_state['df_stock'].copy()
df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip()

# Mapas maestros
costo_map = df_stock.set_index('Codigo')['Costo'].to_dict()
familia_map = df_stock.set_index('Codigo')['Familia'].to_dict()

# ==============================================================================
# 2. CARGADOR DEL ARCHIVO ERI
# ==============================================================================
st.subheader("📥 Subir Archivo de Conteo de Campo")
archivo_eri = st.file_uploader(
    "Cargue el reporte Excel o CSV. Estructura requerida: FECHA, CODIGO, DESCRIPCION, STOCK, CONTEO, DIFERENCIA, ALMACEN, OBSERVACIONES", 
    type=["xlsx", "csv", "xls"],
    key="uploader_eri_solucionado"
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
            st.error(f"❌ El archivo no contiene las columnas necesarias. Faltan: {missing_cols}")
            st.stop()
            
        df_eri_base = df_in[columnas_requeridas].copy()
        df_eri_base['CODIGO'] = df_eri_base['CODIGO'].astype(str).str.strip()
        df_eri_base['ALMACEN'] = df_eri_base['ALMACEN'].astype(str).str.strip()
        df_eri_base['STOCK'] = pd.to_numeric(df_eri_base['STOCK'], errors='coerce').fillna(0)
        df_eri_base['CONTEO'] = pd.to_numeric(df_eri_base['CONTEO'], errors='coerce').fillna(0)
        df_eri_base['DIFERENCIA'] = pd.to_numeric(df_eri_base['DIFERENCIA'], errors='coerce').fillna(0)
        
        # Parseo cronológico del mes dinámico
        df_eri_base['FECHA_DT'] = pd.to_datetime(df_eri_base['FECHA'], errors='coerce')
        df_eri_base['MES_MOV'] = df_eri_base['FECHA_DT'].dt.strftime('%Y-%m')
        
        # Cruces con maestro de stock
        df_eri_base['FAMILIA'] = df_eri_base['CODIGO'].map(familia_map).fillna("SIN FAMILIA")
        df_eri_base['COSTO_UNITARIO'] = df_eri_base['CODIGO'].map(costo_map).fillna(0.0)
        
        # 💰 Columnas financieras
        df_eri_base['MONTO_AUDITADO'] = df_eri_base['STOCK'] * df_eri_base['COSTO_UNITARIO']
        
        # Diferencia en costo (Solo si hay pérdidas / Diferencia negativa)
        df_eri_base['DIFERENCIA_EN_COSTO'] = df_eri_base.apply(
            lambda r: abs(r['DIFERENCIA']) * r['COSTO_UNITARIO'] if r['DIFERENCIA'] < 0 else 0.0, axis=1
        )
        
        # Aumento en costo (Solo si hay ingresos / Diferencia positiva)
        df_eri_base['AUMENTO_EN_COSTO'] = df_eri_base.apply(
            lambda r: r['DIFERENCIA'] * r['COSTO_UNITARIO'] if r['DIFERENCIA'] > 0 else 0.0, axis=1
        )
        
        # Columna de control para porcentaje de acierto
        df_eri_base['ES_EXACTO'] = (df_eri_base['DIFERENCIA'] == 0).astype(int)

        # ==============================================================================
        # 3. FILTROS DINÁMICOS
        # ==============================================================================
        st.sidebar.header("🎯 Filtros de Segmentación")
        
        list_alm = ["TODOS"] + sorted(df_eri_base['ALMACEN'].unique().tolist())
        filtro_alm = st.sidebar.selectbox("Filtrar por Almacén", list_alm)
        
        df_eri_f = df_eri_base.copy()
        if filtro_alm != "TODOS":
            df_eri_f = df_eri_f[df_eri_f['ALMACEN'] == filtro_alm]
            
        list_fam = ["TODOS"] + sorted(df_eri_f['FAMILIA'].unique().tolist())
        filtro_fam = st.sidebar.selectbox("Filtrar por Familia", list_fam)
        if filtro_fam != "TODOS":
            df_eri_f = df_eri_f[df_eri_f['FAMILIA'] == filtro_fam]
            
        # Lista de meses basada estrictamente en los datos existentes
        meses_existentes = sorted(df_eri_f['MES_MOV'].dropna().unique().tolist())
        list_mes = ["TODOS"] + meses_existentes
        filtro_mes = st.sidebar.selectbox("Filtrar por Mes de Auditoría", list_mes)
        if filtro_mes != "TODOS":
            df_eri_f = df_eri_f[df_eri_f['MES_MOV'] == filtro_mes]

        # ==============================================================================
        # 4. PANELS DE CONTROL KPI
        # ==============================================================================
        total_skus = len(df_eri_f)
        skus_exactos = df_eri_f['ES_EXACTO'].sum()
        porcentaje_eri = (skus_exactos / total_skus) * 100 if total_skus > 0 else 0
        
        total_auditado = df_eri_f['MONTO_AUDITADO'].sum()
        total_diferencia_costo = df_eri_f['DIFERENCIA_EN_COSTO'].sum()
        total_aumento_costo = df_eri_f['AUMENTO_EN_COSTO'].sum()
        
        st.write("### 📊 Indicadores del Segmento Seleccionado")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("🎯 Indicador ERI", f"{porcentaje_eri:.2f} %", "Objetivo >= 95%")
        with kpi2:
            st.metric("💰 Total Monto Auditado", f"S/. {total_auditado:,.2f}")
        with kpi3:
            st.metric("📉 Total Diferencia (Faltantes)", f"S/. {total_diferencia_costo:,.2f}", delta_color="inverse")
        with kpi4:
            st.metric("📈 Total Aumento (Sobrantes)", f"S/. {total_aumento_costo:,.2f}")
            
        st.markdown("---")
        
        # ==============================================================================
        # 5. ESTRUCTURA GRÁFICA OPTIMIZADA (GRANDE Y DESDE EL PRIMER MES REAL)
        # ==============================================================================
        st.subheader("📈 Gráficos de Gestión y Comportamiento del ERI")
        
        g1, g2, g3 = st.columns(3)
        
        with g1:
            st.write("#### 📅 Evolución del ERI Mes a Mes")
            
            # Agrupación dinámica basada UNICAMENTE en meses válidos con datos
            df_mes_eri = df_eri_base.dropna(subset=['MES_MOV']).groupby('MES_MOV').agg(
                Total=('ES_EXACTO', 'count'),
                Exactos=('ES_EXACTO', 'sum')
            ).reset_index()
            df_mes_eri['ERI'] = (df_mes_eri['Exactos'] / df_mes_eri['Total']) * 100
            df_mes_eri = df_mes_eri.sort_values(by='MES_MOV') # Orden cronológico natural
            df_mes_eri.columns = ['Mes', 'Total', 'Exactos', 'ERI']
            
            # Construcción de gráfico con diseño visual mejorado (Grande y nítido)
            fig_trend = px.line(
                df_mes_eri, x='Mes', y='ERI', markers=True, 
                text=df_mes_eri['ERI'].map('{:.1f}%'.format),
                color_discrete_sequence=["#10b981"]
            )
            
            # Mejoras de visibilidad del trazo y las etiquetas
            fig_trend.update_traces(
                line=dict(width=4), 
                marker=dict(size=10),
                textposition="top center",
                textfont=dict(size=13, color="black", weight="bold")
            )
            
            fig_trend.update_layout(
                plot_bgcolor='white', 
                yaxis=dict(range=[0, 110], title="ERI (%)", gridcolor="#e5e7eb"),
                xaxis=dict(type='category', title="Meses con Auditoría", gridcolor="#e5e7eb"),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with g2:
            st.write("#### 🏢 Precisión ERI por Almacén")
            df_alm_eri = df_eri_base.groupby('ALMACEN').agg(
                Total=('ES_EXACTO', 'count'),
                Exactos=('ES_EXACTO', 'sum')
            ).reset_index()
            df_alm_eri['ERI'] = (df_alm_eri['Exactos'] / df_alm_eri['Total']) * 100
            
            fig_alm = px.bar(df_alm_eri, x='ALMACEN', y='ERI', text=df_alm_eri['ERI'].map('{:.1f}%'.format),
                             color='ERI', color_continuous_scale="Viridis")
            fig_alm.update_traces(textposition="outside", textfont=dict(size=12, weight="bold"))
            fig_alm.update_layout(plot_bgcolor='white', yaxis=dict(range=[0, 110]))
            st.plotly_chart(fig_alm, use_container_width=True)
            
        with g3:
            st.write("#### 🗂️ Nivel de ERI por Familia de Producto")
            df_fam_eri = df_eri_base.groupby('FAMILIA').agg(
                Total=('ES_EXACTO', 'count'),
                Exactos=('ES_EXACTO', 'sum')
            ).reset_index()
            df_fam_eri['ERI'] = (df_fam_eri['Exactos'] / df_fam_eri['Total']) * 100
            
            fig_fam = px.bar(df_fam_eri, y='FAMILIA', x='ERI', text=df_fam_eri['ERI'].map('{:.1f}%'.format),
                             orientation='h', color_discrete_sequence=["#3b82f6"])
            fig_fam.update_traces(textposition="outside", textfont=dict(size=12, weight="bold"))
            fig_fam.update_layout(plot_bgcolor='white', xaxis=dict(range=[0, 115]))
            st.plotly_chart(fig_fam, use_container_width=True)

        # ==============================================================================
        # 6. MATRIZ DE DESPLIEGUE FINAL EXACTO
        # ==============================================================================
        st.write("---")
        st.write("### 📋 Tabla Analítica Integral de Control ERI")
        
        columnas_despliegue = [
            'FECHA', 'MES_MOV', 'ALMACEN', 'CODIGO', 'FAMILIA', 'DESCRIPCION', 
            'STOCK', 'CONTEO', 'DIFERENCIA', 'MONTO_AUDITADO', 'DIFERENCIA_EN_COSTO', 'AUMENTO_EN_COSTO', 'OBSERVACIONES'
        ]
        
        st.dataframe(
            df_eri_f[columnas_despliegue].style.format({
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
        
        # Exportador
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_eri_f[columnas_despliegue].to_excel(writer, index=False, sheet_name='Matriz_ERI_Auditoria')
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Descargar Auditoría de Ajustes a Excel",
            data=processed_data,
            file_name="Auditoria_ERI_Historico.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Error procesando la consistencia de los datos del ERI: {e}")
else:
    st.info("💡 Complete el ciclo: Suba su plantilla de auditoría con columnas: FECHA, CODIGO, DESCRIPCION, STOCK, CONTEO, DIFERENCIA, ALMACEN y OBSERVACIONES.")