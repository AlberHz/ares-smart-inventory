import streamlit as st
import pandas as pd
import numpy as np
import datetime
import unicodedata
import io

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
        HRFlowable, PageBreak, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS UI/UX
# ==============================================================================
st.set_page_config(
    layout="wide", 
    page_title="INFORME DE KPIS",
    page_icon="📊"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0f172a;
    }
    .kpi-sub {
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 4px;
    }
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 25px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

if 'df_stock' not in st.session_state or 'df_mov' not in st.session_state:
    st.warning("⚠️ Debe cargar los datos de origen (Stock y Movimientos) en la pantalla de inicio.")
    st.stop()

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

COLOR_ACTIVO = '#10b981'
COLOR_MEDIO = '#f59e0b'
COLOR_BAJO = '#f97316'
COLOR_CRITICO = '#b91c1c'

def desacentuar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")

def obtener_colormap(nombre):
    try:
        return plt.colormaps.get_cmap(nombre)
    except AttributeError:
        return plt.cm.get_cmap(nombre)

def sanitizar_numerico(serie):
    if serie is None or serie.empty: 
        return pd.Series(dtype=float)
    return (
        serie.astype(str)
        .str.replace('S/.', '', regex=False)
        .str.replace('S/', '', regex=False)
        .str.replace('$', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0.0)
    )

# ==============================================================================
# PIPELINE Y PROCESAMIENTO GERENCIAL
# ==============================================================================
@st.cache_data(show_spinner="Sincronizando métricas gerenciales...")
def procesar_datos_gerenciales(df_stock_raw, df_mov_raw, df_eri_raw=None):
    df_stock_clean = df_stock_raw.copy()
    df_mov_clean = df_mov_raw.copy()
    
    df_stock_clean.columns = [desacentuar_texto(c) for c in df_stock_clean.columns]
    df_mov_clean.columns = [desacentuar_texto(c) for c in df_mov_clean.columns]

    # Estructura del Stock
    df_s = pd.DataFrame()
    df_s['Codigo'] = df_stock_clean['CODIGO'].astype(str).str.strip().str.upper() if 'CODIGO' in df_stock_clean.columns else 'SIN CODIGO'
    
    if 'DESCRIPCION' in df_stock_clean.columns:
        df_s['Descripcion'] = df_stock_clean['DESCRIPCION'].astype(str).str.strip()
    else:
        cols_desc = [c for c in df_stock_clean.columns if 'DESC' in c or 'MAT' in c or 'PROD' in c]
        df_s['Descripcion'] = df_stock_clean[cols_desc[0]].astype(str).str.strip() if cols_desc else 'SIN DESCRIPCION'

    df_s['Almacen'] = df_stock_clean['ALMACEN'].astype(str).str.strip().str.upper() if 'ALMACEN' in df_stock_clean.columns else 'GENERAL'
    df_s['Familia'] = df_stock_clean['FAMILIA'].astype(str).str.strip().str.upper() if 'FAMILIA' in df_stock_clean.columns else 'SIN CLASIFICAR'
    df_s['SubFamilia'] = df_stock_clean['SUBFAMILIA'].astype(str).str.strip().str.upper() if 'SUBFAMILIA' in df_stock_clean.columns else 'GENERAL'
    
    df_s['Stock'] = sanitizar_numerico(df_stock_clean['STOCK'] if 'STOCK' in df_stock_clean.columns else pd.Series(0, index=df_stock_clean.index))
    df_s['Costo'] = sanitizar_numerico(df_stock_clean['COSTO'] if 'COSTO' in df_stock_clean.columns else pd.Series(0, index=df_stock_clean.index))

    df_s = df_s[df_s['Stock'] > 0].copy().reset_index(drop=True)
    df_s['Valor_Total'] = df_s['Stock'] * df_s['Costo']

    # Estructura de Movimientos
    df_m = pd.DataFrame()
    df_m['Codigo'] = df_mov_clean['CODIGO'].astype(str).str.strip().str.upper() if 'CODIGO' in df_mov_clean.columns else 'SIN CODIGO'
    df_m['Almacen'] = df_mov_clean['ALMACEN'].astype(str).str.strip().str.upper() if 'ALMACEN' in df_mov_clean.columns else 'GENERAL'
    
    cols_tipo = [c for c in df_mov_clean.columns if 'TIPO' in c or 'MOV' in c]
    df_m['Tipo_Movimiento'] = df_mov_clean[cols_tipo[0]].astype(str).str.strip().str.upper() if cols_tipo else ''
    
    cols_cant = [c for c in df_mov_clean.columns if 'CANT' in c]
    df_m['Cantidad'] = sanitizar_numerico(df_mov_clean[cols_cant[0]] if cols_cant else pd.Series(0, index=df_mov_clean.index))

    cols_fecha = [c for c in df_mov_clean.columns if 'FEC' in c or 'DATE' in c]
    if cols_fecha:
        df_m['Fecha'] = pd.to_datetime(df_mov_clean[cols_fecha[0]], dayfirst=True, errors='coerce')
        df_m['Mes_Mov'] = df_m['Fecha'].dt.strftime('%Y-%m')
    else:
        df_m['Fecha'] = pd.NaT
        df_m['Mes_Mov'] = '2026-08'

    df_m['Entradas'] = np.where(df_m['Tipo_Movimiento'].str.contains('NI|INGRESO', regex=True, na=False), df_m['Cantidad'], 0.0)
    df_m['Salidas'] = np.where(df_m['Tipo_Movimiento'].str.contains('NS|SALIDA|CONSUMO', regex=True, na=False), df_m['Cantidad'], 0.0)

    # Agrupación y Clasificación ABC por Frecuencia de Salidas
    df_ns = df_m[df_m['Salidas'] > 0]
    conteo_frecuencia = df_ns.groupby(['Codigo', 'Almacen']).size().reset_index(name='Volumen_Pedidos')

    df_s = df_s.merge(conteo_frecuencia, on=['Codigo', 'Almacen'], how='left')
    df_s['Volumen_Pedidos'] = df_s['Volumen_Pedidos'].fillna(0).astype(int)

    df_s = df_s.sort_values(by=['Volumen_Pedidos', 'Valor_Total'], ascending=[False, False]).reset_index(drop=True)
    total_pedidos_global = df_s['Volumen_Pedidos'].sum()

    if total_pedidos_global > 0:
        df_s['Pct_Pedidos'] = (df_s['Volumen_Pedidos'] / total_pedidos_global * 100.0)
        df_s['Pedidos_Acum_Pct'] = (df_s['Volumen_Pedidos'].cumsum() / total_pedidos_global * 100.0)

        df_s['Clase_ABC'] = np.select(
            [
                df_s['Pedidos_Acum_Pct'] <= 80.001,
                (df_s['Pedidos_Acum_Pct'] > 80.001) & (df_s['Pedidos_Acum_Pct'] <= 95.001)
            ],
            ['A', 'B'],
            default='C'
        )
    else:
        df_s['Pct_Pedidos'] = 0.0
        df_s['Pedidos_Acum_Pct'] = 0.0
        df_s['Clase_ABC'] = 'C'

    # Evolutivo Histórico por Almacén
    meses_historicos = sorted([m_h for m_h in df_m['Mes_Mov'].dropna().astype(str).unique().tolist() if m_h.lower() != 'nan'])
    costo_map = df_s.groupby('Codigo')['Costo'].mean().to_dict()
    stock_actual_agrupado = df_s.groupby(['Codigo', 'Almacen'])['Stock'].sum().to_dict()

    pivot_movs = df_m.groupby(['Mes_Mov', 'Codigo', 'Almacen'])[['Entradas', 'Salidas']].sum().reset_index()
    entradas_p = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Entradas', aggfunc='sum').fillna(0)
    salidas_p = pivot_movs.pivot_table(index=['Codigo', 'Almacen'], columns='Mes_Mov', values='Salidas', aggfunc='sum').fillna(0)

    for mes_h in meses_historicos:
        if mes_h not in entradas_p.columns: entradas_p[mes_h] = 0.0
        if mes_h not in salidas_p.columns: salidas_p[mes_h] = 0.0

    combinaciones_maestro = df_s.groupby(['Codigo', 'Almacen']).size().index
    evol_almacen = []

    for mes_h in meses_historicos:
        meses_futuros = [m_f for m_f in meses_historicos if m_f > mes_h]
        ef_totales = entradas_p[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}
        sf_totales = salidas_p[meses_futuros].sum(axis=1).to_dict() if meses_futuros else {}

        capital_por_almacen = {}
        for sku, alm in combinaciones_maestro:
            stk_act = stock_actual_agrupado.get((sku, alm), 0.0)
            ef = ef_totales.get((sku, alm), 0.0)
            sf = sf_totales.get((sku, alm), 0.0)
            stk_mes_alm = max(0.0, stk_act - ef + sf)

            costo = costo_map.get(sku, 0.0)
            capital_por_almacen[alm] = capital_por_almacen.get(alm, 0.0) + stk_mes_alm * costo

        for alm, cap in capital_por_almacen.items():
            evol_almacen.append({'Mes': mes_h, 'Almacen': alm, 'Capital': cap})

    df_evol = pd.DataFrame(evol_almacen)

    # Lógica de Inmovilizados
    fecha_hoy = pd.Timestamp(datetime.date.today())
    m_valid = df_m[df_m['Fecha'].notnull()].copy()

    if m_valid.empty:
        df_s['f_ult_salida'] = pd.NaT
        df_s['dias_inactivo_hoy'] = 999.0
    else:
        s_salidas = m_valid[m_valid['Salidas'] > 0].groupby('Codigo')['Fecha'].max()
        df_s['f_ult_salida'] = df_s['Codigo'].map(s_salidas)
        dias_inact = (fecha_hoy - df_s['f_ult_salida']).dt.days
        df_s['dias_inactivo_hoy'] = dias_inact.fillna(999)

    conds_inmov = [
        df_s['dias_inactivo_hoy'] < 90,
        (df_s['dias_inactivo_hoy'] >= 90) & (df_s['dias_inactivo_hoy'] < 180),
        (df_s['dias_inactivo_hoy'] >= 180) & (df_s['dias_inactivo_hoy'] < 270)
    ]
    choices_inmov = [
        '1 a 3 Meses (Rotación Activa)',
        '3 a 6 Meses (Rotación Media)',
        '6 a 9 Meses (Rotación Baja / Riesgo)'
    ]
    df_s['Tramo_Inmovilizado'] = np.select(conds_inmov, choices_inmov, default='9 a Más Meses (Inmovilizado Crítico)')
    df_s['Capital_Total'] = df_s['Stock'] * df_s['Costo']

    # Métricas Globales
    total_capital = df_s['Capital_Total'].sum()
    total_unidades = df_s['Stock'].sum()
    total_skus = df_s['Codigo'].nunique()

    monto_activa = df_s[df_s['Tramo_Inmovilizado'] == '1 a 3 Meses (Rotación Activa)']['Capital_Total'].sum()
    monto_media = df_s[df_s['Tramo_Inmovilizado'] == '3 a 6 Meses (Rotación Media)']['Capital_Total'].sum()
    monto_riesgo = df_s[df_s['Tramo_Inmovilizado'] == '6 a 9 Meses (Rotación Baja / Riesgo)']['Capital_Total'].sum()
    monto_critico = df_s[df_s['Tramo_Inmovilizado'] == '9 a Más Meses (Inmovilizado Crítico)']['Capital_Total'].sum()

    res_alm = (
        df_s.groupby('Almacen')
        .agg(Capital=('Capital_Total', 'sum'), SKUs=('Codigo', 'nunique'), Stock_Unidades=('Stock', 'sum'))
        .reset_index()
    )
    res_alm['Pct_Capital'] = (res_alm['Capital'] / total_capital * 100.0 if total_capital > 0 else 0.0)
    res_alm = res_alm.sort_values('Capital', ascending=False)

    res_abc_alm = (
        df_s.groupby(['Almacen', 'Clase_ABC'])
        .agg(SKUs=('Codigo', 'nunique'), Capital=('Capital_Total', 'sum'), Pedidos=('Volumen_Pedidos', 'sum'))
        .reset_index()
    )

    res_pareto_operativo = (
        df_s.groupby('Clase_ABC')
        .agg(SKUs=('Codigo', 'nunique'), Pedidos=('Volumen_Pedidos', 'sum'), Valorizacion=('Capital_Total', 'sum'))
        .reindex(['A', 'B', 'C'], fill_value=0)
        .reset_index()
    )

    tot_skus_gen = res_pareto_operativo['SKUs'].sum()
    tot_ped_gen = res_pareto_operativo['Pedidos'].sum()

    res_pareto_operativo['Pct_SKUs'] = (res_pareto_operativo['SKUs'] / tot_skus_gen * 100.0 if tot_skus_gen > 0 else 0.0)
    res_pareto_operativo['Pct_Frecuencia'] = (res_pareto_operativo['Pedidos'] / tot_ped_gen * 100.0 if tot_ped_gen > 0 else 0.0)

    res_inmov_alm = (
        df_s[df_s['Stock'] > 0]
        .groupby(['Almacen', 'Tramo_Inmovilizado'])
        .agg(Capital=('Capital_Total', 'sum'), SKUs=('Codigo', 'nunique'))
        .reset_index()
    )

    res_inmov_fam = (
        df_s[df_s['Stock'] > 0]
        .groupby(['Familia', 'Tramo_Inmovilizado'])
        .agg(Capital=('Capital_Total', 'sum'), SKUs=('Codigo', 'nunique'))
        .reset_index()
    )

    top30_skus = df_s[df_s['Stock'] > 0].sort_values('Capital_Total', ascending=False).head(30)
    top30_inmov = df_s[(df_s['Stock'] > 0) & (df_s['Tramo_Inmovilizado'] == '9 a Más Meses (Inmovilizado Crítico)')].sort_values('Capital_Total', ascending=False).head(30)

    # Indicador ERI
    if df_eri_raw is not None and not df_eri_raw.empty:
        df_e = df_eri_raw.copy()
        df_e.columns = [desacentuar_texto(c) for c in df_e.columns]
        
        if 'ALMACEN' in df_e.columns:
            df_e = df_e[~df_e['ALMACEN'].astype(str).str.upper().isin(['OBSERVADOS', 'DESINVENTARIO', 'MUESTRAS'])]
        df_e['ES_EXACTO'] = ((df_e['DIFERENCIA'] == 0).astype(int) if 'DIFERENCIA' in df_e.columns else 1)

        if 'MES_MOV' in df_e.columns:
            df_eri_hist = df_e.groupby('MES_MOV').agg(Total=('ES_EXACTO', 'count'), Exactos=('ES_EXACTO', 'sum')).reset_index()
            df_eri_hist['ERI'] = (df_eri_hist['Exactos'] / df_eri_hist['Total'] * 100.0)
            df_eri_hist.rename(columns={'MES_MOV': 'Mes'}, inplace=True)
            df_eri_hist = df_eri_hist.sort_values('Mes')
        else:
            df_eri_hist = pd.DataFrame({'Mes': meses_historicos, 'ERI': [98.0] * len(meses_historicos)})

        if 'ALMACEN' in df_e.columns:
            df_eri_alm = df_e.groupby('ALMACEN').agg(Total=('ES_EXACTO', 'count'), Exactos=('ES_EXACTO', 'sum')).reset_index()
            df_eri_alm['ERI'] = (df_eri_alm['Exactos'] / df_eri_alm['Total'] * 100.0)
            df_eri_alm.rename(columns={'ALMACEN': 'Almacen'}, inplace=True)
        else:
            df_eri_alm = pd.DataFrame({'Almacen': res_alm['Almacen'].tolist(), 'ERI': [98.0] * len(res_alm)})
    else:
        df_eri_hist = pd.DataFrame({'Mes': meses_historicos, 'ERI': [98.0] * len(meses_historicos)})
        df_eri_alm = pd.DataFrame({'Almacen': res_alm['Almacen'].tolist(), 'ERI': [98.0] * len(res_alm)})

    return {
        'df_s': df_s,
        'total_capital': total_capital,
        'total_unidades': total_unidades,
        'total_skus': total_skus,
        'monto_activa': monto_activa,
        'monto_media': monto_media,
        'monto_riesgo': monto_riesgo,
        'monto_critico': monto_critico,
        'res_alm': res_alm,
        'res_abc_alm': res_abc_alm,
        'res_pareto_operativo': res_pareto_operativo,
        'df_evol': df_evol,
        'res_inmov_alm': res_inmov_alm,
        'res_inmov_fam': res_inmov_fam,
        'top30_skus': top30_skus,
        'top30_inmov': top30_inmov,
        'df_eri_hist': df_eri_hist,
        'df_eri_alm': df_eri_alm
    }

df_eri_sesion = st.session_state.get('df_eri_base', st.session_state.get('df_eri', None))
m = procesar_datos_gerenciales(st.session_state['df_stock'], st.session_state['df_mov'], df_eri_sesion)

# ==============================================================================
# FUNCIONES DE GENERACIÓN DE GRÁFICOS
# ==============================================================================
def generar_grafico_evolucion_global(df_evol):
    fig, ax = plt.subplots(figsize=(8.5, 2.3), dpi=250)
    df_tot = df_evol.groupby('Mes')['Capital'].sum().reset_index().sort_values('Mes')
    ax.plot(df_tot['Mes'], df_tot['Capital'] / 1e6, marker='o', linestyle='-', linewidth=2, markersize=4.5, color='#0d9488')
    for _, r in df_tot.iterrows():
        v = r['Capital'] / 1e6
        ax.annotate(f"S/. {v:.2f}M", (r['Mes'], v), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=6, fontweight='bold', color='#0f172a')
    ax.set_title("VALORIZACIÓN DEL INVENTARIO MES A MES", fontsize=8, fontweight='bold', pad=8, color='#0f172a')
    ax.set_ylabel("Capital (S/. M)", fontsize=6.5, fontweight='bold')
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('S/. %.1fM'))
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='x', rotation=30, labelsize=5.5)
    ax.tick_params(axis='y', labelsize=5.5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generar_grafico_almacen_individual(df_evol, nombre_almacen):
    fig, ax = plt.subplots(figsize=(8.5, 2.1), dpi=250)
    sub = df_evol[df_evol['Almacen'] == nombre_almacen].sort_values('Mes')
    colores_map = {'MATERIA PRIMA': '#0284c7', 'SUMINISTROS': '#ec4899', 'OBSERVADOS': '#10b981', 'GENERAL': '#64748b'}
    c = colores_map.get(str(nombre_almacen), '#0d9488')
    ax.plot(sub['Mes'], sub['Capital'] / 1e6, marker='o', linestyle='-', linewidth=2, markersize=4.5, color=c)
    for _, r in sub.iterrows():
        v = r['Capital'] / 1e6
        lbl = f"S/. {v:.2f}M" if v >= 1.0 else f"S/. {r['Capital']/1e3:.0f}K"
        ax.annotate(lbl, (r['Mes'], v), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=6, fontweight='bold', color='#0f172a')
    ax.set_title(f"Evolución Mensual: {nombre_almacen}", fontsize=8, fontweight='bold', loc='left', color='#0f172a', pad=8)
    ax.set_ylabel("Capital (S/. M)", fontsize=6.5, fontweight='bold')
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('S/. %.2fM'))
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='x', rotation=30, labelsize=5.5)
    ax.tick_params(axis='y', labelsize=5.5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generar_graficos_eri_reestructurado(df_eri_hist, df_eri_alm, res_alm):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(8.5, 2.5), dpi=250, gridspec_kw={'width_ratios': [1.2, 1.0, 1.1]})
    ax1.plot(df_eri_hist['Mes'], df_eri_hist['ERI'], marker='o', color='#10b981', linewidth=1.8, markersize=4)
    ax1.axhline(98.0, color='#dc2626', linestyle='--', linewidth=1, label='Target (98%)')
    for _, r in df_eri_hist.iterrows():
        ax1.annotate(f"{r['ERI']:.1f}%", (r['Mes'], r['ERI']), textcoords="offset points", xytext=(0, 3), ha='center', fontsize=5, fontweight='bold')
    ax1.set_title("Evolución ERI", fontsize=7.5, fontweight='bold')
    ax1.set_ylim(0, 108)
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.tick_params(labelsize=5.5)
    ax1.tick_params(axis='x', rotation=30)

    bars2 = ax2.bar(df_eri_alm['Almacen'], df_eri_alm['ERI'], color=['#0284c7', '#ec4899', '#10b981'][:len(df_eri_alm)], width=0.45)
    for bar in bars2:
        h = bar.get_height()
        ax2.annotate(f"{h:.1f}%", (bar.get_x() + bar.get_width()/2, h), textcoords="offset points", xytext=(0,2), ha='center', fontsize=5.5, fontweight='bold')
    ax2.set_title("ERI por Almacén", fontsize=7.5, fontweight='bold')
    ax2.set_ylim(0, 108)
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.tick_params(labelsize=5.5)

    colores_pie = ['#0284c7', '#ec4899', '#10b981', '#f59e0b']
    ax3.pie(res_alm['Capital'], labels=res_alm['Almacen'], autopct='%1.1f%%', pctdistance=0.7, labeldistance=1.15, startangle=140, colors=colores_pie[:len(res_alm)], textprops=dict(fontsize=5, weight='bold'))
    ax3.add_artist(plt.Circle((0,0), 0.5, fc='white'))
    ax3.set_title("Porcentaje del Capital por Almacén", fontsize=7.5, fontweight='bold')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generar_grafico_top_skus_amplio_30(df_skus, titulo, color_map):
    fig, ax = plt.subplots(figsize=(8.5, 6.0), dpi=250)
    top_sorted = df_skus.sort_values(by='Capital_Total', ascending=True).tail(30)
    
    labels = []
    for _, r in top_sorted.iterrows():
        desc = str(r['Descripcion'])
        if len(desc) > 50: desc = desc[:47] + "..."
        labels.append(f"[{r['Codigo']}] {desc}")

    valores = top_sorted['Capital_Total'].to_numpy() / 1e3
    cmap = obtener_colormap(color_map)
    colors_bar = cmap(np.linspace(0.35, 0.9, len(valores)))
    bars = ax.barh(labels, valores, color=colors_bar, height=0.72)
    
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', color='#0f172a', pad=8)
    ax.set_xlabel("Valor Total (S/. K)", fontsize=6.5, fontweight='bold', color='#334155')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.tick_params(axis='both', which='major', labelsize=4.8)

    for bar in bars:
        w = bar.get_width()
        ax.annotate(f"S/. {w:.1f}K", (w, bar.get_y() + bar.get_height()/2),
                    xytext=(3, 0), textcoords="offset points", ha='left', va='center',
                    fontsize=4.5, fontweight='bold', color='#1e293b')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generar_grafico_abc_por_almacen(df_abc_alm):
    fig, ax = plt.subplots(figsize=(8.5, 2.95), dpi=250)

    if df_abc_alm.empty:
        ax.text(0.5, 0.5, "Sin datos ABC disponibles", ha='center', va='center')
        ax.axis('off')
    else:
        pivot_cap = (
            df_abc_alm.pivot_table(
                index='Almacen', columns='Clase_ABC',
                values='Capital', aggfunc='sum', fill_value=0
            ).reindex(columns=['A', 'B', 'C'], fill_value=0)
        )
        pivot_skus = (
            df_abc_alm.pivot_table(
                index='Almacen', columns='Clase_ABC',
                values='SKUs', aggfunc='sum', fill_value=0
            ).reindex(columns=['A', 'B', 'C'], fill_value=0)
        )

        almacenes = pivot_cap.index.tolist()
        x = np.arange(len(almacenes))
        width = 0.25
        colores_abc = {'A': '#ef4444', 'B': '#f59e0b', 'C': '#10b981'}

        for i, clase in enumerate(['A', 'B', 'C']):
            vals_cap = pivot_cap[clase].to_numpy()
            vals_skus = pivot_skus[clase].to_numpy()
            rects = ax.bar(
                x + (i - 1) * width,
                vals_cap / 1e6,
                width,
                label=f'Clase {clase}',
                color=colores_abc[clase]
            )

            for idx, rect in enumerate(rects):
                h = rect.get_height()
                if h > 0:
                    lbl_val = f"S/. {h:.2f}M" if h >= 0.01 else f"S/. {h*1000:.0f}K"
                    lbl = f"{lbl_val}\n{int(vals_skus[idx]):,} códigos"
                    ax.annotate(
                        lbl,
                        (rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3),
                        textcoords='offset points',
                        ha='center', va='bottom',
                        fontsize=4.7, fontweight='bold', color='#0f172a'
                    )

        ax.set_title("CLASIFICACIÓN ABC POR ALMACÉN", fontsize=8.2, fontweight='bold', color='#0f172a', pad=23)
        ax.set_ylabel("Capital (S/. M)", fontsize=6.5, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(almacenes, fontsize=6, fontweight='bold')
        ax.legend(bbox_to_anchor=(0.5, 1.01), loc='lower center', ncol=3, fontsize=5.5, frameon=True, borderpad=0.35, handlelength=1.4, columnspacing=1.2)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.tick_params(axis='both', labelsize=5.5)

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def _formato_capital(v):
    if v >= 1_000_000:
        return f"S/. {v/1e6:.2f}M"
    if v >= 1_000:
        return f"S/. {v/1e3:.0f}K"
    return f"S/. {v:,.0f}"

def generar_grafico_rotacion_almacen_fidelizado(df_inmov):
    fig, ax = plt.subplots(figsize=(8.5, 3.2), dpi=250)

    tramos = [
        '1 a 3 Meses (Rotación Activa)',
        '3 a 6 Meses (Rotación Media)',
        '6 a 9 Meses (Rotación Baja / Riesgo)',
        '9 a Más Meses (Inmovilizado Crítico)'
    ]
    colores = {
        tramos[0]: COLOR_ACTIVO,
        tramos[1]: COLOR_MEDIO,
        tramos[2]: COLOR_BAJO,
        tramos[3]: COLOR_CRITICO
    }

    if df_inmov.empty:
        ax.text(0.5, 0.5, "Sin datos de rotación disponibles", ha='center', va='center')
        ax.axis('off')
    else:
        pivot = (
            df_inmov.pivot_table(
                index='Almacen', columns='Tramo_Inmovilizado',
                values='Capital', aggfunc='sum', fill_value=0
            ).reindex(columns=tramos, fill_value=0)
        )
        pivot['__total__'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('__total__', ascending=True)
        totals = pivot['__total__'].copy()
        pivot = pivot.drop(columns='__total__')

        almacenes = pivot.index.tolist()
        y = np.arange(len(almacenes))
        lefts = np.zeros(len(almacenes))

        for tramo in tramos:
            vals = pivot[tramo].to_numpy()
            bars = ax.barh(
                y, vals / 1e6, left=lefts / 1e6,
                label=tramo, color=colores[tramo], height=0.75
            )
            
            for idx, bar in enumerate(bars):
                val = vals[idx]
                tot = totals.iloc[idx]
                if val > 0 and tot > 0:
                    val_str = f"S/. {val/1e6:.2f}M" if val >= 1e6 else f"S/. {val/1e3:.0f}K"
                    if (val / tot) > 0.02:
                        x_pos = (lefts[idx] + val / 2) / 1e6
                        ax.text(
                            x_pos, bar.get_y() + bar.get_height()/2,
                            val_str, ha='center', va='center',
                            rotation=-90,
                            fontsize=5, fontweight='bold', color='white'
                        )
            lefts += vals

        x_max = max(float(lefts.max()/1e6), 1.0)
        ax.set_xlim(0, x_max * 1.18)
        for idx, alm in enumerate(almacenes):
            total = float(totals.loc[alm])
            if total <= 0:
                continue
            x_bar = total / 1e6
            ax.annotate(
                _formato_capital(total),
                xy=(x_bar, idx),
                xytext=(x_bar + x_max*0.02, idx),
                textcoords='data',
                ha='left', va='center',
                fontsize=5.8, fontweight='bold', color='#0f172a'
            )

        ax.set_yticks(y)
        ax.set_yticklabels(almacenes, fontsize=6.2, fontweight='bold')
        ax.set_title("VALOR DE TRAMOS DE INMOVILIZACIÓN POR ALMACÉN", fontsize=8.5, fontweight='bold', loc='left', color='#0f172a', pad=22)
        ax.set_xlabel("Capital Valorizado (S/. M)", fontsize=6.5, fontweight='bold')
        ax.legend(bbox_to_anchor=(0.5, 1.01), loc='lower center', ncol=4, fontsize=4.8, frameon=False, handlelength=1.2, columnspacing=0.9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.tick_params(axis='x', labelsize=5.5)

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generar_grafico_top15_familias(df_fam):
    fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=250)

    tramos = [
        '1 a 3 Meses (Rotación Activa)',
        '3 a 6 Meses (Rotación Media)',
        '6 a 9 Meses (Rotación Baja / Riesgo)',
        '9 a Más Meses (Inmovilizado Crítico)'
    ]
    colores = {
        tramos[0]: COLOR_ACTIVO,
        tramos[1]: COLOR_MEDIO,
        tramos[2]: COLOR_BAJO,
        tramos[3]: COLOR_CRITICO
    }

    if df_fam.empty:
        ax.text(0.5, 0.5, "Sin datos de familias disponibles", ha='center', va='center')
        ax.axis('off')
    else:
        pivot = (
            df_fam.pivot_table(
                index='Familia', columns='Tramo_Inmovilizado',
                values='Capital', aggfunc='sum', fill_value=0
            ).reindex(columns=tramos, fill_value=0)
        )
        pivot['__total__'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('__total__', ascending=True).tail(15)
        totals = pivot['__total__'].copy()
        pivot = pivot.drop(columns='__total__')

        familias = pivot.index.tolist()
        y = np.arange(len(familias))
        lefts = np.zeros(len(familias))

        for tramo in tramos:
            vals = pivot[tramo].to_numpy()
            bars = ax.barh(
                y, vals / 1e6, left=lefts / 1e6,
                label=tramo, color=colores[tramo], height=0.72
            )
            
            for idx, bar in enumerate(bars):
                val = vals[idx]
                tot = totals.iloc[idx]
                if val > 0 and tot > 0:
                    val_str = f"S/. {val/1e6:.2f}M" if val >= 1e6 else f"S/. {val/1e3:.0f}K"
                    if (val / totals.max()) > 0.02:
                        x_pos = (lefts[idx] + val / 2) / 1e6
                        ax.text(
                            x_pos, bar.get_y() + bar.get_height()/2,
                            val_str, ha='center', va='center',
                            fontsize=3.5, fontweight='bold', color='white'
                        )
            lefts += vals

        x_max = max(float(lefts.max()/1e6), 1.0)
        ax.set_xlim(0, x_max * 1.18)
        for idx, familia in enumerate(familias):
            total = float(totals.loc[familia])
            if total <= 0:
                continue
            x_bar = total / 1e6
            ax.annotate(
                _formato_capital(total),
                xy=(x_bar, idx),
                xytext=(x_bar + x_max*0.02, idx),
                textcoords='data',
                ha='left', va='center',
                fontsize=5.2, fontweight='bold', color='#0f172a'
            )

        ax.set_yticks(y)
        ax.set_yticklabels(familias, fontsize=5.5)
        ax.set_title("FAMILIAS POR TRAMO DE INMOVILIZACIÓN", fontsize=8.2, fontweight='bold', loc='left', color='#0f172a', pad=22)
        ax.set_xlabel("Capital Valorizado (S/. M)", fontsize=6.5, fontweight='bold')
        ax.legend(bbox_to_anchor=(0.5, 1.01), loc='lower center', ncol=4, fontsize=4.7, frameon=False, handlelength=1.2, columnspacing=0.9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.tick_params(axis='x', labelsize=5.5)

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

# ==============================================================================
# GENERACIÓN DE PDF
# ==============================================================================
def generar_pdf_gerencial(m, periodo, autor, destinatario):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, 
        rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=colors.HexColor('#0f172a'))
    sub_style = ParagraphStyle('S1', fontName='Helvetica', fontSize=6.5, leading=8.5, textColor=colors.HexColor('#475569'))
    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=8, leading=9.5, textColor=colors.HexColor('#0f172a'), spaceBefore=3, spaceAfter=2)

    elements = []
    elements.append(Paragraph("INFORME DE KPIS DE INVENTARIOS", title_style))
    elements.append(Paragraph(f"<b>Periodo:</b> {periodo} | <b>Elaborado por:</b> ARES PERU SAC | <b>Dirigido a:</b> GERENCIA GENERAL", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor('#0f172a'), spaceAfter=4))

    # HOJA 1
    elements.append(Paragraph("1. RESUMEN POR ALMACÉN", h1_style))
    data_alm = [["Almacén", "Capital (S/.)", "SKUs", "Unidades", "% Capital"]]
    for _, r in m['res_alm'].iterrows():
        data_alm.append([str(r['Almacen']), f"S/. {r['Capital']:,.2f}", f"{r['SKUs']:,}", f"{r['Stock_Unidades']:,.0f}", f"{r['Pct_Capital']:.2f}%"])
    t_alm = Table(data_alm, colWidths=[140, 110, 60, 110, 70])
    t_alm.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t_alm)
    elements.append(Spacer(1, 2))

    elements.append(Paragraph("2. CIERRES MENSUALES DEL VALOR DEL INVENTARIO", h1_style))
    elements.append(Image(generar_grafico_evolucion_global(m['df_evol']), width=540, height=135))
    elements.append(Spacer(1, 2))

    elements.append(Paragraph("3. EVOLUCIÓN HISTÓRICA POR ALMACÉN", h1_style))
    for alm_nombre in m['df_evol']['Almacen'].unique():
        elements.append(Image(generar_grafico_almacen_individual(m['df_evol'], alm_nombre), width=540, height=125))
        elements.append(Spacer(1, 2))

    elements.append(PageBreak())

    # HOJA 2
    elements.append(Paragraph("4. INDICADOR ERI Y CONCENTRACIÓN DEL CAPITAL", h1_style))
    elements.append(Image(generar_graficos_eri_reestructurado(m['df_eri_hist'], m['df_eri_alm'], m['res_alm']), width=540, height=140))
    elements.append(Spacer(1, 3))

    elements.append(Paragraph("5. TOP 30 SKUs DE MAYOR CAPITAL VALORIZADO", h1_style))
    elements.append(Image(generar_grafico_top_skus_amplio_30(m['top30_skus'], "Top 30 SKUs de Mayor Concentración de Capital", "magma"), width=540, height=350))

    elements.append(PageBreak())

    # HOJA 3
    elements.append(Paragraph("6. TOP 30 SKUs SIN ROTACIÓN / INMOVILIZADOS (>9 MESES)", h1_style))
    elements.append(Image(generar_grafico_top_skus_amplio_30(m['top30_inmov'], "Top 30 SKUs Críticos Sin Rotación", "viridis"), width=540, height=280))
    elements.append(Spacer(1, 3))

    elements.append(Paragraph("7. CLASIFICACIÓN ABC", h1_style))
    elements.append(Image(generar_grafico_abc_por_almacen(m['res_abc_alm']), width=540, height=150))
    elements.append(Spacer(1, 3))

    elements.append(Paragraph("8. CUADRO PARETO OPERATIVO", h1_style))
    data_pareto = [["Zona ABC", "N° SKUs", "% SKUs", "Salidas (NS)", "% Frecuencia", "Valorización Inventario"]]
    for _, r in m['res_pareto_operativo'].iterrows():
        data_pareto.append([
            f"Clase {r['Clase_ABC']}",
            f"{r['SKUs']:,}",
            f"{r['Pct_SKUs']:.1f}%",
            f"{r['Pedidos']:,.0f}",
            f"{r['Pct_Frecuencia']:.2f}%",
            f"S/. {r['Valorizacion']:,.2f}"
        ])
    t_pareto = Table(data_pareto, colWidths=[80, 65, 65, 100, 110, 120])
    t_pareto.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('TEXTCOLOR', (0,1), (0,1), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0,2), (0,2), colors.HexColor('#d97706')),
        ('TEXTCOLOR', (0,3), (0,3), colors.HexColor('#16a34a')),
        ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold')
    ]))
    elements.append(t_pareto)

    elements.append(PageBreak())

    # HOJA 4
    elements.append(Paragraph("9. ROTACIÓN Y TRAMOS POR ALMACÉN", h1_style))
    elements.append(Image(generar_grafico_rotacion_almacen_fidelizado(m['res_inmov_alm']), width=540, height=180))
    elements.append(Spacer(1, 4))

    elements.append(Paragraph("RESUMEN POR ALMACÉN Y TRAMOS DE ROTACIÓN", h1_style))
    orden_tramos = [
        '1 a 3 Meses (Rotación Activa)',
        '3 a 6 Meses (Rotación Media)',
        '6 a 9 Meses (Rotación Baja / Riesgo)',
        '9 a Más Meses (Inmovilizado Crítico)'
    ]
    df_tramos_alm = m['df_s'].pivot_table(
        index='Almacen',
        columns='Tramo_Inmovilizado',
        values='Capital_Total',
        aggfunc='sum',
        fill_value=0
    ).reindex(columns=orden_tramos, fill_value=0)

    df_resumen_alm = m['df_s'].groupby('Almacen').agg(
        SKUs=('Codigo', 'nunique'),
        Unidades=('Stock', 'sum'),
        Capital_Total=('Capital_Total', 'sum')
    ).reset_index()

    df_master_alm = pd.merge(df_resumen_alm, df_tramos_alm, on='Almacen')
    tot_gen = df_master_alm['Capital_Total'].sum()
    df_master_alm['% Rep. Total'] = (df_master_alm['Capital_Total'] / tot_gen * 100) if tot_gen > 0 else 0
    df_master_alm = df_master_alm.sort_values(by='Capital_Total', ascending=False)

    data_m_pdf = [["Almacén", "SKUs", "Unid.", "Cap. Total", "Activo 1-3M", "Medio 3-6M", "Riesgo 6-9M", "Crítico >9M", "% Total"]]
    for _, r in df_master_alm.iterrows():
        data_m_pdf.append([
            str(r['Almacen']),
            f"{r['SKUs']:,}",
            f"{r['Unidades']:,.0f}",
            f"S/. {r['Capital_Total']:,.2f}",
            f"S/. {r['1 a 3 Meses (Rotación Activa)']:,.2f}",
            f"S/. {r['3 a 6 Meses (Rotación Media)']:,.2f}",
            f"S/. {r['6 a 9 Meses (Rotación Baja / Riesgo)']:,.2f}",
            f"S/. {r['9 a Más Meses (Inmovilizado Crítico)']:,.2f}",
            f"{r['% Rep. Total']:.1f}%"
        ])
    t_m_pdf = Table(data_m_pdf, colWidths=[65, 35, 40, 75, 75, 75, 75, 75, 45])
    t_m_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 5.2),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t_m_pdf)

    elements.append(Spacer(1, 4))
    elements.append(Paragraph("10. TOP FAMILIAS POR CAPITAL (DESGLOSE DE ROTACIÓN)", h1_style))
    elements.append(Image(generar_grafico_top15_familias(m['res_inmov_fam']), width=540, height=220))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==============================================================================
# VISTA STREAMLIT
# ==============================================================================
st.title("INFORME DE KPIS DE INVENTARIO")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Capital Valorizado Total</div>
        <div class='kpi-value'>S/. {m['total_capital']:,.2f}</div>
        <div class='kpi-sub' style='color:#64748b;'>Custodiado en almacenes</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Unidades Custodiadas</div>
        <div class='kpi-value'>{m['total_unidades']:,.0f}</div>
        <div class='kpi-sub' style='color:#64748b;'>Stock físico total positivo</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>SKUs Activos Total</div>
        <div class='kpi-value'>{m['total_skus']:,}</div>
        <div class='kpi-sub' style='color:#64748b;'>Códigos con saldo mayor a 0</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div class='section-header'>DESGLOSE EJECUTIVO DE TRAMOS DE ROTACIÓN Y RIESGO</div>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

pct_critico = (m['monto_critico'] / m['total_capital'] * 100) if m['total_capital'] > 0 else 0
pct_riesgo = (m['monto_riesgo'] / m['total_capital'] * 100) if m['total_capital'] > 0 else 0
pct_media = (m['monto_media'] / m['total_capital'] * 100) if m['total_capital'] > 0 else 0
pct_activa = (m['monto_activa'] / m['total_capital'] * 100) if m['total_capital'] > 0 else 0

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>1-3 Meses (Rotación Activa)</div>
        <div class='kpi-value' style='color:#10b981;'>S/. {m['monto_activa']:,.2f}</div>
        <div class='kpi-sub' style='color:#10b981;'>{pct_activa:.1f}% - Flujo constante</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>3-6 Meses (Rotación Media)</div>
        <div class='kpi-value' style='color:#f59e0b;'>S/. {m['monto_media']:,.2f}</div>
        <div class='kpi-sub' style='color:#f59e0b;'>{pct_media:.1f}% - Observación regular</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>6-9 Meses (Riesgo Próximo)</div>
        <div class='kpi-value' style='color:#f97316;'>S/. {m['monto_riesgo']:,.2f}</div>
        <div class='kpi-sub' style='color:#f97316;'>{pct_riesgo:.1f}% - Alerta de acumulación</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>Inmovilizado Crítico (> 9 Meses)</div>
        <div class='kpi-value' style='color:#b91c1c;'>S/. {m['monto_critico']:,.2f}</div>
        <div class='kpi-sub' style='color:#b91c1c;'>{pct_critico:.1f}% - Inmovilizado severo</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.subheader("Cuadro Pareto Operativo")
st.dataframe(m['res_pareto_operativo'].style.format({
    'SKUs': '{:,}',
    'Pct_SKUs': '{:.1f}%',
    'Pedidos': '{:,.0f}',
    'Pct_Frecuencia': '{:.2f}%',
    'Valorizacion': 'S/. {:,.2f}'
}), use_container_width=True)

st.subheader("1. Tendencia Global de Cierre Mes a Mes")
st.image(generar_grafico_evolucion_global(m['df_evol']), use_container_width=True)

st.subheader("2. Evolutivo Histórico por Cada Almacén")
for alm in m['df_evol']['Almacen'].unique():
    st.image(generar_grafico_almacen_individual(m['df_evol'], alm), use_container_width=True)

st.subheader("3. Indicador ERI y Concentración de Inventario por Almacén")
st.image(generar_graficos_eri_reestructurado(m['df_eri_hist'], m['df_eri_alm'], m['res_alm']), use_container_width=True)

g1, g2 = st.columns(2)
with g1:
    st.image(generar_grafico_top_skus_amplio_30(m['top30_skus'], "Top 30 SKUs por Capital", "magma"), use_container_width=True)
    st.image(generar_grafico_abc_por_almacen(m['res_abc_alm']), use_container_width=True)

with g2:
    st.image(generar_grafico_top_skus_amplio_30(m['top30_inmov'], "Top 30 SKUs Sin Rotación", "viridis"), use_container_width=True)

st.subheader("9. Rotación y Tramos por Almacén")
st.image(generar_grafico_rotacion_almacen_fidelizado(m['res_inmov_alm']), use_container_width=True)

st.markdown("<div class='section-header'>RESUMEN MÁSTER POR ALMACÉN Y TRAMOS DE ROTACIÓN</div>", unsafe_allow_html=True)

orden_tramos = [
    '1 a 3 Meses (Rotación Activa)',
    '3 a 6 Meses (Rotación Media)',
    '6 a 9 Meses (Rotación Baja / Riesgo)',
    '9 a Más Meses (Inmovilizado Crítico)'
]

df_tramos_alm = m['df_s'].pivot_table(
    index='Almacen',
    columns='Tramo_Inmovilizado',
    values='Capital_Total',
    aggfunc='sum',
    fill_value=0
).reindex(columns=orden_tramos, fill_value=0)

df_resumen_alm = m['df_s'].groupby('Almacen').agg(
    SKUs=('Codigo', 'nunique'),
    Unidades=('Stock', 'sum'),
    Capital_Total=('Capital_Total', 'sum')
).reset_index()

df_master_alm = pd.merge(df_resumen_alm, df_tramos_alm, on='Almacen')
total_general = df_master_alm['Capital_Total'].sum()
df_master_alm['% Rep. Total'] = (df_master_alm['Capital_Total'] / total_general * 100) if total_general > 0 else 0
df_master_alm = df_master_alm.sort_values(by='Capital_Total', ascending=False)

df_master_view = pd.DataFrame({
    'Almacén': df_master_alm['Almacen'],
    'SKUs': df_master_alm['SKUs'].map('{:,}'.format),
    'Unidades': df_master_alm['Unidades'].map('{:,.0f}'.format),
    'Capital Total (S/.)': df_master_alm['Capital_Total'].map('S/. {:,.2f}'.format),
    'Activo 1-3M (S/.)': df_master_alm['1 a 3 Meses (Rotación Activa)'].map('S/. {:,.2f}'.format),
    'Medio 3-6M (S/.)': df_master_alm['3 a 6 Meses (Rotación Media)'].map('S/. {:,.2f}'.format),
    'Riesgo 6-9M (S/.)': df_master_alm['6 a 9 Meses (Rotación Baja / Riesgo)'].map('S/. {:,.2f}'.format),
    'Crítico >9M (S/.)': df_master_alm['9 a Más Meses (Inmovilizado Crítico)'].map('S/. {:,.2f}'.format),
    '% del Total': df_master_alm['% Rep. Total'].map('{:.1f}%'.format)
})

st.dataframe(df_master_view, use_container_width=True, hide_index=True)

st.subheader("10. Top 15 Familias por Capital (Desglose de Rotación)")
st.image(generar_grafico_top15_familias(m['res_inmov_fam']), use_container_width=True)

st.markdown("---")
if REPORTLAB_INSTALLED:
    pdf_bytes = generar_pdf_gerencial(
        m, 
        f"Cierre {datetime.date.today().strftime('%B %Y')}", 
        "Ares Peru SAC", 
        "Gerencia General"
    )
    
    st.download_button(
        label="📥 DESCARGAR INFORME GERENCIAL (PDF)",
        data=pdf_bytes,
        file_name=f"Informe_Gerencial_Inventario_{datetime.date.today()}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.error("Instale ReportLab ejecutando `pip install reportlab matplotlib` para habilitar la descarga.")