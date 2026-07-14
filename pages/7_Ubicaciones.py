import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import io

st.set_page_config(layout="wide")

st.title("📦 Módulo de Capacidad, Ocupación y Costos de Almacenamiento (WMS)")
st.markdown("Analice la infraestructura física frente al WMS, calculando ocupación y costos operativos por m², m³ y nicho con depreciación de activos.")
st.markdown("---")

# ==============================================================================
# FUNCIÓN DE NORMALIZACIÓN DE CABECERAS
# ==============================================================================
def normalizar_columnas(df):
    def limpiar_texto(col):
        c = str(col).replace('\ufeff', '').strip().upper()
        c = "".join(x for x in unicodedata.normalize('NFD', c) if unicodedata.category(x) != 'Mn')
        return " ".join(c.split())
    df.columns = [limpiar_texto(col) for col in df.columns]
    return df

# ==============================================================================
# 1. ENTRADA DE ARCHIVOS PREVIA PARA DETECTAR TIPOS DE UBICACIÓN
# ==============================================================================
col_up1, col_up2 = st.columns(2)

with col_up1:
    st.subheader("🏢 SUBIR AQUÍ: Layout Físico Simplificado")
    archivo_a = st.file_uploader(
        "Sube aquí el layout (Solo Ubicación y Tipo de Estructura)", 
        type=["csv", "xlsx"], 
        key="up_layout"
    )

with col_up2:
    st.subheader("📊 SUBIR AQUÍ: Reporte WMS")
    archivo_b = st.file_uploader(
        "Sube aquí el Reporte de stock WMS", 
        type=["csv", "xlsx"], 
        key="up_wms"
    )

# Valores por defecto si no se ha subido archivo aún
tipos_unicos = ["RACK", "PASILLO"]

if archivo_a is not None:
    try:
        # Pre-lectura rápida para extraer tipos únicos
        if archivo_a.name.endswith('.csv'):
            df_temp = pd.read_csv(archivo_a, sep=None, engine='python', encoding='utf-8-sig')
        else:
            df_temp = pd.read_excel(archivo_a)
        
        df_temp = normalizar_columnas(df_temp)
        
        # Buscar columna "Tipo"
        col_tipo_temp = None
        for col in df_temp.columns:
            if any(key in col for key in ['TIPO', 'ESTRUCTURA', 'ESTADO', 'CLASE']):
                col_tipo_temp = col
                break
        
        if col_tipo_temp:
            tipos_unicos = sorted(df_temp[col_tipo_temp].dropna().unique().tolist())
    except Exception as e:
        pass

# ==============================================================================
# CONTROLES LATERALES: METRAJE POR TIPO Y GASTOS REALES
# ==============================================================================
st.sidebar.header("📐 1. Metraje por Tipo de Ubicación")
st.sidebar.caption("Define los m² de suelo ocupados para cada tipo detectado en tu excel:")

m2_por_tipo = {}
for t in tipos_unicos:
    # Valor sugerido automático
    val_sugerido = 1.44 if "RACK" in str(t).upper() else 1.20
    m2_por_tipo[t] = st.sidebar.number_input(f"m² de {t}:", min_value=0.01, value=val_sugerido, step=0.05, key=f"m2_{t}")

alto_estandar = st.sidebar.number_input("Altura promedio de nicho (m)", min_value=0.5, value=1.5, step=0.1)

st.sidebar.header("💰 2. Gastos Mensuales Reales")

st.sidebar.subheader("Alquiler")
area_total_almacen = st.sidebar.number_input("Área Total Alquilada (m²)", min_value=1.0, value=1200.0, step=50.0)
costo_alquiler_usd_m2 = st.sidebar.number_input("Tarifa Alquiler (USD / m²)", min_value=0.0, value=5.0, step=0.1)
tipo_cambio = st.sidebar.number_input("Tipo de Cambio (1 USD -> S/.)", min_value=1.0, value=3.75, step=0.01)

alquiler_calculado_pen = area_total_almacen * costo_alquiler_usd_m2 * tipo_cambio

st.sidebar.subheader("Recursos y Personal")
c_personal = st.sidebar.number_input("Sueldos Mensuales Operativos (S/.)", min_value=0.0, value=18000.0, step=500.0)
c_servicios = st.sidebar.number_input("Consumo de Luz / Recursos (S/.)", min_value=0.0, value=2500.0, step=100.0)

st.sidebar.subheader("🚜 Depreciación Montacargas")
st.sidebar.caption("Hyster de 3.5 TN (Comprado hace 2 meses)")
costo_hyster_usd = st.sidebar.number_input("Costo de Compra del Hyster (USD)", min_value=0.0, value=40000.0, step=1000.0)
tasa_depreciacion_anual = st.sidebar.slider("Tasa Depreciación Anual (%)", min_value=5, max_value=30, value=20) # 20% es el estandar SUNAT para vehiculos/carga

# Cálculos de depreciación
costo_hyster_pen = costo_hyster_usd * tipo_cambio
depreciacion_anual_pen = costo_hyster_pen * (tasa_depreciacion_anual / 100.0)
depreciacion_mensual_pen = depreciacion_anual_pen / 12.0
depreciacion_acumulada_2meses = depreciacion_mensual_pen * 2

st.sidebar.info(f"Depreciación mensual: S/. {depreciacion_mensual_pen:,.2f}")

# COSTO GLOBAL TOTAL
costo_fijo_total = alquiler_calculado_pen + c_personal + c_servicios + depreciacion_mensual_pen
st.sidebar.markdown(f"### **Gasto Operativo Total:**\n### **S/. {costo_fijo_total:,.2f}**")

# ==============================================================================
# PROCESAMIENTO PRINCIPAL DE DATOS
# ==============================================================================
if archivo_a is not None and archivo_b is not None:
    try:
        # Lectura de Archivos
        if archivo_a.name.endswith('.csv'):
            df_a = pd.read_csv(archivo_a, sep=None, engine='python', encoding='utf-8-sig')
        else:
            df_a = pd.read_excel(archivo_a)
            
        if archivo_b.name.endswith('.csv'):
            df_b = pd.read_csv(archivo_b, sep=None, engine='python', encoding='utf-8-sig')
        else:
            df_b = pd.read_excel(archivo_b)

        # Normalizar cabeceras
        df_lay_raw = normalizar_columnas(df_a)
        df_wms_raw = normalizar_columnas(df_b)

        # Mapear columnas del Layout
        cols_lay = df_lay_raw.columns.tolist()
        ubicacion_col = next((c for c in cols_lay if any(k in c for k in ['CODIGO', 'UBICACION', 'FISICO', 'COD'])), cols_lay[0])
        tipo_col = next((c for c in cols_lay if any(k in c for k in ['TIPO', 'ESTRUCTURA', 'ESTADO', 'CLASE']) and c != ubicacion_col), None)
        
        if not tipo_col:
            otras = [c for c in cols_lay if c != ubicacion_col]
            tipo_col = otras[0] if otras else 'TIPO'
            if 'TIPO' not in df_lay_raw.columns:
                df_lay_raw['TIPO'] = 'RACK'

        df_lay = df_lay_raw.rename(columns={ubicacion_col: 'UBICACION', tipo_col: 'TIPO'})[['UBICACION', 'TIPO']]

        # Mapear columnas de Stock WMS
        map_wms = {
            'CODIGO SKU': 'CODIGO',
            'DESCRIPCION': 'DESCRIPCION',
            'UBICACION ESPECIFICA': 'UBICACION',
            'CANTIDAD EN ESTA UBICACION': 'CANTIDAD',
            'STOCK TOTAL SISTEMA': 'STOCK_SISTEMA',
            'FALTANTE GLOBAL SKU': 'FALTANTE',
            'ESTADO ASIGNACION': 'ESTADO'
        }
        df_wms = df_wms_raw.rename(columns=map_wms)

        df_lay['UBICACION'] = df_lay['UBICACION'].astype(str).str.strip()
        df_wms['UBICACION'] = df_wms['UBICACION'].astype(str).str.strip()

        st.success("🎉 ¡Archivos mapeados y analizados correctamente!")

        # Parsear la coordenada A-P1-C1-N1-A
        def extraer_componentes(row):
            cod = str(row['UBICACION'])
            partes = cod.split('-')
            estructura_id, columna, nivel, fondo_letra = "SIN CLASIFICAR", "1", "N1", "A"
            if len(partes) >= 5:
                estructura_id = partes[1]            
                columna = partes[2].replace('C', '')  
                nivel = partes[3]                    
                fondo_letra = partes[4]              
            return pd.Series([estructura_id, columna, nivel, fondo_letra])

        df_lay[['ESTRUCTURA_ID', 'COLUMNA', 'NIVEL', 'FONDO_LETRA']] = df_lay.apply(extraer_componentes, axis=1)
        depth_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        df_lay['FONDO_NUM'] = df_lay['FONDO_LETRA'].map(depth_map).fillna(1)

        # Agrupar stock por ubicación
        wms_grouped = df_wms.groupby('UBICACION').agg(
            skus_distintos=('CODIGO', 'count'),
            cantidad_piezas=('CANTIDAD', 'sum'),
            stock_sistema=('STOCK_SISTEMA', 'sum'),
            faltante_total=('FALTANTE', 'sum')
        ).reset_index()

        df_marge = pd.merge(df_lay, wms_grouped, on='UBICACION', how='left')

        for col in ['skus_distintos', 'cantidad_piezas', 'stock_sistema', 'faltante_total']:
            df_marge[col] = df_marge[col].fillna(0)

        df_marge['estado_ocupacion'] = df_marge['cantidad_piezas'].apply(
            lambda x: "OCUPADO" if x > 0 else "DISPONIBLE (VACÍO)"
        )

        # ==============================================================================
        # ASIGNACIÓN DE METRAJE POR FILTRADO DINÁMICO DE TIPO
        # ==============================================================================
        df_marge['m2_posicion'] = df_marge['TIPO'].map(m2_por_tipo).fillna(1.2)
        df_marge['m3_posicion'] = df_marge['m2_posicion'] * alto_estandar
        df_marge['m2_ocupados'] = df_marge.apply(lambda r: r['m2_posicion'] if r['estado_ocupacion'] == "OCUPADO" else 0.0, axis=1)

        # Totales Consolidados
        total_ubicaciones_global = len(df_marge)
        area_util_calculada = df_marge['m2_posicion'].sum()
        ocupadas_global = (df_marge['estado_ocupacion'] == 'OCUPADO').sum()
        pct_utilizacion_global = (ocupadas_global / total_ubicaciones_global) * 100 if total_ubicaciones_global > 0 else 0

        # Costos Unitarios
        costo_por_nicho_global = costo_fijo_total / total_ubicaciones_global if total_ubicaciones_global > 0 else 0
        costo_por_m2_alquilado = costo_fijo_total / area_total_almacen if area_total_almacen > 0 else 0
        costo_por_m2_util = costo_fijo_total / area_util_calculada if area_util_calculada > 0 else 0

        # ==============================================================================
        # SECCIÓN VISUAL: METRICAS CLAVE DE AUDITORÍA
        # ==============================================================================
        col_gauge, col_kpi = st.columns([1, 2])
        
        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = pct_utilizacion_global,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Utilización de Posiciones", 'font': {'size': 18, 'weight': 'bold'}},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#3b82f6"},
                    'bgcolor': "white",
                    'steps': [
                        {'range': [0, 50], 'color': '#fee2e2'}, 
                        {'range': [50, 80], 'color': '#fef08a'}, 
                        {'range': [80, 100], 'color': '#bbf7d0'} 
                    ]
                }
            ))
            fig_gauge.update_layout(height=280, margin=dict(t=30, b=0, l=10, r=10))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_kpi:
            st.write("### 💰 Estructura Financiera de Almacenamiento")
            kpi_f1, kpi_f2, kpi_f3 = st.columns(3)
            with kpi_f1:
                st.metric("🏢 Costo Real por Nicho (Slot)", f"S/. {costo_por_nicho_global:,.2f}", "Costo Unitario / Mes")
                st.metric("📐 Costo por m² Útil", f"S/. {costo_por_m2_util:,.2f}", "Basado en Racks/Pasillos")
            with kpi_f2:
                st.metric("💸 Costo Absorbido (Ocupado)", f"S/. {ocupadas_global * costo_por_nicho_global:,.2f}", "Sustentado por Stock")
                st.metric("📏 Costo por m² Alquilado", f"S/. {costo_por_m2_alquilado:,.2f}", "Sobre el metraje contratado")
            with kpi_f3:
                st.metric("⚠️ Costo Ocioso (Vacío)", f"S/. {(total_ubicaciones_global - ocupadas_global) * costo_por_nicho_global:,.2f}", "Dinero perdido en vacíos", delta_color="inverse")
                st.metric("📦 Área Útil Física", f"{area_util_calculada:,.1f} m²", f"{(area_util_calculada / area_total_almacen)*100:.1f}% del área total")

        # Visualizador de gastos fijos
        st.info(f"💡 **Nota sobre Activos:** Tu montacargas Hyster (Inversión: S/. {costo_hyster_pen:,.2f}) se está depreciando contablemente a una tasa del {tasa_depreciacion_anual}% anual. Su depreciación acumulada de estos 2 meses es de **S/. {depreciacion_acumulada_2meses:,.2f}**.")

        # ==============================================================================
        # DESGLOSE POR TIPO DE ESTRUCTURA DETALLADA
        # ==============================================================================
        st.write("---")
        st.subheader("🧱 Distribución y Rendimiento por Estructura")
        
        df_resumen_est = df_marge.groupby(['TIPO', 'ESTRUCTURA_ID']).apply(
            lambda g: pd.Series({
                'Nichos Totales': len(g),
                'Nichos Ocupados': (g['estado_ocupacion'] == 'OCUPADO').sum(),
                'Nichos Disponibles': (g['estado_ocupacion'] == 'DISPONIBLE (VACÍO)').sum(),
                'M² Útiles': g['m2_posicion'].sum(),
                'M³ Útiles': g['m3_posicion'].sum(),
                '% Ocupación': ((g['estado_ocupacion'] == 'OCUPADO').sum() / len(g)) * 100 if len(g) > 0 else 0
            })
        ).reset_index()

        df_resumen_est['Costo Operación'] = df_resumen_est['Nichos Totales'] * costo_por_nicho_global
        df_resumen_est['Costo Real x m²'] = df_resumen_est['Costo Operación'] / df_resumen_est['M² Útiles']

        col_tbl, col_chr = st.columns([5, 4])
        with col_tbl:
            st.dataframe(
                df_resumen_est.style.format({
                    'Nichos Totales': '{:,.0f}',
                    'Nichos Ocupados': '{:,.0f}',
                    'Nichos Disponibles': '{:,.0f}',
                    'M² Útiles': '{:,.1f} m²',
                    'M³ Útiles': '{:,.1f} m³',
                    '% Ocupación': '{:.1f}%',
                    'Costo Operación': 'S/. {:,.2f}',
                    'Costo Real x m²': 'S/. {:,.2f}'
                }),
                use_container_width=True,
                hide_index=True
            )
        with col_chr:
            df_resumen_est['S/. Ocupado'] = df_resumen_est['Nichos Ocupados'] * costo_por_nicho_global
            df_resumen_est['S/. Vacío'] = df_resumen_est['Nichos Disponibles'] * costo_por_nicho_global
            
            fig_bar_est = px.bar(
                df_resumen_est, 
                x='ESTRUCTURA_ID', 
                y=['S/. Ocupado', 'S/. Vacío'],
                barmode='stack',
                color_discrete_map={'S/. Ocupado': '#10b981', 'S/. Vacío': '#ef4444'},
                labels={'value': 'Inversión Logística (S/.)', 'variable': 'Estado', 'ESTRUCTURA_ID': 'Estructura'}
            )
            fig_bar_est.update_layout(plot_bgcolor='white', height=255, margin=dict(t=10, b=10))
            st.plotly_chart(fig_bar_est, use_container_width=True)

        # ==============================================================================
        # MAPA CALIENTE / PLANO 3D
        # ==============================================================================
        st.write("---")
        st.subheader("🗺️ Plano de Ocupación por Profundidad y Altura")
        
        estructuras_disponibles = sorted(df_marge['ESTRUCTURA_ID'].unique().tolist())
        sel_est_plano = st.selectbox("Seleccione la estructura para visualizar su plano:", estructuras_disponibles)
        
        df_plano = df_marge[df_marge['ESTRUCTURA_ID'] == sel_est_plano].copy()
        
        if not df_plano.empty:
            df_plano['NIVEL_NUM'] = df_plano['NIVEL'].str.extract(r'(\d+)').astype(float).fillna(1)
            df_plano['COLUMNA_NUM'] = pd.to_numeric(df_plano['COLUMNA'], errors='coerce')
            
            vista_plano = st.radio(
                "Elija el tipo de visualización espacial:",
                ["🎮 Gemelo Digital 3D", "📐 Vista de Corte 2D por Profundidad"],
                horizontal=True
            )
            
            if vista_plano == "🎮 Gemelo Digital 3D":
                fig_layout = px.scatter_3d(
                    df_plano, 
                    x='COLUMNA_NUM', 
                    y='FONDO_NUM', 
                    z='NIVEL_NUM', 
                    color='estado_ocupacion',
                    hover_name='UBICACION',
                    hover_data={
                        'FONDO_LETRA': True, 
                        'NIVEL': True,
                        'skus_distintos': True, 
                        'cantidad_piezas': True,
                        'COLUMNA_NUM': False,
                        'FONDO_NUM': False,
                        'NIVEL_NUM': False
                    },
                    labels={'COLUMNA_NUM': 'Columna', 'FONDO_NUM': 'Profundidad', 'NIVEL_NUM': 'Nivel'},
                    color_discrete_map={"OCUPADO": "#ef4444", "DISPONIBLE (VACÍO)": "#10b981"}
                )
                fig_layout.update_traces(marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
                fig_layout.update_layout(
                    scene=dict(
                        xaxis=dict(title='Columna', tickmode='linear', dtick=1),
                        yaxis=dict(title='Fondo', tickvals=[1, 2, 3, 4], ticktext=['A (Frente)', 'B', 'C', 'D (Fondo)']),
                        zaxis=dict(title='Nivel', tickvals=[1, 2, 3, 4, 5], ticktext=['N1', 'N2', 'N3', 'N4', 'N5']),
                        aspectratio=dict(x=2.5, y=1.2, z=1.5)
                    ),
                    margin=dict(l=0, r=0, b=0, t=50),
                    height=550
                )
                st.plotly_chart(fig_layout, use_container_width=True)
            else:
                lista_profundidades = sorted(df_plano['FONDO_LETRA'].unique().tolist())
                sel_prof = st.select_slider("Fondo:", options=lista_profundidades, value=lista_profundidades[0])
                
                df_slice = df_plano[df_plano['FONDO_LETRA'] == sel_prof]
                fig_layout = px.scatter(
                    df_slice, 
                    x='COLUMNA_NUM', 
                    y='NIVEL', 
                    color='estado_ocupacion',
                    hover_name='UBICACION',
                    hover_data={'skus_distintos': True, 'cantidad_piezas': True, 'COLUMNA_NUM': False},
                    color_discrete_map={"OCUPADO": "#ef4444", "DISPONIBLE (VACÍO)": "#10b981"}
                )
                fig_layout.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')), marker_size=28)
                fig_layout.update_layout(plot_bgcolor='#f8fafc', height=450)
                st.plotly_chart(fig_layout, use_container_width=True)

        # ==============================================================================
        # REPORTE DE AUDITORÍA DETALLADO PARA EXPORTAR
        # ==============================================================================
        st.write("---")
        st.write("### 📋 Reporte de Auditoría de Espacios")
        
        df_marge['costo_mantenimiento'] = costo_por_nicho_global
        df_marge['costo_efectivo_perdido'] = df_marge.apply(
            lambda r: costo_por_nicho_global if r['estado_ocupacion'] == "DISPONIBLE (VACÍO)" else 0.0, axis=1
        )
        
        df_mostrar = df_marge[[
            'UBICACION', 'TIPO', 'ESTRUCTURA_ID', 'COLUMNA', 'NIVEL', 'FONDO_LETRA', 
            'estado_ocupacion', 'skus_distintos', 'cantidad_piezas', 'm2_posicion', 'm3_posicion', 'costo_mantenimiento', 'costo_efectivo_perdido'
        ]].rename(columns={
            'UBICACION': 'UBICACIÓN',
            'TIPO': 'ESTRUCTURA',
            'ESTRUCTURA_ID': 'ID ESTRUCTURA',
            'FONDO_LETRA': 'FONDO',
            'estado_ocupacion': 'ESTADO REAL',
            'skus_distintos': 'SKUs',
            'cantidad_piezas': 'PIEZAS WMS',
            'm2_posicion': 'ÁREA (M²)',
            'm3_posicion': 'VOLUMEN (M³)',
            'costo_mantenimiento': 'COSTO SLOT',
            'costo_efectivo_perdido': 'COSTO OCIOSO'
        })

        st.dataframe(
            df_mostrar.style.format({
                'SKUs': '{:,.0f}',
                'PIEZAS WMS': '{:,.0f}',
                'ÁREA (M²)': '{:,.2f} m²',
                'VOLUMEN (M³)': '{:,.2f} m³',
                'COSTO SLOT': 'S/. {:,.2f}',
                'COSTO OCIOSO': 'S/. {:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Generar Excel de Descarga
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_mostrar.to_excel(writer, index=False, sheet_name='Auditoria_Espacial')
        st.download_button(
            label="📥 Descargar Auditoría de Costos a Excel",
            data=output.getvalue(),
            file_name="Auditoria_Espacios_Hyster_Precision.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Error procesando los datos cargados: {e}")
else:
    st.info("💡 Por favor, cargue el Layout Simplificado (Columna izquierda) y el Reporte WMS (Columna derecha) para iniciar la auditoría.")