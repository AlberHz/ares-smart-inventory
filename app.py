import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(
    page_title="Ares Peru SAC",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 700; color: #0f172a; letter-spacing: -0.025em; }
    .stMetric { background-color: #f8fafc; padding: 1.5rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; }
    div[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 700 !important; color: #1e3a8a; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard (KPIS) de los Almacenes de Materia Prima y Suministros")
st.markdown("---")

col_a, col_b = st.columns(2)
with col_a:
    archivo_stock = st.file_uploader("Cargar archivo excel del Stock Actual (.xlsx)", type=["xlsx"])
with col_b:
    archivo_mov = st.file_uploader("Cargar archivo excel de todos los Movimientos de todos los almacenes (.xlsx)", type=["xlsx"])

def limpiar_cabecera(texto):
    """Elimina tildes, caracteres especiales, espacios extras y convierte a mayúsculas"""
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto

def normalizar_df(df):
    """Limpia los nombres de las columnas para evitar errores de tildes como DESCRIPCIÓN -> DESCRIPCION"""
    df.columns = [limpiar_cabecera(c) for c in df.columns]
    return df

def leer_y_unir_hojas(file):
    """Lee todas las pestañas del Excel, normaliza encabezados y asigna el almacén automáticamente si falta"""
    dict_hojas = pd.read_excel(file, sheet_name=None)
    lista_dfs = []
    
    for nombre_hoja, df in dict_hojas.items():
        if df.empty:
            continue
        df = df.copy()
        df = normalizar_df(df)
        
        # Si la hoja no tiene columna ALMACEN, usa el nombre de la pestaña
        if 'ALMACEN' not in df.columns:
            almacen_nombre = limpiar_cabecera(nombre_hoja).replace('MOV_', '').replace('MOVIMIENTO_', '').replace('_', ' ')
            df['ALMACEN'] = almacen_nombre
            
        lista_dfs.append(df)
        
    return pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()

@st.cache_data
def inicializar_pipeline(file_stock, file_mov):
    # Consolida todas las pestañas
    df_stock = leer_y_unir_hojas(file_stock)
    df_mov = leer_y_unir_hojas(file_mov)
    
    # --------------------------------------------------------------------------
    # 1. TRATAMIENTO PARA STOCK
    # --------------------------------------------------------------------------
    # Mapeo flexible de columnas para evitar KeyErrors
    df_stock['CODIGO'] = df_stock['CODIGO'].astype(str).str.strip().str.upper() if 'CODIGO' in df_stock.columns else 'SIN CODIGO'
    df_stock['ALMACEN'] = df_stock['ALMACEN'].astype(str).str.strip().str.upper() if 'ALMACEN' in df_stock.columns else 'GENERAL'
    
    if 'FAMILIA' in df_stock.columns:
        df_stock['FAMILIA'] = df_stock['FAMILIA'].fillna('SIN CLASIFICAR').astype(str).str.strip().str.upper()
    else:
        df_stock['FAMILIA'] = 'SIN CLASIFICAR'

    # Auto-detección de DESCRIPCION (soporta DESCRIPCION, DESCRIPCIÓN, MATERIAL, PRODUCTO)
    if 'DESCRIPCION' not in df_stock.columns:
        cols_similares = [c for c in df_stock.columns if 'DESC' in c or 'MAT' in c or 'PROD' in c]
        if cols_similares:
            df_stock['DESCRIPCION'] = df_stock[cols_similares[0]].astype(str).str.strip()
        else:
            df_stock['DESCRIPCION'] = 'SIN DESCRIPCION'
    else:
        df_stock['DESCRIPCION'] = df_stock['DESCRIPCION'].astype(str).str.strip()

    df_stock['STOCK'] = pd.to_numeric(df_stock['STOCK'] if 'STOCK' in df_stock.columns else 0, errors='coerce').fillna(0.0)
    df_stock['COSTO'] = pd.to_numeric(df_stock['COSTO'] if 'COSTO' in df_stock.columns else 0, errors='coerce').fillna(0.0)
    df_stock['Valor_Total'] = df_stock['STOCK'] * df_stock['COSTO']
    
    # --------------------------------------------------------------------------
    # 2. TRATAMIENTO PARA MOVIMIENTOS
    # --------------------------------------------------------------------------
    df_mov['CODIGO'] = df_mov['CODIGO'].astype(str).str.strip().str.upper() if 'CODIGO' in df_mov.columns else 'SIN CODIGO'
    df_mov['ALMACEN'] = df_mov['ALMACEN'].astype(str).str.strip().str.upper() if 'ALMACEN' in df_mov.columns else 'GENERAL'
    
    # Mapeo flexible de Tipo de Movimiento
    cols_tipo = [c for c in df_mov.columns if 'TIPO' in c or 'MOV' in c]
    if cols_tipo:
        df_mov['TIPO_MOVIMIENTO'] = df_mov[cols_tipo[0]].astype(str).str.strip().str.upper()
    else:
        df_mov['TIPO_MOVIMIENTO'] = ''
        
    # Mapeo flexible de Cantidad
    cols_cant = [c for c in df_mov.columns if 'CANT' in c]
    if cols_cant:
        df_mov['CANTIDAD'] = pd.to_numeric(df_mov[cols_cant[0]], errors='coerce').fillna(0.0).abs()
    else:
        df_mov['CANTIDAD'] = 0.0
    
    # Manejo de fechas
    cols_fecha = [c for c in df_mov.columns if 'FEC' in c or 'DATE' in c]
    if cols_fecha:
        df_mov['FECHA'] = pd.to_datetime(df_mov[cols_fecha[0]], dayfirst=True, errors='coerce')
    else:
        df_mov['FECHA'] = pd.NaT
        
    df_mov['Mes_Mov'] = df_mov['FECHA'].dt.to_period('M').astype(str)
    
    return df_stock, df_mov

if archivo_stock and archivo_mov:
    df_s, df_m = inicializar_pipeline(archivo_stock, archivo_mov)
    st.session_state['df_stock'] = df_s
    st.session_state['df_mov'] = df_m
    st.success("Bases de datos consolidadas en memoria exitosamente desde todas las pestañas. Proceda a utilizar los módulos financieros del panel lateral.")
else:
    st.info("A la espera de reportes de origen para inicializar la sesión analítica.")