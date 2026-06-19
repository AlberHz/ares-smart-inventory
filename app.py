# -*- coding: utf-8 -*-
"""
=============================================================================
ARES SMART INVENTORY CORE v11.2 — ENTERPRISE RESOURCE LOGISTICS ENGINE
Desarrollado bajo los Estándares Macrologísticos del MIT Center for Transportation & Logistics
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =========================================================================
# 1. CONFIGURACIÓN ESTRUCTURAL DE LA INTERFAZ EJECUTIVA DE ALTA GESTIÓN
# =========================================================================
st.set_page_config(
    page_title="Plataforma de Diagnóstico y Análisis Financiero de Inventarios",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS avanzados para entorno industrial (Tema Oscuro Profesional)
st.markdown("""
    <style>
    /* Estilos generales de la aplicación */
    .reportview-container { 
        background: #0f1116; 
    }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Bloques contenedores premium para métricas de costos */
    .metric-card-premium {
        background-color: #1a1f2c;
        border-radius: 8px;
        padding: 22px;
        border-left: 5px solid #00ebc7;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-card-alert {
        background-color: #1a1f2c;
        border-radius: 8px;
        padding: 22px;
        border-left: 5px solid #ef553b;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-card-warning {
        background-color: #1a1f2c;
        border-radius: 8px;
        padding: 22px;
        border-left: 5px solid #fecb52;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-card-financial {
        background-color: #16222f;
        border-radius: 8px;
        padding: 22px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-title-executive { 
        font-size: 11px; 
        color: #94a3b8; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.9px; 
    }
    .metric-value-executive { 
        font-size: 24px; 
        color: #ffffff; 
        font-weight: 800; 
        padding: 6px 0; 
    }
    .metric-subtitle-executive { 
        font-size: 11px; 
        color: #94a3b8; 
        font-weight: 500; 
    }
    .highlight-cyan { color: #00ebc7; font-weight: 700; }
    .highlight-red { color: #ef553b; font-weight: 700; }
    .highlight-blue { color: #3b82f6; font-weight: 700; }
    
    /* Separadores de sección */
    .section-divider {
        margin: 30px 0;
        border-bottom: 2px solid #2e374a;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado Corporativo Principal
st.title("🛡️ Plataforma Avanzada de Análisis de Inventarios y Auditoría de Costos")
st.markdown("""
**Macro-Logistics Enterprise Solution** | Diagnóstico avanzado de capital inmovilizado en Soles (S/.), simulación de costos de almacenamiento y auditoría integral para la toma de decisiones financieras a nivel S&OP.
""")

# =========================================================================
# 2. PARÁMETROS FINANCIEROS GLOBALES DE ENTRADA (SIDEBAR CONTROL MASTER)
# =========================================================================
st.sidebar.header("💰 Configuración de Tasas Financieras")
tasa_holding_anual = st.sidebar.slider(
    "Costo Anual de Retención de Stock (Holding Cost % del Costo SKU):", 
    min_value=5.0, max_value=40.0, value=18.0, step=0.5,
    help="Porcentaje del valor del inventario que representa mantener el stock en almacén por un año (seguros, mermas, costo de oportunidad)."
) / 100.0

costo_arriendo_m2_mes = st.sidebar.number_input(
    "Costo Logístico de Espacio Fisico por Unidad Equivalente/Mes (S/.):",
    min_value=0.0, value=1.50, step=0.10,
    help="Costo de infraestructura prorrateado por cada unidad física almacenada mensualmente en Soles."
)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Filtros de Control Jerárquico")

# =========================================================================
# 3. ALGORITMOS LOGÍSTICOS Y FUNCIONES MATEMÁTICAS AVANZADAS
# =========================================================================

def helper_cargar_y_limpiar_datos(file_object):
    """
    Carga adaptativa de archivos Excel o CSV. Realiza el tratamiento de cadenas de texto,
    elimina columnas sin información y estandariza las cabeceras del set de datos.
    """
    if file_object is None:
        return None
    try:
        if file_object.name.endswith('.csv'):
            df = pd.read_csv(file_object)
        else:
            df = pd.read_excel(file_object)
            
        df.columns = df.columns.str.strip().str.upper()
        df = df.loc[:, ~df.columns.str.contains('^UNNAMED|^$')]
        
        if 'CODIGO' in df.columns:
            df['CODIGO'] = df['CODIGO'].astype(str).str.strip().str.upper()
            
        return df
    except Exception as e:
        st.error(f"Error en la pre-lectura del archivo {file_object.name}: {str(e)}")
        return None


def clasificar_aging_gerencial(dias_inactivos):
    """
    Segmentación estricta de curvas de obsolescencia operativa según el capital inmovilizado.
    """
    if pd.isna(dias_inactivos):
        return "04. INMOVILIZADO CRÍTICO (>180 días)"
        
    if dias_inactivos <= 30:
        return "01. Rotación Saludable (<30 días)"
    elif dias_inactivos <= 90:
        return "02. Alerta Preventiva (30-90 días)"
    elif dias_inactivos <= 180:
        return "03. Riesgo Estructural (90-180 días)"
    else:
        return "04. INMOVILIZADO CRÍTICO (>180 días)"


def algoritmo_abc_frecuencia(row_dataframe):
    """
    Clasificación de Pareto basada estrictamente en la frecuencia de las notas de salida (NS).
    """
    if 'FRECUENCIA_SALIDAS' not in row_dataframe or row_dataframe['FRECUENCIA_SALIDAS'] == 0:
        return 'Sin Rotación'
        
    porcentaje_acumulado = row_dataframe['%_ACUMULADO']
    
    if porcentaje_acumulado <= 0.80:
        return 'A (Alta Rotación)'
    elif porcentaje_acumulado <= 0.95:
        return 'B (Media Rotación)'
    else:
        return 'C (Baja Rotación)'


def calcular_matriz_criticidad_cruzada(row_dataframe):
    """
    Cruza la frecuencia operativa (ABC) con el envejecimiento (Aging) para aislar stock muerto.
    """
    if 'CATEGORIA_ABC' not in row_dataframe or 'DIAS_INACTIVOS' not in row_dataframe:
        return "🟢 Surtido Óptimo"
        
    categoria_abc = row_dataframe['CATEGORIA_ABC']
    dias = row_dataframe['DIAS_INACTIVOS']
    stock_actual = row_dataframe.get('STOCK', 0)
    
    if categoria_abc == 'Sin Rotación' and dias > 180 and stock_actual > 0:
        return "🔴 Stock Muerto (Sin Rotación & Envejecido)"
    elif categoria_abc == 'A (Alta Rotación)' and stock_actual <= 0:
        return "⚠️ Riesgo de Quiebre Operacional"
    elif dias > 90 and stock_actual > 0 and categoria_abc in ['C (Baja Rotación)', 'Sin Rotación']:
        return "🟡 Capital Dormido en Almacén"
    else:
        return "🟢 Surtido Óptimo"


def calcular_estrategia_mitigacion(row):
    """
    Determina planes de acción dinámicos basados en costos e inactividad.
    """
    criticidad = row.get('CRITICIDAD_LOGISTICA', '🟢 Surtido Óptimo')
    costo_total_inv = row.get('COSTO_TOTAL_INVENTARIO', 0)
    
    if "🔴 Stock Muerto" in criticidad:
        if costo_total_inv > 10000:
            return "Liquidar vía Descuento Agresivo / Venta en Lote Corporativo"
        return "Depuración Directa de Almacén / Destrucción Contable Certificada"
    elif "🟡 Capital Dormido" in criticidad:
        return "Frenar Órdenes de Compra Automáticas y Transferir a Sedes de Mayor Demanda"
    elif "⚠️ Riesgo de Quiebre" in criticidad:
        return "Generar Alerta de Reabastecimiento Urgente / Compra Spot Expeditada"
    return "Mantener bajo Lógica Just-In-Time / Monitorear Nivel de Servicio"

# =========================================================================
# 4. INTERFAZ DE CARGA DE ARCHIVOS FUENTE
# =========================================================================
st.markdown("### 📥 Panel de Sincronización de Datos Maestros")
col_upload_left, col_upload_right = st.columns(2)

with col_upload_left:
    file_movs = st.file_uploader(
        "1. Archivo de Movimientos Históricos (Estructura: FECHA, CODIGO, CT, CANTIDAD)", 
        type=["xlsx", "csv"], 
        key="uploader_movs",
        help="Historial de movimientos contables de almacén (Kardex). Filtros críticos: CT = 'NS' (Salidas) e 'NI' (Ingresos)."
    )

with col_upload_right:
    file_stock = st.file_uploader(
        "2. Maestro de Stock Actual Base y Costos (Estructura: CODIGO, DESCRIPCIÓN, FAMILIA, STOCK, COSTO)", 
        type=["xlsx", "csv"], 
        key="uploader_stock",
        help="Listado maestro oficial. Debe incluir la columna COSTO unitario en Soles para habilitar la suite financiera."
    )

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# =========================================================================
# 5. MOTOR PROCESADOR CENTRAL Y MOTOR FINANCIERO DE COSTOS (DATA ENGINE)
# =========================================================================
if file_movs and file_stock:
    try:
        df_movs_raw = helper_cargar_y_limpiar_datos(file_movs)
        df_stock_raw = helper_cargar_y_limpiar_datos(file_stock)
        
        # Validaciones de consistencia de datos de las columnas maestras
        columnas_movs_requeridas = ['FECHA', 'CODIGO', 'CT', 'CANTIDAD']
        columnas_stock_requeridas = ['CODIGO', 'DESCRIPCIÓN', 'FAMILIA', 'STOCK', 'COSTO']
        
        missing_movs = [col for col in columnas_movs_requeridas if col not in df_movs_raw.columns]
        missing_stock = [col for col in columnas_stock_requeridas if col not in df_stock_raw.columns]
        
        if missing_movs:
            st.error(f"Estructura incorrecta en Kardex de Movimientos. Faltan las siguientes columnas: {missing_movs}")
            st.stop()
        if missing_stock:
            st.error(f"Estructura incorrecta en Maestro de Stock. Faltan las siguientes columnas: {missing_stock}")
            st.stop()
            
        # Limpieza, formateo tipográfico e igualación de claves
        df_stock_raw['CODIGO'] = df_stock_raw['CODIGO'].astype(str).str.strip().str.upper()
        df_movs_raw['CODIGO'] = df_movs_raw['CODIGO'].astype(str).str.strip().str.upper()
        
        df_stock_raw['FAMILIA'] = df_stock_raw['FAMILIA'].fillna('SIN FAMILIA').astype(str).str.strip().str.upper()
        df_stock_raw['DESCRIPCIÓN'] = df_stock_raw['DESCRIPCIÓN'].fillna('PRODUCTO SIN DETALLE RELEVANTE').astype(str).str.strip()
        df_stock_raw['STOCK'] = pd.to_numeric(df_stock_raw['STOCK'], errors='coerce').fillna(0.0)
        df_stock_raw['COSTO'] = pd.to_numeric(df_stock_raw['COSTO'], errors='coerce').fillna(0.0)
        
        df_stock_clean = df_stock_raw[df_stock_raw['CODIGO'] != 'NAN'].copy()
        maestro_articulos_dict = df_stock_clean.drop_duplicates(subset=['CODIGO']).set_index('CODIGO')
        
        df_movs_raw['FECHA'] = pd.to_datetime(df_movs_raw['FECHA'], errors='coerce')
        df_movs_clean = df_movs_raw.dropna(subset=['FECHA', 'CODIGO', 'CT']).copy()
        df_movs_clean['CANTIDAD'] = pd.to_numeric(df_movs_clean['CANTIDAD'], errors='coerce').fillna(0.0)
        
        fecha_corte_sistema = df_movs_clean['FECHA'].max()
        
        # Eliminación proactiva de redundancias funcionales antes de realizar la unión (Merge)
        for col_to_drop in ['FAMILIA', 'DESCRIPCIÓN', 'COSTO']:
            if col_to_drop in df_movs_clean.columns:
                df_movs_clean = df_movs_clean.drop(columns=[col_to_drop])
                
        df_movs_enriquecido = df_movs_clean.merge(
            maestro_articulos_dict[['DESCRIPCIÓN', 'FAMILIA', 'COSTO']], 
            on='CODIGO', 
            how='left'
        )
        df_movs_enriquecido['FAMILIA'] = df_movs_enriquecido['FAMILIA'].fillna('OTRAS').astype(str).str.upper()
        df_movs_enriquecido['DESCRIPCIÓN'] = df_movs_enriquecido['DESCRIPCIÓN'].fillna('DESCONOCIDO')
        df_movs_enriquecido['COSTO'] = df_movs_enriquecido['COSTO'].fillna(0.0)
        
        # Aislamiento analítico de flujos comerciales específicos (Demanda Real)
        df_notas_salida = df_movs_enriquecido[df_movs_enriquecido['CT'] == 'NS'].copy()
        df_notas_salida['AÑO_MES_PERIOD'] = df_notas_salida['FECHA'].dt.to_period('M')
        
        # 5.1. Días de Inactividad Operativa Global por SKU
        df_global_ultima_actividad = df_movs_enriquecido.groupby('CODIGO')['FECHA'].max().reset_index()
        df_global_ultima_actividad = df_global_ultima_actividad.rename(columns={'FECHA': 'FECHA_ULTIMA_ACTIVIDAD'})
        
        # 5.2. Análisis de Volatilidad y Predictibilidad S&OP
        df_demanda_agrupada_mes = df_notas_salida.groupby(['CODIGO', 'AÑO_MES_PERIOD'])['CANTIDAD'].sum().reset_index()
        df_metricas_cv = df_demanda_agrupada_mes.groupby('CODIGO')['CANTIDAD'].agg(['mean', 'std']).reset_index()
        df_metricas_cv = df_metricas_cv.rename(columns={'mean': 'CONSUMO_PROMEDIO_MENSUAL', 'std': 'DESVIACION_ESTANDAR_MENSUAL'})
        df_metricas_cv['CV'] = (df_metricas_cv['DESVIACION_ESTANDAR_MENSUAL'] / df_metricas_cv['CONSUMO_PROMEDIO_MENSUAL']).fillna(0.0)
        
        # 5.3. Frecuencia Absoluta Operativa para Pareto ABC
        df_global_frecuencia_salidas = df_notas_salida.groupby('CODIGO').size().reset_index(name='FRECUENCIA_SALIDAS')

        # =========================================================================
        # 6. MODELO MATEMÁTICO REVERSIBLE DE CIERRES HISTÓRICOS DE INVENTARIO
        # =========================================================================
        df_movs_enriquecido['AÑO_MES_PERIOD'] = df_movs_enriquecido['FECHA'].dt.to_period('M')
        secuencia_meses_ordenados = sorted(df_movs_enriquecido['AÑO_MES_PERIOD'].dropna().unique())
        universo_total_codigos = set(df_movs_enriquecido['CODIGO'].dropna().unique()).union(set(df_stock_clean['CODIGO'].dropna().unique()))
        
        diccionario_stock_actual_almacen = df_stock_clean.set_index('CODIGO')['STOCK'].to_dict()
        registro_reconstruccion_stock = {cod: diccionario_stock_actual_almacen.get(cod, 0.0) for cod in universo_total_codigos}
        
        matriz_cierres_historicos_calculados = {}
        secuencia_meses_reversa = sorted(df_movs_enriquecido['AÑO_MES_PERIOD'].unique(), reverse=True)
        
        for periodo_mes in secuencia_meses_reversa:
            df_movimientos_del_mes = df_movs_enriquecido[df_movs_enriquecido['AÑO_MES_PERIOD'] == periodo_mes]
            resumen_transacciones_mes = df_movimientos_del_mes.groupby(['CODIGO', 'CT'])['CANTIDAD'].sum().unstack(fill_value=0.0)
            
            if 'NI' not in resumen_transacciones_mes.columns:
                resumen_transacciones_mes['NI'] = 0.0
            if 'NS' not in resumen_transacciones_mes.columns:
                resumen_transacciones_mes['NS'] = 0.0
                
            matriz_cierres_historicos_calculados[periodo_mes] = {}
            
            for codigo_sku in universo_total_codigos:
                cantidad_ingresada_ni = resumen_transacciones_mes.loc[codigo_sku, 'NI'] if codigo_sku in resumen_transacciones_mes.index else 0.0
                cantidad_salida_ns = resumen_transacciones_mes.loc[codigo_sku, 'NS'] if codigo_sku in resumen_transacciones_mes.index else 0.0
                
                # Deshacer transacciones en reversa: Stock Inicial = Stock Final - Ingresos + Salidas
                stock_al_inicio_de_periodo = registro_reconstruccion_stock[codigo_sku] - cantidad_ingresada_ni + cantidad_salida_ns
                stock_al_inicio_de_periodo = max(0.0, stock_al_inicio_de_periodo)
                
                matriz_cierres_historicos_calculados[periodo_mes][codigo_sku] = stock_al_inicio_de_periodo
                registro_reconstruccion_stock[codigo_sku] = stock_al_inicio_de_periodo

        # Consolidación transaccional indexada del histórico financiero mensual
        registros_series_temporales_consolidados = []
        for periodo_mes in secuencia_meses_ordenados:
            df_movimientos_del_mes = df_movs_enriquecido[df_movs_enriquecido['AÑO_MES_PERIOD'] == periodo_mes]
            resumen_transacciones_mes = df_movimientos_del_mes.groupby(['CODIGO', 'CT'])['CANTIDAD'].sum().unstack(fill_value=0.0)
            
            if 'NI' not in resumen_transacciones_mes.columns:
                resumen_transacciones_mes['NI'] = 0.0
            if 'NS' not in resumen_transacciones_mes.columns:
                resumen_transacciones_mes['NS'] = 0.0
                
            for codigo_sku in universo_total_codigos:
                cantidad_ingresada_ni = resumen_transacciones_mes.loc[codigo_sku, 'NI'] if codigo_sku in resumen_transacciones_mes.index else 0.0
                cantidad_salida_ns = resumen_transacciones_mes.loc[codigo_sku, 'NS'] if codigo_sku in resumen_transacciones_mes.index else 0.0
                
                stock_inicial_mes = matriz_cierres_historicos_calculados[periodo_mes].get(codigo_sku, 0.0)
                stock_final_mes = max(0.0, stock_inicial_mes + cantidad_ingresada_ni - cantidad_salida_ns)
                
                meta_descripcion = maestro_articulos_dict.loc[codigo_sku, 'DESCRIPCIÓN'] if codigo_sku in maestro_articulos_dict.index else 'DESCONOCIDO'
                meta_familia = maestro_articulos_dict.loc[codigo_sku, 'FAMILIA'] if codigo_sku in maestro_articulos_dict.index else 'OTRAS'
                meta_costo_unitario = maestro_articulos_dict.loc[codigo_sku, 'COSTO'] if codigo_sku in maestro_articulos_dict.index else 0.0
                
                # Incorporación de capas analíticas financieras mensuales
                costo_total_mes_cierre = stock_final_mes * meta_costo_unitario
                holding_cost_mensual_calculado = costo_total_mes_cierre * (tasa_holding_anual / 12.0)
                arriendo_cost_mensual_calculado = stock_final_mes * costo_arriendo_m2_mes
                
                registros_series_temporales_consolidados.append({
                    'AÑO_MES': periodo_mes.strftime('%Y-%m'),
                    'CODIGO': codigo_sku,
                    'DESCRIPCIÓN': meta_descripcion,
                    'FAMILIA': meta_familia,
                    'COSTO_UNITARIO': meta_costo_unitario,
                    'STOCK_INICIAL': stock_inicial_mes,
                    'INGRESOS': cantidad_ingresada_ni,
                    'SALIDAS': cantidad_salida_ns,
                    'STOCK_FINAL': stock_final_mes,
                    'VALORIZACION_CIERRE': costo_total_mes_cierre,
                    'COSTO_RETENCION_HOLDING': holding_cost_mensual_calculado,
                    'COSTO_OCUPACION_ESPACIO': arriendo_cost_mensual_calculado,
                    'COSTO_LOGISTICO_TOTAL': holding_cost_mensual_calculado + arriendo_cost_mensual_calculado
                })
                
        df_historico_grande_maestro = pd.DataFrame(registros_series_temporales_consolidados)

        # =========================================================================
        # 7. FILTROS JERÁRQUICOS DINÁMICOS (BARRA LATERAL)
        # =========================================================================
        lista_familias_validas = sorted([f for f in df_stock_clean['FAMILIA'].unique() if f not in ['NAN', 'NONE', 'UNKNOWN']])
        opciones_familias_desplegable = ["TODAS LAS FAMILIAS"] + lista_familias_validas
        familia_seleccionada = st.sidebar.selectbox("1. Filtrar por Familia Logística:", opciones_familias_desplegable)
        
        if familia_seleccionada != "TODAS LAS FAMILIAS":
            df_codigos_filtrados_por_familia = df_stock_clean[df_stock_clean['FAMILIA'] == familia_seleccionada]
            lista_codigos_disponibles = sorted(df_codigos_filtrados_por_familia['CODIGO'].unique())
        else:
            lista_codigos_disponibles = sorted(df_stock_clean['CODIGO'].unique())
            
        opciones_codigos_desplegable = ["TODOS LOS SKU"] + lista_codigos_disponibles
        codigo_seleccionado = st.sidebar.selectbox("2. Filtrar SKU Específico (Filtro para Gráficos Avanzados):", opciones_codigos_desplegable)

        # Configuración de pestañas de visualización ejecutiva
        tab_dashboard, tab_financial_audit, tab_data_pbi = st.tabs([
            "📊 Executive Health Dashboard", 
            "💰 Financial & Cost Audit Suite",
            "📥 Data Warehouse Clean (Power BI)"
        ])

        # =========================================================================
        # 8. PESTAÑA 1: PANEL METROLÓGICO DEL INVENTARIO (MIT STANDARDS)
        # =========================================================================
        with tab_dashboard:
            
            # Reconstrucción de la matriz consolidada del Dashboard
            df_unificado_dashboard = df_stock_clean.copy()
            df_unificado_dashboard = df_unificado_dashboard.merge(df_global_ultima_actividad, on='CODIGO', how='left')
            df_unificado_dashboard = df_unificado_dashboard.merge(df_global_frecuencia_salidas, on='CODIGO', how='left').fillna({'FRECUENCIA_SALIDAS': 0.0})
            
            df_unificado_dashboard['DIAS_INACTIVOS'] = (fecha_corte_sistema - pd.to_datetime(df_unificado_dashboard['FECHA_ULTIMA_ACTIVIDAD'])).dt.days.fillna(365).astype(int)
            df_unificado_dashboard['RANGO_AGING'] = df_unificado_dashboard['DIAS_INACTIVOS'].apply(clasificar_aging_gerencial)
            
            # Algoritmia estricta de Pareto por frecuencia operativa
            df_unificado_dashboard = df_unificado_dashboard.sort_values(by='FRECUENCIA_SALIDAS', ascending=False).reset_index(drop=True)
            suma_total_frecuencia_operativa = df_unificado_dashboard['FRECUENCIA_SALIDAS'].sum()
            
            if suma_total_frecuencia_operativa > 0:
                df_unificado_dashboard['%_ACUMULADO'] = (df_unificado_dashboard['FRECUENCIA_SALIDAS'] / suma_total_frecuencia_operativa).cumsum()
            else:
                df_unificado_dashboard['%_ACUMULADO'] = 1.0
                
            df_unificado_dashboard['CATEGORIA_ABC'] = df_unificado_dashboard.apply(algoritmo_abc_frecuencia, axis=1)
            df_unificado_dashboard['CRITICIDAD_LOGISTICA'] = df_unificado_dashboard.apply(calcular_matriz_criticidad_cruzada, axis=1)
            
            # Inyección de cálculos de costos estáticos de inventario actual
            df_unificado_dashboard['COSTO_TOTAL_INVENTARIO'] = df_unificado_dashboard['STOCK'] * df_unificado_dashboard['COSTO']
            df_unificado_dashboard['COSTO_MANTENIMIENTO_ANUAL'] = df_unificado_dashboard['COSTO_TOTAL_INVENTARIO'] * tasa_holding_anual
            df_unificado_dashboard['ACCION_MITIGACION_SUGERIDA'] = df_unificado_dashboard.apply(calcular_estrategia_mitigacion, axis=1)

            # Aplicación de filtros maestros jerárquicos
            if familia_seleccionada != "TODAS LAS FAMILIAS":
                df_visualizacion_dashboard = df_unificado_dashboard[df_unificado_dashboard['FAMILIA'] == familia_seleccionada].copy()
            else:
                df_visualizacion_dashboard = df_unificado_dashboard.copy()

            total_skus_muestra_activa = df_visualizacion_dashboard['CODIGO'].nunique()

            # Matriz superior de KPIs Operacionales y Financieros Básicos
            st.markdown(f"#### 📐 Indicadores Estructurales Base ({total_skus_muestra_activa} SKUs en la Vista)")
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            
            with kpi_col1:
                total_unidades_fisicas = df_visualizacion_dashboard['STOCK'].sum()
                st.markdown(f"""
                <div class='metric-card-premium'>
                    <div class='metric-title-executive'>Unidades en Stock</div>
                    <div class='metric-value-executive'>{total_unidades_fisicas:,.0f}</div>
                    <div class='metric-subtitle-executive'>Volumen físico total en almacenes.</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_col2:
                total_valorizado_capital = df_visualizacion_dashboard['COSTO_TOTAL_INVENTARIO'].sum()
                st.markdown(f"""
                <div class='metric-card-financial'>
                    <div class='metric-title-executive'>Valorización Total (Costo)</div>
                    <div class='metric-value-executive'>S/. {total_valorizado_capital:,.2f}</div>
                    <div class='metric-subtitle-executive'>Capital de trabajo activo en piso (Soles).</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_col3:
                total_skus_muertos = df_visualizacion_dashboard[df_visualizacion_dashboard['CRITICIDAD_LOGISTICA'].str.contains('🔴')]['CODIGO'].nunique()
                valor_skus_muertos = df_visualizacion_dashboard[df_visualizacion_dashboard['CRITICIDAD_LOGISTICA'].str.contains('🔴')]['COSTO_TOTAL_INVENTARIO'].sum()
                st.markdown(f"""
                <div class='metric-card-alert'>
                    <div class='metric-title-executive'>SKUs en Estatus Muerto</div>
                    <div class='metric-value-executive'>{total_skus_muertos}</div>
                    <div class='metric-subtitle-executive'>Representa un valor de <span class='highlight-red'>S/. {valor_skus_muertos:,.2f}</span></div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_col4:
                total_skus_alta_rotacion = df_visualizacion_dashboard[df_visualizacion_dashboard['CATEGORIA_ABC'] == 'A (Alta Rotación)']['CODIGO'].nunique()
                st.markdown(f"""
                <div class='metric-card-warning'>
                    <div class='metric-title-executive'>SKUs Alta Rotación (A)</div>
                    <div class='metric-value-executive'>{total_skus_alta_rotacion}</div>
                    <div class='metric-subtitle-executive'>Concentran el 80% de salidas de almacén.</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # ---------------------------------------------------------------------
            # GRÁFICO 1 Y 2: ANÁLISIS DUAL DE DISTRIBUCIONES FÍSICAS DE ALMACÉN
            # ---------------------------------------------------------------------
            st.markdown("#### 📊 Distribución Estructural de Unidades Físicas en Almacén")
            g2_col1, g2_col2 = st.columns(2)
            
            df_resumen_barras_aging = df_visualizacion_dashboard.groupby('RANGO_AGING', observed=False)['STOCK'].agg(['sum', 'count']).reset_index()
            df_resumen_barras_abc = df_visualizacion_dashboard.groupby('CATEGORIA_ABC', observed=False)['STOCK'].agg(['sum', 'count']).reset_index()

            with g2_col1:
                fig_barras_aging = px.bar(
                    df_resumen_barras_aging, x='RANGO_AGING', y='sum', color='RANGO_AGING', text_auto='.0f',
                    title="Gráfico 1: Unidades Disponibles por Rango de Inactividad (Aging)",
                    labels={'sum': 'Unidades en Piso', 'RANGO_AGING': 'Rango Temporal de Envejecimiento'},
                    color_discrete_map={"01. Rotación Saludable (<30 días)": "#00cc96", "02. Alerta Preventiva (30-90 días)": "#fecb52", "03. Riesgo Estructural (90-180 días)": "#ff9900", "04. INMOVILIZADO CRÍTICO (>180 días)": "#ef553b"}
                )
                fig_barras_aging.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_barras_aging, use_container_width=True)
                
            with g2_col2:
                fig_barras_abc = px.bar(
                    df_resumen_barras_abc, x='CATEGORIA_ABC', y='sum', color='CATEGORIA_ABC', text_auto='.0f',
                    title="Gráfico 2: Unidades Disponibles por Segmentación de Demanda ABC",
                    labels={'sum': 'Unidades en Piso', 'CATEGORIA_ABC': 'Categoría Operativa de Salidas'},
                    color_discrete_sequence=['#00ebc7', '#fecb52', '#ef553b', '#6b7280']
                )
                fig_barras_abc.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_barras_abc, use_container_width=True)

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # ---------------------------------------------------------------------
            # GRÁFICO 3: MATRIZ DE CRITICIDAD CRUZADA OPERACIONAL
            # ---------------------------------------------------------------------
            st.markdown(f"#### 🔀 3. Cruce Analítico de Riesgo Operativo: Intersección ABC vs. Perfil de Inactividad")
            df_agrupamiento_cruce_criticidad = df_visualizacion_dashboard.groupby(['CATEGORIA_ABC', 'CRITICIDAD_LOGISTICA']).size().reset_index(name='CANTIDAD_SKUS_UNIKOS')
            
            fig_cruce_gerencial = px.bar(
                df_agrupamiento_cruce_criticidad, x='CATEGORIA_ABC', y='CANTIDAD_SKUS_UNIKOS', color='CRITICIDAD_LOGISTICA', barmode='group', text_auto=True,
                title=f"Matriz Corporativa de Conteo de Códigos SKU por Nivel de Riesgo Operacional — Filtro: {familia_seleccionada}",
                labels={'CANTIDAD_SKUS_UNIKOS': 'Cantidad de SKUs Únicos', 'CATEGORIA_ABC': 'Estatus de Rotación Contable'},
                color_discrete_map={"🔴 Stock Muerto (Sin Rotación & Envejecido)": "#ef553b", "⚠️ Riesgo de Quiebre Operacional": "#fecb52", "🟡 Capital Dormido en Almacén": "#ff9900", "🟢 Surtido Óptimo": "#00cc96"}
            )
            fig_cruce_gerencial.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            st.plotly_chart(fig_cruce_gerencial, use_container_width=True)

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # Aplicación de filtros específicos avanzados de series temporales
            df_filtros_series_temporales = df_historico_grande_maestro.copy()
            if familia_seleccionada != "TODAS LAS FAMILIAS":
                df_filtros_series_temporales = df_filtros_series_temporales[df_filtros_series_temporales['FAMILIA'] == familia_seleccionada]
            if codigo_seleccionado != "TODOS LOS SKU":
                df_filtros_series_temporales = df_filtros_series_temporales[df_filtros_series_temporales['CODIGO'] == codigo_seleccionado]

            skus_en_series_temporales = df_filtros_series_temporales['CODIGO'].nunique()

            # ---------------------------------------------------------------------
            # GRÁFICO 4: EVOLUCIÓN HISTÓRICA DE STOCK DE CIERRE MENSUAL
            # ---------------------------------------------------------------------
            st.markdown(f"#### 📈 4. Evolución Histórica de Volumen de Cierres de Inventario y Variación Mensual MoM")
            df_g4_agrupamiento_mes = df_filtros_series_temporales.groupby('AÑO_MES')['STOCK_FINAL'].sum().reset_index()
            df_g4_agrupamiento_mes['VARIACION_NETA_INTERMENSUAL'] = df_g4_agrupamiento_mes['STOCK_FINAL'].diff().fillna(0.0)
            
            fig_lineas_g4 = go.Figure()
            fig_lineas_g4.add_trace(go.Scatter(
                x=df_g4_agrupamiento_mes['AÑO_MES'], y=df_g4_agrupamiento_mes['STOCK_FINAL'], mode='lines+markers+text', name='Stock Cierre de Mes (Unidades)',
                text=df_g4_agrupamiento_mes['STOCK_FINAL'].map(lambda val: f"{val:,.0f}"), textposition="top center",
                line=dict(color='#00ebc7', width=3), marker=dict(size=8)
            ))
            fig_lineas_g4.add_trace(go.Bar(
                x=df_g4_agrupamiento_mes['AÑO_MES'], y=df_g4_agrupamiento_mes['VARIACION_NETA_INTERMENSUAL'], name='Variación Neta de Unidades (MoM)',
                marker_color=np.where(df_g4_agrupamiento_mes['VARIACION_NETA_INTERMENSUAL'] >= 0, '#00cc96', '#ef553b'), opacity=0.5
            ))
            fig_lineas_g4.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Eje Temporal de Análisis", yaxis_title="Unidades Físicas", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_lineas_g4, use_container_width=True)

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # ---------------------------------------------------------------------
            # GRÁFICO 5: BALANCE DE ENTRADAS Y SALIDAS (FLUJOS)
            # ---------------------------------------------------------------------
            st.markdown(f"#### 🔄 5. Balance Transaccional Mensual y Tasa de Consumo del Disponible")
            df_g5_agrupamiento_flujo = df_filtros_series_temporales.groupby('AÑO_MES')[['STOCK_INICIAL', 'INGRESOS', 'SALIDAS', 'STOCK_FINAL']].sum().reset_index()
            df_g5_agrupamiento_flujo['INVENTARIO_DISPONIBLE_TOTAL'] = df_g5_agrupamiento_flujo['STOCK_INICIAL'] + df_g5_agrupamiento_flujo['INGRESOS']
            df_g5_agrupamiento_flujo['TASA_CONSUMO_PORCENTUAL'] = np.where(df_g5_agrupamiento_flujo['INVENTARIO_DISPONIBLE_TOTAL'] > 0, (df_g5_agrupamiento_flujo['SALIDAS'] / df_g5_agrupamiento_flujo['INVENTARIO_DISPONIBLE_TOTAL']) * 100.0, 0.0)
            
            fig_interactivo_g6 = go.Figure()
            fig_interactivo_g6.add_trace(go.Bar(x=df_g5_agrupamiento_flujo['AÑO_MES'], y=df_g5_agrupamiento_flujo['INGRESOS'], name='Ingresos Reales (NI)', marker_color='#00cc96'))
            fig_interactivo_g6.add_trace(go.Bar(x=df_g5_agrupamiento_flujo['AÑO_MES'], y=df_g5_agrupamiento_flujo['SALIDAS'], name='Salidas Realizadas (NS)', marker_color='#ef553b'))
            fig_interactivo_g6.add_trace(go.Bar(x=df_g5_agrupamiento_flujo['AÑO_MES'], y=df_g5_agrupamiento_flujo['STOCK_FINAL'], name='Stock Remanente al Cierre', marker_color='#3b82f6', opacity=0.35))
            fig_interactivo_g6.add_trace(go.Scatter(x=df_g5_agrupamiento_flujo['AÑO_MES'], y=df_g5_agrupamiento_flujo['TASA_CONSUMO_PORCENTUAL'], name='% Tasa Eficiencia de Despacho', mode='lines+markers', line=dict(color='#fecb52', width=3, dash='dash'), yaxis='y2'))
            
            fig_interactivo_g6.update_layout(
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', barmode='group', xaxis_title="Meses Analizados", yaxis_title="Volumen de Unidades",
                yaxis2=dict(title="Tasa Mensual de Rotación (%)", overlaying='y', side='right', range=[0, 105], ticksuffix="%"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_interactivo_g6, use_container_width=True)

        # =========================================================================
        # 9. PESTAÑA 2: SUITE EXCLUSIVA DE AUDITORÍA FINANCIERA Y COSTOS TOTALES
        # =========================================================================
        with tab_financial_audit:
            st.subheader("💰 Auditoría Avanzada de Costos de Retención e Inmovilización Financiera")
            st.markdown("Cálculos avanzados de costos logísticos aplicados directamente sobre la muestra filtrada actual expresados en **Soles (S/.)**.")
            
            # Bloque de KPIs Financieros Avanzados de Costos
            aud_col1, aud_col2, aud_col3, aud_col4 = st.columns(4)
            
            # Agregaciones directas de costos logísticos de la muestra de series temporales
            total_holding_cost_historico = df_filtros_series_temporales['COSTO_RETENCION_HOLDING'].sum()
            total_arriendo_cost_historico = df_filtros_series_temporales['COSTO_OCUPACION_ESPACIO'].sum()
            total_logistico_financiero_historico = df_filtros_series_temporales['COSTO_LOGISTICO_TOTAL'].sum()
            
            with aud_col1:
                st.markdown(f"""
                <div class='metric-card-financial'>
                    <div class='metric-title-executive'>Costo Oportunidad Histórico (Holding)</div>
                    <div class='metric-value-executive'>S/. {total_holding_cost_historico:,.2f}</div>
                    <div class='metric-subtitle-executive'>Penalización financiera acumulada por tasa de <span class='highlight-blue'>{tasa_holding_anual*100:.1f}%</span>.</div>
                </div>
                """, unsafe_allow_html=True)
                
            with aud_col2:
                st.markdown(f"""
                <div class='metric-card-premium'>
                    <div class='metric-title-executive'>Costo Ocupación Física Total</div>
                    <div class='metric-value-executive'>S/. {total_arriendo_cost_historico:,.2f}</div>
                    <div class='metric-subtitle-executive'>Costo de m2 físico en base a la tasa de <span class='highlight-cyan'>S/. {costo_arriendo_m2_mes:.2f}/unidad</span>.</div>
                </div>
                """, unsafe_allow_html=True)
                
            with aud_col3:
                st.markdown(f"""
                <div class='metric-card-warning'>
                    <div class='metric-title-executive'>Costo Logístico Total Stock</div>
                    <div class='metric-value-executive'>S/. {total_logistico_financiero_historico:,.2f}</div>
                    <div class='metric-subtitle-executive'>Suma consolidada (Retención de capital + Almacenamiento).</div>
                </div>
                """, unsafe_allow_html=True)
                
            with aud_col4:
                # Fuga financiera por obsolescencia (Stock muerto en la muestra activa actual)
                perdida_holding_stock_muerto_anual = df_visualizacion_dashboard[df_visualizacion_dashboard['CRITICIDAD_LOGISTICA'].str.contains('🔴')]['COSTO_MANTENIMIENTO_ANUAL'].sum()
                st.markdown(f"""
                <div class='metric-card-alert'>
                    <div class='metric-title-executive'>Fuga Anual de Stock Muerto</div>
                    <div class='metric-value-executive'>S/. {perdida_holding_stock_muerto_anual:,.2f}</div>
                    <div class='metric-subtitle-executive'>Pérdida anual por mantener SKUs inmovilizados críticos.</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            
            # ---------------------------------------------------------------------
            # TRILOGÍA DE GRÁFICOS DE PASTEL PARA ALTA GERENCIA (ANÁLISIS DEL UNIVERSO DEL DINERO)
            # ---------------------------------------------------------------------
            st.markdown("### 🏢 Análisis de Estructura y Distribución del Capital Invertido")
            st.markdown("Sección diseñada para identificar de manera inmediata dónde se encuentra concentrado el dinero de la empresa y qué porcentaje de este representa un riesgo latente.")
            
            g_fin_col1, g_fin_col2, g_fin_col3 = st.columns(3)
            
            with g_fin_col1:
                st.markdown("#### 🥧 6. Composición del Universo de Inversión por Familia Logística (S/.)")
                # Agrupamos todo el dinero de la muestra actual abierta por familias logísticas
                df_pie_familia = df_visualizacion_dashboard.groupby('FAMILIA')['COSTO_TOTAL_INVENTARIO'].sum().reset_index()
                df_pie_familia = df_pie_familia[df_pie_familia['COSTO_TOTAL_INVENTARIO'] > 0].sort_values(by='COSTO_TOTAL_INVENTARIO', ascending=False)
                
                fig_pie_share = px.pie(
                    df_pie_familia, names='FAMILIA', values='COSTO_TOTAL_INVENTARIO',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                # MODIFICACIÓN: Se añade 'value' a textinfo y se define el formato con texttemplate
                fig_pie_share.update_traces(
                    textposition='inside', 
                    textinfo='percent+label+value',
                    texttemplate='%{label}<br>S/. %{value:,.2f}<br>%{percent}',
                    hovertemplate="<b>Familia Logística:</b> %{label}<br><b>Capital Invertido:</b> S/. %{value:,.2f}<br><b>% del Universo:</b> %{percent}"
                )
                fig_pie_share.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=False
                )
                st.plotly_chart(fig_pie_share, use_container_width=True)
                
            with g_fin_col2:
                st.markdown("#### 📊 6B. Distribución del Universo de Inversión por Rotación (ABC)")
                # Agrupamos todo el dinero de la muestra según su categoría de rotación
                df_pie_abc = df_visualizacion_dashboard.groupby('CATEGORIA_ABC')['COSTO_TOTAL_INVENTARIO'].sum().reset_index()
                df_pie_abc = df_pie_abc[df_pie_abc['COSTO_TOTAL_INVENTARIO'] > 0].sort_values(by='COSTO_TOTAL_INVENTARIO', ascending=False)
                
                fig_pie_abc = px.pie(
                    df_pie_abc, names='CATEGORIA_ABC', values='COSTO_TOTAL_INVENTARIO',
                    hole=0.4,
                    color='CATEGORIA_ABC',
                    color_discrete_map={
                        'A (Alta Rotación)': '#00ebc7', 
                        'B (Media Rotación)': '#fecb52', 
                        'C (Baja Rotación)': '#ff9900',
                        'Sin Rotación': '#ef553b'
                    }
                )
                # MODIFICACIÓN: Se añade 'value' a textinfo y se define el formato con texttemplate
                fig_pie_abc.update_traces(
                    textposition='inside', 
                    textinfo='percent+label+value',
                    texttemplate='%{label}<br>S/. %{value:,.2f}<br>%{percent}',
                    hovertemplate="<b>Segmentación ABC:</b> %{label}<br><b>Capital Atado:</b> S/. %{value:,.2f}<br><b>% del Universo:</b> %{percent}"
                )
                fig_pie_abc.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=False
                )
                st.plotly_chart(fig_pie_abc, use_container_width=True)

            with g_fin_col3:
                st.markdown("#### 🚨 6C. Mapeo Exclusivo de Capital Inmovilizado (Stock Muerto) por Familia")
                df_inmovilizado_pie = df_visualizacion_dashboard[df_visualizacion_dashboard['CRITICIDAD_LOGISTICA'].str.contains('🔴')].copy()
                df_pie_inmovilizado_fam = df_inmovilizado_pie.groupby('FAMILIA')['COSTO_TOTAL_INVENTARIO'].sum().reset_index()
                
                if not df_pie_inmovilizado_fam.empty and df_pie_inmovilizado_fam['COSTO_TOTAL_INVENTARIO'].sum() > 0:
                    fig_pie_inmovilizado = px.pie(
                        df_pie_inmovilizado_fam, names='FAMILIA', values='COSTO_TOTAL_INVENTARIO',
                        hole=0.4, 
                        color_discrete_sequence=px.colors.sequential.Reds_r
                    )
                    # MODIFICACIÓN: Se añade 'value' a textinfo y se define el formato con texttemplate
                    fig_pie_inmovilizado.update_traces(
                        textposition='inside', 
                        textinfo='percent+label+value',
                        texttemplate='%{label}<br>S/. %{value:,.2f}<br>%{percent}',
                        hovertemplate="<b>Familia Afectada:</b> %{label}<br><b>Dinero Pérdida:</b> S/. %{value:,.2f}<br><b>% del Total Inmovilizado:</b> %{percent}"
                    )
                else:
                    fig_pie_inmovilizado = go.Figure()
                    fig_pie_inmovilizado.add_annotation(
                        text="Salud del Inventario Óptima:<br>No hay Stock Muerto Inmovilizado bajo este filtro", 
                        showarrow=False, 
                        font=dict(size=13, color="#00cc96")
                    )
                
                fig_pie_inmovilizado.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=False
                )
                st.plotly_chart(fig_pie_inmovilizado, use_container_width=True)
            
            # CONTINUACIÓN NATURAL DE LA SUITE ORIGINAL DE COSTOS MENSUALES
            st.markdown("#### 📊 7. Estructura Mensual del Costo Operacional (Holding vs. Storage)")
            df_g8_costos_comp = df_filtros_series_temporales.groupby('AÑO_MES')[['COSTO_RETENCION_HOLDING', 'COSTO_OCUPACION_ESPACIO']].sum().reset_index()
            
            fig_g8_composicion = go.Figure()
            fig_g8_composicion.add_trace(go.Bar(x=df_g8_costos_comp['AÑO_MES'], y=df_g8_costos_comp['COSTO_RETENCION_HOLDING'], name='Costo Inmovilización (Holding)', marker_color='#90e0ef'))
            fig_g8_composicion.add_trace(go.Bar(x=df_g8_costos_comp['AÑO_MES'], y=df_g8_costos_comp['COSTO_OCUPACION_ESPACIO'], name='Costo Físico Espacio (Storage)', marker_color='#0096c7'))
            fig_g8_composicion.update_layout(
                template="plotly_dark", 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                barmode='stack', 
                xaxis_title="Evolución Mensual", 
                yaxis_title="Costo Acumulado (S/.)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_g8_composicion, use_container_width=True)
            
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            
            # ---------------------------------------------------------------------
            # GRÁFICO 8: GRÁFICO DUAL EVOLUTIVO CANTIDADES VS COSTO POR AÑO/MES
            # ---------------------------------------------------------------------
            st.markdown("#### 📈 8. Matriz Dual Histórica: Volumen de Unidades vs. Valorización de Inventario (S/.)")
            df_dual_mes = df_filtros_series_temporales.groupby('AÑO_MES')[['STOCK_FINAL', 'VALORIZACION_CIERRE']].sum().reset_index()
            
            fig_dual_axis = go.Figure()
            fig_dual_axis.add_trace(go.Bar(
                x=df_dual_mes['AÑO_MES'], y=df_dual_mes['STOCK_FINAL'],
                name='Volumen Stock (Unidades)',
                marker_color='#2a9d8f',
                opacity=0.6,
                yaxis='y1'
            ))
            fig_dual_axis.add_trace(go.Scatter(
                x=df_dual_mes['AÑO_MES'], y=df_dual_mes['VALORIZACION_CIERRE'],
                name='Valorización Cierre (S/.)',
                mode='lines+markers',
                line=dict(color='#e76f51', width=4),
                marker=dict(size=8),
                yaxis='y2'
            ))
            
            fig_dual_axis.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Evolución Temporal por Periodo",
                yaxis=dict(
                    title=dict(text="Volumen Físico (Unidades)", font=dict(color="#2a9d8f")),
                    tickfont=dict(color="#2a9d8f")
                ),
                yaxis2=dict(
                    title=dict(text="Valor Monetario del Inventario (S/.)", font=dict(color="#e76f51")),
                    tickfont=dict(color="#e76f51"),
                    overlaying='y',
                    side='right',
                    tickprefix="S/. "
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )
            st.plotly_chart(fig_dual_axis, use_container_width=True)
            
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            
            # ---------------------------------------------------------------------
            # GRÁFICO 9: CAPITAL DE TRABAJO EN EL TIEMPO
            # ---------------------------------------------------------------------
            st.markdown("#### 💸 9. Evolución del Capital de Trabajo Neto Inmovilizado al Cierre de Mes")
            df_g7_valorizacion_mes = df_filtros_series_temporales.groupby('AÑO_MES')['VALORIZACION_CIERRE'].sum().reset_index()
            
            fig_g7_valor_monetario = px.area(
                df_g7_valorizacion_mes, x='AÑO_MES', y='VALORIZACION_CIERRE',
                title=f"Tendencia Acumulada del Capital Financiero Inmovilizado (Muestra: {skus_en_series_temporales} SKUs)",
                labels={'VALORIZACION_CIERRE': 'Valorización de Cierre (S/.)', 'AÑO_MES': 'Periodo Mensual'},
                line_shape='spline'
            )
            fig_g7_valor_monetario.update_traces(line_color='#3b82f6', fillcolor='rgba(59, 130, 246, 0.25)')
            fig_g7_valor_monetario.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_g7_valor_monetario, use_container_width=True)
            
            # Panel de Mitigación Estratégica Inmediata
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            st.markdown("#### 🚨 Auditoría de Plan de Acción Contable sobre Muestra Actual")
            df_inspeccion_mitigacion = df_visualizacion_dashboard[df_visualizacion_dashboard['STOCK'] > 0][
                ['CODIGO', 'DESCRIPCIÓN', 'STOCK', 'COSTO', 'COSTO_TOTAL_INVENTARIO', 'RANGO_AGING', 'CATEGORIA_ABC', 'CRITICIDAD_LOGISTICA', 'ACCION_MITIGACION_SUGERIDA']
            ].sort_values(by='COSTO_TOTAL_INVENTARIO', ascending=False)
            st.dataframe(df_inspeccion_mitigacion, use_container_width=True)

        # =========================================================================
        # 10. PESTAÑA 3: DATA WAREHOUSE INTEGRAL PARA EXPORTACIÓN A POWER BI
        # =========================================================================
        with tab_data_pbi:
            st.subheader("📥 Data Warehouse Corporativo — Orígenes de Datos Limgios")
            st.markdown("Modelos de datos normalizados para inyección directa en Power BI.")
            
            reporte_solicitado = st.selectbox(
                "Seleccione el Modelo de Datos a Exportar:",
                [
                    "1. Reporte Maestro de Antigüedad, Costos y Acciones de Mitigación",
                    "2. Histórico de Cierres de Mes Indexado por SKU con Métricas de Costo",
                    "3. Matriz de Transacciones Mensual Balanceada (Para Gráficos Estadísticos / Waterfall)",
                    "4. Clasificación ABC de Rotación y Matriz de Criticidad Cruce",
                    "5. Módulo de Proyecciones de Escenarios de Consumo vs Inventario Base"
                ]
            )
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            if "1. Reporte Maestro de Antigüedad" in reporte_solicitado:
                st.dataframe(df_visualizacion_dashboard, use_container_width=True)
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer_engine:
                    df_visualizacion_dashboard.to_excel(writer_engine, index=False)
                st.download_button("📥 Descargar Fact_Aging_And_Costs.xlsx", data=output_excel.getvalue(), file_name="Fact_Aging_And_Costs.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            elif "2. Histórico de Cierres de Mes" in reporte_solicitado:
                df_cierres_exportar = df_historico_grande_maestro[df_historico_grande_maestro['STOCK_FINAL'] > 0][
                    ['AÑO_MES', 'CODIGO', 'DESCRIPCIÓN', 'FAMILIA', 'STOCK_FINAL', 'VALORIZACION_CIERRE', 'COSTO_RETENCION_HOLDING', 'COSTO_OCUPACION_ESPACIO', 'COSTO_LOGISTICO_TOTAL']
                ].rename(columns={'STOCK_FINAL': 'STOCK_CIERRE'})
                
                st.dataframe(df_cierres_exportar, use_container_width=True)
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer_engine:
                    df_cierres_exportar.to_excel(writer_engine, index=False)
                st.download_button("📥 Descargar Fact_Cierre_Mes_Costos.xlsx", data=output_excel.getvalue(), file_name="Fact_Cierre_Mes_Costos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            elif "3. Matriz de Transacciones" in reporte_solicitado:
                st.dataframe(df_historico_grande_maestro, use_container_width=True)
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer_engine:
                    df_historico_grande_maestro.to_excel(writer_engine, index=False)
                st.download_button("📥 Descargar Fact_Matriz_Waterfall_Completa.xlsx", data=output_excel.getvalue(), file_name="Fact_Matriz_Waterfall_Completa.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            elif "4. Clasificación ABC de Rotación" in reporte_solicitado:
                df_abc_export = df_visualizacion_dashboard[['CODIGO', 'DESCRIPCIÓN', 'FAMILIA', 'STOCK', 'COSTO', 'COSTO_TOTAL_INVENTARIO', 'CATEGORIA_ABC', 'CRITICIDAD_LOGISTICA']]
                st.dataframe(df_abc_export, use_container_width=True)
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer_engine:
                    df_abc_export.to_excel(writer_engine, index=False)
                st.download_button("📥 Descargar Dim_Productos_ABC_Costos.xlsx", data=output_excel.getvalue(), file_name="Dim_Productos_ABC_Costos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            elif "5. Módulo de Proyecciones" in reporte_solicitado:
                df_pivot_mensual_prod = df_notas_salida.groupby(['CODIGO', 'AÑO_MES_PERIOD'])['CANTIDAD'].sum().unstack(fill_value=0.0)
                df_calculo_promedios_proy = df_pivot_mensual_prod.mean(axis=1).reset_index(name='CONSUMO_PROMEDIO_NORMAL')
                
                df_calculo_promedios_proy['CONSUMO_ESCENARIO_25%'] = (df_calculo_promedios_proy['CONSUMO_PROMEDIO_NORMAL'] * 1.25).round(2)
                df_calculo_promedios_proy['CONSUMO_ESCENARIO_35%'] = (df_calculo_promedios_proy['CONSUMO_PROMEDIO_NORMAL'] * 1.35).round(2)
                
                meses_futuros_proyeccion = ['Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                registros_proyecciones_long = []
                
                for index, row_data in df_calculo_promedios_proy.iterrows():
                    sku_code = row_data['CODIGO']
                    costo_u = maestro_articulos_dict.loc[sku_code, 'COSTO'] if sku_code in maestro_articulos_dict.index else 0.0
                    for nombre_mes in meses_futuros_proyeccion:
                        c_normal = row_data['CONSUMO_PROMEDIO_NORMAL']
                        c_25 = row_data['CONSUMO_ESCENARIO_25%']
                        c_35 = row_data['CONSUMO_ESCENARIO_35%']
                        
                        registros_proyecciones_long.append({
                            'CODIGO': sku_code,
                            'MES_PROYECCION': nombre_mes,
                            'CONSUMO_NORMAL': round(c_normal, 2),
                            'VALORIZACION_PROY_NORMAL': round(c_normal * costo_u, 2),
                            'CONSUMO_MAS_25': round(c_25, 2),
                            'VALORIZACION_PROY_25': round(c_25 * costo_u, 2),
                            'CONSUMO_MAS_35': round(c_35, 2),
                            'VALORIZACION_PROY_35': round(c_35 * costo_u, 2)
                        })
                        
                df_tabla_proyecciones_final = pd.DataFrame(registros_proyecciones_long)
                
                col_split_b1, col_split_b2 = st.columns(2)
                with col_split_b1:
                    st.markdown("**Tabla 1: Inventario Base Actual Valorizado (S/.)**")
                    df_base_v = df_stock_clean[['CODIGO', 'DESCRIPCIÓN', 'FAMILIA', 'STOCK', 'COSTO']]
                    df_base_v['TOTAL_VALORIZADO'] = df_base_v['STOCK'] * df_base_v['COSTO']
                    st.dataframe(df_base_v, use_container_width=True)
                    out_b1 = io.BytesIO()
                    with pd.ExcelWriter(out_b1, engine='openpyxl') as w_b1:
                        df_base_v.to_excel(w_b1, index=False)
                    st.download_button("📥 Descargar Archivo 1: Stock Base Valorizado", data=out_b1.getvalue(), file_name="Dim_Stock_Base_Actual_Valorizado.xlsx")
                    
                with col_split_b2:
                    st.markdown("**Tabla 2: Escenarios de Consumo Proyectados Financieros (S/.)**")
                    st.dataframe(df_tabla_proyecciones_final, use_container_width=True)
                    out_b2 = io.BytesIO()
                    with pd.ExcelWriter(out_b2, engine='openpyxl') as w_b2:
                        df_tabla_proyecciones_final.to_excel(w_b2, index=False)
                    st.download_button("📥 Descargar Archivo 2: Costos Consumos Proyectados", data=out_b2.getvalue(), file_name="Fact_Consumos_Proyectados_Financieros.xlsx")

    except Exception as error_global_sistema:
        st.error(f"❌ Error crítico detectado en el núcleo de procesamiento macro-logístico: {str(error_global_sistema)}")
else:
    st.info("💡 Suite Ares v11.2 en Espera de Archivos. Cargue el Historial de Movimientos Contables (Kardex) y el Maestro de Stock Actual con Costos para desplegar los análisis financieros.")
