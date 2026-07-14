import streamlit as st
import pandas as pd

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

st.title("Sistema de Control de Inventarios")
st.write("Carga centralizada de datos para auditoría patrimonial y flujos financieros.")

st.markdown("---")

col_a, col_b = st.columns(2)
with col_a:
    archivo_stock = st.file_uploader("Cargar Reporte Masivo de Stock Actual (.xlsx)", type=["xlsx"])
with col_b:
    archivo_mov = st.file_uploader("Cargar Kardex Completo de Movimientos Históricos (.xlsx)", type=["xlsx"])

@st.cache_data
def inicializar_pipeline(file_stock, file_mov):
    df_stock = pd.read_excel(file_stock)
    df_mov = pd.read_excel(file_mov)
    
    # Limpieza corporativa estricta e indexación de SubFamilia
    df_stock['Codigo'] = df_stock['Codigo'].astype(str).str.strip().str.upper()
    df_stock['Almacen'] = df_stock['Almacen'].astype(str).str.strip()
    df_stock['Familia'] = df_stock['Familia'].fillna('SIN CLASIFICAR').astype(str).str.strip().str.upper()
    df_stock['SubFamilia'] = df_stock['SubFamilia'].fillna('GENERAL').astype(str).str.strip().str.upper()
    df_stock['Valor_Total'] = df_stock['Stock'] * df_stock['Costo']
    
    df_mov['Codigo'] = df_mov['Codigo'].astype(str).str.strip().str.upper()
    df_mov['Almacen'] = df_mov['Almacen'].astype(str).str.strip()
    df_mov['Fecha'] = pd.to_datetime(df_mov['Fecha'])
    df_mov['Mes_Mov'] = df_mov['Fecha'].dt.to_period('M').astype(str)
    
    return df_stock, df_mov

if archivo_stock and archivo_mov:
    df_s, df_m = inicializar_pipeline(archivo_stock, archivo_mov)
    st.session_state['df_stock'] = df_s
    st.session_state['df_mov'] = df_m
    st.success("Bases de datos consolidadas en memoria. Proceda a utilizar los módulos financieros del panel lateral.")
else:
    st.info("A la espera de reportes de origen para inicializar la sesión analítica.")