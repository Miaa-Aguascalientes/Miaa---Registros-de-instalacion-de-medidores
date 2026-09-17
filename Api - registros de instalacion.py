# API - registros de instalacion_4.py
import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
import numpy as np
from shapely.geometry import Point, Polygon
import pydeck as pdk

# SECCIÓN 1: ---------------------------------------------------------------------- CONFIGURACIÓN GENERAL DE LA PÁGINA ---------------------------------------------------------------------------------------------

st.set_page_config(
    page_title="Dashboard Instalación Medidores Inteligentes", 
    page_icon="https://www.miaa.mx/favicon.ico", 
    layout="wide"
)

# SECCIÓN 2: ------------------------------------------------------------------------- ESTILOS CSS PERSONALIZADOS ---------------------------------------------------------------------------------------------------

custom_style = """
    <style>
    /* Importar FontAwesome para los iconos */
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 320px !important;
    }
    
    [data-testid="collapsedControl"] { display: none !important; }

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        margin-top: -30px !important;
    }

    /* Cabecera Superior */
    .dashboard-header-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0px;
        margin-bottom: 8px;
        padding: 5px 0px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        width: 100%;
    }

    .dashboard-main-title {
        font-size: 1.3rem;
        font-weight: 800;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 0;
        text-shadow: 0px 2px 15px rgba(56, 189, 248, 0.2);
    }

    .dashboard-subtitle-right {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
        letter-spacing: 0.3px;
        white-space: nowrap;
    }

    /* Tarjetas Compactas: Indicadores KPI */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 12px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        height: 58px;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.5);
        box-shadow: 0 8px 12px -3px rgba(59, 130, 246, 0.2);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent);
        transition: 0.5s;
    }

    .metric-card:hover::before {
        left: 100%;
    }

    .metric-icon-box {
        font-size: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 30px;
    }

    .metric-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        overflow: hidden;
        width: 100%;
    }

    .metric-title {
        color: #94a3b8;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .metric-value {
        color: #ffffff;
        font-size: 17px;
        font-weight: 700;
        line-height: 1.2;
    }

    /* Estilos para Tarjetas Contenedoras de Gráficos */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.3s ease;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(59, 130, 246, 0.4) !important;
        box-shadow: 0 8px 12px -3px rgba(59, 130, 246, 0.15) !important;
    }

    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# SECCIÓN 2: Cabecera superior del titulo de la pagina
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px;">
        <div style="width: 180px;"></div>
        <div style="flex-grow: 1; text-align: center;">
            <h1 style="color: white; font-size: 26px; margin: 0; font-weight: bold;">DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</h1>
        </div>
        <div style="width: 180px; text-align: right; color: #a0a0a0; font-size: 14px;">
            Actualizado al: 14/09/2026
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# SECCIÓN 3: FUNCIONES DE CONEXIÓN Y DATOS (API Y BASE DE DATOS)
url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

@st.cache_data(ttl=300)
def cargar_datos_api():
    try:
        usuario = st.secrets["api"]["usuario"]
        password = st.secrets["api"]["password"]
        res_login = requests.post(url_login, json={"username": usuario, "password": password}, headers={"Content-Type": "application/json"})
        if res_login.status_code == 200:
            token = res_login.json().get("token") or res_login.json().get("access_token")
            if token:
                res_inst = requests.get(url_instalaciones, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
                if res_inst.status_code == 200:
                    return res_inst.json()
        return None
    except Exception:
        return None

@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = """
            SELECT 
                Colonia_ATL, 
                Usuarios_Reales, 
                Usuarios_con_medidor_inteligente, 
                Usuarios_nueva_instalacion, 
                Poligono_de_instalacion 
            FROM Diccionario_instalacion_medidores
        """
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_poligonos_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = """
            SELECT 
                FID, 
                Sector_comercial, 
                Vertice, 
                coord, 
                Orden_inst, 
                Area_km2, 
                Medidores 
            FROM Diccionario_poligonos_instalacion
        """
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_tipos_instalacion_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = "SELECT ID, tipo_instalacion FROM Diccionario_tipo_instalacion"
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_anomalias_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = "SELECT ID, anomalia FROM Diccionario_anomalias"
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()


# SECCIÓN 4: FUNCIONES AUXILIARES PARA MAPAS
def agregar_capas_base(m):
    api_key = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"
    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key}",
        name="Vista Nocturna",
        attr='&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains="abcd",
        max_zoom=20,
        control=False
    ).add_to(m)
    Fullscreen(position="topright", title="Ampliar Mapa", cancel_title="Salir de pantalla completa").add_to(m)


# SECCIÓN 5: PROCESAMIENTO Y LIMPIEZA INICIAL DE DATOS
if 'datos_instalaciones' not in st.session_state:
    res = cargar_datos_api()
    if res:
        st.session_state['datos_instalaciones'] = res

if 'datos_instalaciones' in st.session_state:
    data = st.session_state['datos_instalaciones']
    lista_registros = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list): lista_registros.extend(v)
            elif isinstance(v, dict): lista_registros.append(v)
        df = pd.DataFrame(lista_registros) if lista_registros else pd.DataFrame([data])
    else:
        df = pd.DataFrame(data if isinstance(data, list) else [data])

    col_fecha_ref = 'fechaRegistro' if 'fechaRegistro' in df.columns else None
    df['fecha_dt'] = pd.to_datetime(df[col_fecha_ref], errors='coerce') if col_fecha_ref else pd.NaT

    lat_centro, lon_centro = 21.8853, -102.2916
    df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce') if 'latitud' in df.columns else np.nan
    df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce') if 'longitud' in df.columns else np.nan

    df_metas = cargar_metas_db()
    df_poligonos = cargar_poligonos_db()
    df_anomalias_db = cargar_anomalias_db()

    df_tipos_db = cargar_tipos_instalacion_db()
    dict_tipos_map = dict(zip(df_tipos_db['ID'].astype(str), df_tipos_db['tipo_instalacion'])) if not df_tipos_db.empty else {}

    if 'lugarInstalacionId' in df.columns:
        df['lugarInstalacion_id_str'] = df['lugarInstalacionId'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        df['tipo_instalacion_nombre'] = df['lugarInstalacion_id_str'].map(dict_tipos_map).fillna("SIN ESPECIFICAR")
    else:
        df['tipo_instalacion_nombre'] = "SIN ESPECIFICAR"

    dict_anomalias_map = dict(zip(df_anomalias_db['ID'].astype(str), df_anomalias_db['anomalia'])) if not df_anomalias_db.empty else {}
    if 'anomaliaId' in df.columns:
        df['anomalia_id_str'] = df['anomaliaId'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        df['anomalia_nombre'] = df['anomalia_id_str'].map(dict_anomalias_map).fillna("SIN ANOMALÍA / REGULAR")
    else:
        df['anomalia_nombre'] = "SIN ANOMALÍA / REGULAR"
    
    df_metas_valido = df_metas[df_metas['Usuarios_con_medidor_inteligente'] > 0].copy() if not df_metas.empty else pd.DataFrame()

    # SECCIÓN 6: BARRA LATERAL (FILTROS Y CONTROLES)
    logo_url = "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg"
    st.sidebar.image(logo_url, use_container_width=True)
    st.sidebar.markdown("---")

    st.sidebar.subheader("Periodo de Fechas")
    opcion_periodo = st.sidebar.selectbox(
        "Seleccionar Rango",
        ["Este mes", "El mes pasado", "Últimos tres meses", "Últimos 6 meses", "Este año", "El año pasado"],
        index=0
    )

    hoy = pd.to_datetime("2026-09-14").date()
    if opcion_periodo == "Este mes":
        fecha_inicio, fecha_fin = hoy.replace(day=1), hoy
    elif opcion_periodo == "El mes pasado":
        mes_anterior = hoy.replace(day=1) - pd.Timedelta(days=1)
        fecha_inicio, fecha_fin = mes_anterior.replace(day=1), mes_anterior
    elif opcion_periodo == "Últimos tres meses":
        fecha_inicio, fecha_fin = (pd.to_datetime(hoy) - pd.DateOffset(months=3)).date(), hoy
    elif opcion_periodo == "Últimos 6 meses":
        fecha_inicio, fecha_fin = (pd.to_datetime(hoy) - pd.DateOffset(months=6)).date(), hoy
    elif opcion_periodo == "Este año":
        fecha_inicio, fecha_fin = hoy.replace(month=1, day=1), hoy
    elif opcion_periodo == "El año pasado":
        fecha_inicio, fecha_fin = hoy.replace(year=hoy.year - 1, month=1, day=1), hoy.replace(year=hoy.year - 1, month=12, day=31)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Polígonos")
    
    lista_poligonos = sorted([str(p) for p in df_metas_valido['Poligono_de_instalacion'].dropna().unique()], key=lambda x: int(x) if x.isdigit() else x) if not df_metas_valido.empty else []

    for p in lista_poligonos:
        if f"chk_pol_{p}" not in st.session_state:
            st.session_state[f"chk_pol_{p}"] = True

    col_c1, col_c2 = st.sidebar.columns(2)
    if col_c1.button("Marcar todos"):
        for p in lista_poligonos: st.session_state[f"chk_pol_{p}"] = True
    if col_c2.button("Desmarcar"):
        for p in lista_poligonos: st.session_state[f"chk_pol_{p}"] = False

    with st.sidebar.container(height=220):
        poligonos_seleccionados = [pol for pol in lista_poligonos if st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}")]

    df_metas_filtrado = df_metas_valido[df_metas_valido['Poligono_de_instalacion'].astype(str).isin(poligonos_seleccionados)].copy() if not df_metas_valido.empty else pd.DataFrame()
    df_filtrado = df.loc[(df['fecha_dt'].dt.date >= fecha_inicio) & (df['fecha_dt'].dt.date <= fecha_fin)].copy() if col_fecha_ref and not df['fecha_dt'].isna().all() else df.copy()

    meta_total = int(df_metas['Usuarios_nueva_instalacion'].sum()) if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else len(df_filtrado)
    total_instalados = len(df_filtrado)
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0

    total_externo = int(df_filtrado['usuarioExterno'].fillna(False).astype(bool).sum()) if 'usuarioExterno' in df_filtrado.columns else 0
    total_miaa = int((~df_filtrado['usuarioExterno'].fillna(False).astype(bool)).sum()) if 'usuarioExterno' in df_filtrado.columns else len(df_filtrado)
    df_externo = df_filtrado[df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy() if 'usuarioExterno' in df_filtrado.columns else pd.DataFrame()
    df_miaa_pers = df_filtrado[~df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy() if 'usuarioExterno' in df_filtrado.columns else df_filtrado.copy()

    if not df_metas_filtrado.empty:
        df_eficiencia = df_metas_filtrado.groupby(['Colonia_ATL', 'Poligono_de_instalacion'], as_index=False).agg({'Usuarios_Reales': 'sum', 'Usuarios_con_medidor_inteligente': 'sum'})
        df_eficiencia['pct_sort'] = np.where(df_eficiencia['Usuarios_Reales'] > 0, (df_eficiencia['Usuarios_con_medidor_inteligente'] / df_eficiencia['Usuarios_Reales']) * 100, 0.0)
        df_eficiencia = df_eficiencia.sort_values(by='pct_sort', ascending=False).reset_index(drop=True)
        df_eficiencia['%'] = df_eficiencia['pct_sort'].round(2).astype(str) + '%'
        df_eficiencia = df_eficiencia.rename(columns={'Colonia_ATL': 'Colonia', 'Usuarios_Reales': 'Med. tot', 'Usuarios_con_medidor_inteligente': 'Med. inst', 'Poligono_de_instalacion': 'Polígono'})[['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono']]
    else:
        df_eficiencia = pd.DataFrame(columns=['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono'])

    # SECCIÓN 7: PESTAÑAS PRINCIPALES
    tab_principal, tab_poligonos, tab_externo, tab_miaa, tab_anomalias, tab_tabla = st.tabs([
        "📊 Dashboard Principal", "🗺️ Mapa Polígonos", "👷 Personal Externo", "👤 Personal MIAA", "⚠️ Análisis de Anomalías", "📋 Tabla Base de Datos Completa"
    ])

    with tab_principal:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-bullseye"></i></div><div class="metric-content"><div class="metric-title">Meta Total</div><div class="metric-value">{meta_total:,}</div></div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-circle-check"></i></div><div class="metric-content"><div class="metric-title">Instalados</div><div class="metric-value">{total_instalados:,}</div></div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div><div class="metric-content"><div class="metric-title">Instalados Externo</div><div class="metric-value">{total_externo:,}</div></div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-building-user"></i></div><div class="metric-content"><div class="metric-title">Instalados MIAA</div><div class="metric-value">{total_miaa:,}</div></div></div>', unsafe_allow_html=True)
        k5.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-chart-pie"></i></div><div class="metric-content"><div class="metric-title">% Avance</div><div class="metric-value">{porc_avance}%</div></div></div>', unsafe_allow_html=True)
        k6.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Sin Coordenadas</div><div class="metric-value">{df_filtrado["latitud"].isna().sum():,}</div></div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
        col_g1, col_g2, col_g3 = st.columns([2.6, 1.2, 0.9])

        with col_g1:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día</p>", unsafe_allow_html=True)
                df_dia = df_filtrado.groupby(df_filtrado['fecha_dt'].dt.date, as_index=False).size() if col_fecha_ref and not df_filtrado['fecha_dt'].isna().all() else pd.DataFrame({'fecha_dia': [], 'size': []})
                if not df_dia.empty: df_dia['fecha_dia'] = pd.to_datetime(df_dia['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_dia = px.bar(df_dia, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#3b82f6']) if not df_dia.empty else px.bar(pd.DataFrame({'Aviso': ['Sin fechas'], 'Valor': [0]}), x='Aviso', y='Valor')
                fig_dia.update_traces(textposition='outside', textfont_size=10)
                fig_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=25, b=5, l=5, r=5), height=230, xaxis_title=None, yaxis_title=None, yaxis=dict(range=[0, 500]))
                st.plotly_chart(fig_dia, use_container_width=True)

        with col_g2:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Tipo de Instalación</p>", unsafe_allow_html=True)
                df_tipo_inst = df_filtrado['tipo_instalacion_nombre'].value_counts().reset_index() if not df_filtrado.empty else pd.DataFrame(columns=['Tipo', 'Cantidad'])
                if not df_tipo_inst.empty: df_tipo_inst.columns = ['Tipo', 'Cantidad']
                fig_pie = go.Figure(go.Pie(labels=df_tipo_inst['Tipo'], values=df_tipo_inst['Cantidad'], hole=0.5, domain=dict(x=[0.0, 0.62], y=[0.05, 0.95]), textinfo='value+percent', texttemplate='%{value} (%{percent})', textposition='outside', textfont=dict(color='#ffffff', size=9), marker=dict(colors=['#38bdf8', '#4ade80', '#f59e0b', '#a855f7', '#f43f5e', '#64748b']))) if not df_tipo_inst.empty else go.Figure(go.Pie(labels=['Sin Datos'], values=[len(df_filtrado)], hole=0.5))
                fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=25, b=25, l=10, r=130), height=230, showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)))
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_g3:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Cuadro vs Registro</p>", unsafe_allow_html=True)
                df_cr = df_filtrado.copy()
                df_cr['categoria_cr'] = df_cr['tipo_instalacion_nombre'].apply(lambda n: 'CUADRO' if 'CUADRO' in str(n).upper() else ('REGISTRO' if 'REGISTRO' in str(n).upper() else None))
                df_counts_cr = df_cr.dropna(subset=['categoria_cr'])['categoria_cr'].value_counts().reset_index() if not df_cr.empty else pd.DataFrame()
                if not df_counts_cr.empty:
                    df_counts_cr.columns = ['Tipo', 'Cantidad']
                    tot_cr = df_counts_cr['Cantidad'].sum()
                    fig_cr = go.Figure(go.Pie(labels=df_counts_cr['Tipo'], values=df_counts_cr['Cantidad'], hole=0.6, textinfo='value+percent', marker=dict(colors=[{'CUADRO': '#0066cc', 'REGISTRO': '#e83e8c'}.get(t, '#3b82f6') for t in df_counts_cr['Tipo']])))
                    fig_cr.update_layout(annotations=[dict(text=f"{tot_cr/1000:.1f} mil" if tot_cr >= 1000 else f"{tot_cr:,}", x=0.5, y=0.5, font_size=16, font_color="white", font_weight="bold", showarrow=False)], plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=230, showlegend=True, legend=dict(orientation="h", y=-0.2, font=dict(size=9)))
                else:
                    fig_cr = go.Figure(go.Pie(labels=['Sin Datos'], values=[0], hole=0.6))
                    fig_cr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', height=230)
                st.plotly_chart(fig_cr, use_container_width=True)

        col_inf1, col_inf2 = st.columns([1, 1.6])
        with col_inf1:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Eficiencia por Colonia y Polígono</p>", unsafe_allow_html=True)
                if not df_eficiencia.empty: st.dataframe(df_eficiencia, use_container_width=True, hide_index=True, height=330)
                else: st.info("No se encontraron datos.")

        with col_inf2:
            col_map_h, col_graf_h = st.columns([2.2, 1])
            with col_map_h:
                with st.container(border=True):
                    st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones (Externo vs MIAA)</p>", unsafe_allow_html=True)
                    df_mapa_valido = df_filtrado.dropna(subset=['latitud', 'longitud'])
                    mapa_miaa = folium.Map(location=[df_mapa_valido['latitud'].mean() if not df_mapa_valido.empty else lat_centro, df_mapa_valido['longitud'].mean() if not df_mapa_valido.empty else lon_centro], zoom_start=12, tiles=None)
                    agregar_capas_base(mapa_miaa)
                    for _, row in df_mapa_valido.iterrows():
                        color_punto = '#f59e0b' if bool(row.get('usuarioExterno', False)) else '#a855f7'
                        folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color=color_punto, fill=True, fill_color=color_punto, fill_opacity=0.7).add_to(mapa_miaa)
                    st_folium(mapa_miaa, width=None, height=320, key="mapa_estatico_instalaciones", returned_objects=[])
                    
            with col_graf_h:
                with st.container(border=True):
                    st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Mes</p>", unsafe_allow_html=True)
                    df_mes = df.copy()
                    if col_fecha_ref and not df['fecha_dt'].isna().all():
                        df_mes['periodo_mes'] = df_mes['fecha_dt'].dt.to_period('M')
                        df_mes = df_mes.groupby('periodo_mes', as_index=False).size()
                        df_mes.columns = ['Periodo', 'Cantidad']
                        meses_es = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
                        df_mes['Mes'] = df_mes['Periodo'].apply(lambda x: f"{meses_es[x.month]} {x.year}")
                        df_mes = df_mes.sort_values(by='Periodo', ascending=True)
                    else:
                        df_mes = pd.DataFrame({'Mes': ['Sin datos'], 'Cantidad': [0]})

                    fig_mes_h = px.bar(df_mes, x='Cantidad', y='Mes', orientation='h', text='Cantidad', color='Mes', color_discrete_sequence=['#1e3a8a', '#3b82f6'])
                    fig_mes_h.update_traces(textposition='outside', textfont_size=10)
                    fig_mes_h.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=2, b=2, l=5, r=40), height=130, xaxis=dict(showgrid=False, showticklabels=False, title=None), yaxis=dict(showgrid=False, title=None, tickfont=dict(size=10)), showlegend=False)
                    st.plotly_chart(fig_mes_h, use_container_width=True)

                with st.container(border=True):
                    st.markdown("<p style='font-size:12px; margin-bottom:8px; font-weight:bold;'>Total de Anomalías</p>", unsafe_allow_html=True)
                    total_anomalias_actual = len(df_filtrado[df_filtrado['anomalia_nombre'] != "SIN ANOMALÍA / REGULAR"]) if not df_filtrado.empty else 0
                    st.markdown(f'<div style="display: flex; align-items: center; justify-content: center; gap: 20px; padding: 32px 0;"><div style="font-size: 38px; color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div><div style="font-size: 36px; font-weight: bold; color: #ffffff;">{total_anomalias_actual:,}</div></div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # PESTAÑA: ANÁLISIS DE ANOMALÍAS
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_anomalias:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>⚠️ Análisis Completo de Anomalías en Instalaciones</p>", unsafe_allow_html=True)
        df_con_anomalia = df_filtrado[df_filtrado['anomalia_nombre'] != "SIN ANOMALÍA / REGULAR"].copy()
        total_anomalias_reg, total_registros_filtrados = len(df_con_anomalia), len(df_filtrado)
        pct_anomalias = round((total_anomalias_reg / total_registros_filtrados) * 100, 2) if total_registros_filtrados > 0 else 0.0

        a1, a2, a3, a4 = st.columns(4)
        a1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Total con Anomalía</div><div class="metric-value">{total_anomalias_reg:,}</div></div></div>', unsafe_allow_html=True)
        a2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-list-check"></i></div><div class="metric-content"><div class="metric-title">Tipos de Anomalías</div><div class="metric-value">{df_con_anomalia["anomalia_nombre"].nunique():,}</div></div></div>', unsafe_allow_html=True)
        a3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-percent"></i></div><div class="metric-content"><div class="metric-title">% Incidencia</div><div class="metric-value">{pct_anomalias}%</div></div></div>', unsafe_allow_html=True)
        a4.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-clipboard-check"></i></div><div class="metric-content"><div class="metric-title">Instalaciones Regulares</div><div class="metric-value">{(total_registros_filtrados - total_anomalias_reg):,}</div></div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        col_anom_g1, col_anom_g2 = st.columns([1.5, 1])

        with col_anom_g1:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Tipo de Anomalía</p>", unsafe_allow_html=True)
                if not df_con_anomalia.empty:
                    df_counts_anom = df_con_anomalia['anomalia_nombre'].value_counts().reset_index()
                    df_counts_anom.columns = ['Anomalía', 'Cantidad']
                    fig_anom_bar = px.bar(df_counts_anom, x='Cantidad', y='Anomalía', orientation='h', text='Cantidad', color='Anomalía', color_discrete_sequence=px.colors.qualitative.Bold)
                    fig_anom_bar.update_traces(textposition='outside', textfont_size=10)
                    fig_anom_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=30), height=270, xaxis=dict(showgrid=True, title=None), yaxis=dict(showgrid=False, title=None, categoryorder='total ascending'), showlegend=False)
                    st.plotly_chart(fig_anom_bar, use_container_width=True)
                else:
                    st.info("No se registran anomalías.")

        with col_anom_g2:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Proporción: Con Anomalía vs Regular</p>", unsafe_allow_html=True)
                if total_registros_filtrados > 0:
                    fig_prop_pie = px.pie(pd.DataFrame({'Estado': ['Con Anomalía', 'Regular / Sin Anomalía'], 'Cantidad': [total_anomalias_reg, total_registros_filtrados - total_anomalias_reg]}), names='Estado', values='Cantidad', hole=0.5, color='Estado', color_discrete_map={'Con Anomalía': '#f43f5e', 'Regular / Sin Anomalía': '#3b82f6'})
                    fig_prop_pie.update_traces(textinfo='value+percent', textfont=dict(size=11))
                    fig_prop_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10), height=270, showlegend=True, legend=dict(orientation="h", y=-0.2, font=dict(size=9)))
                    st.plotly_chart(fig_prop_pie, use_container_width=True)

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:20px; margin-bottom:8px;'>📋 Detalle de Registros con Anomalías Detectadas</p>", unsafe_allow_html=True)
        if not df_con_anomalia.empty:
            df_tabla_anom = df_con_anomalia.drop(columns=[c for c in df_con_anomalia.columns if any(term in c.lower() for term in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore')
            if 'fechaInstalacion' in df_tabla_anom.columns: df_tabla_anom['fechaInstalacion'] = pd.to_datetime(df_tabla_anom['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
            st.dataframe(df_tabla_anom.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore'), use_container_width=True)
        else:
            st.success("¡Excelente! No hay registros con anomalías reportadas.")

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # PESTAÑA: MAPA TRIDIMENSIONAL DE POLÍGONOS (CON TARJETAS DE INFORMACIÓN PERMANENTES)
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_poligonos:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:5px;'>🗺️ Mapa Tridimensional de Polígonos de Instalación</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; color: #94a3b8; margin-bottom:12px;'>Visualización 3D con tarjetas informativas estáticas permanentes para cada polígono activo.</p>", unsafe_allow_html=True)
        
        if not df_poligonos.empty:
            fids_disponibles = sorted(df_poligonos['FID'].dropna().unique().tolist(), key=lambda x: int(x) if str(x).isdigit() else str(x))
            for fid in fids_disponibles:
                if f"sel_map_fid_{fid}" not in st.session_state: st.session_state[f"sel_map_fid_{fid}"] = True

            col_sel_izq, col_map_der = st.columns([0.28, 0.72])

            with col_sel_izq:
                st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:5px;'>Seleccionar Polígonos (FID):</p>", unsafe_allow_html=True)
                b_col1, b_col2 = st.columns(2)
                if b_col1.button("Todos", key="btn_all_fids"):
                    for fid in fids_disponibles: st.session_state[f"sel_map_fid_{fid}"] = True
                if b_col2.button("Ninguno", key="btn_none_fids"):
                    for fid in fids_disponibles: st.session_state[f"sel_map_fid_{fid}"] = False

                with st.container(height=450):
                    fids_seleccionados_mapa = [fid for fid in fids_disponibles if st.checkbox(f"Polígono {fid}", key=f"sel_map_fid_{fid}")]

            with col_map_der:
                lat_acumuladas, lon_acumuladas = [], []
                poligonos_procesados, shapely_polygons = {}, {}
                
                for fid in fids_disponibles:
                    df_pol_sel = df_poligonos[df_poligonos['FID'] == fid].sort_values(by='Orden_inst', ascending=True)
                    coordenadas_poligono = []
                    sec_comercial = df_pol_sel['Sector_comercial'].iloc[0] if 'Sector_comercial' in df_pol_sel.columns else "N/A"
                    area_val = df_pol_sel['Area_km2'].iloc[0] if 'Area_km2' in df_pol_sel.columns else 0
                    med_val = df_pol_sel['Medidores'].iloc[0] if 'Medidores' in df_pol_sel.columns else 0

                    for _, r_vertice in df_pol_sel.iterrows():
                        c_val = r_vertice['coord']
                        if pd.isna(c_val): continue
                        c_str = str(c_val).strip()
                        for char in ['(', ')', '[', ']', '"', "'", 'POINT', 'POLYGON']: c_str = c_str.replace(char, '')
                        pares = [p.strip() for p in c_str.split(',') if p.strip()]
                        
                        if len(pares) >= 2 and len(pares) % 2 == 0:
                            for i in range(0, len(pares), 2):
                                try:
                                    p1, p2 = float(pares[i]), float(pares[i+1])
                                    lat, lon = (p2, p1) if abs(p1) > abs(p2) else (p1, p2)
                                    coordenadas_poligono.append([lat, lon])
                                    if fid in fids_seleccionados_mapa: lat_acumuladas.append(lat); lon_acumuladas.append(lon)
                                except Exception: pass

                    if coordenadas_poligono:
                        poligonos_procesados[fid] = {'coordenadas': coordenadas_poligono, 'sector': sec_comercial, 'area': area_val, 'medidores_db': med_val, 'vertis': len(coordenadas_poligono)}
                        try:
                            poly_geom = Polygon(coordenadas_poligono)
                            if not poly_geom.is_valid: poly_geom = poly_geom.buffer(0)
                            shapely_polygons[fid] = poly_geom
                        except Exception: pass

                conteo_medidores_instalados = {fid: 0 for fid in fids_disponibles}
                if shapely_polygons and not df_filtrado.empty:
                    try:
                        for _, row_m in df_filtrado.dropna(subset=['latitud', 'longitud']).iterrows():
                            pt = Point(row_m['latitud'], row_m['longitud'])
                            for fid, poly in shapely_polygons.items():
                                if poly.contains(pt): conteo_medidores_instalados[fid] += 1; break
                    except Exception: pass

                m_p_lat = sum(lat_acumuladas) / len(lat_acumuladas) if lat_acumuladas else lat_centro
                m_p_lon = sum(lon_acumuladas) / len(lon_acumuladas) if lon_acumuladas else lon_centro
                max_inst = max([conteo_medidores_instalados.get(fid, 0) for fid in fids_seleccionados_mapa], default=1) or 1

                pydeck_data = []
                for fid, datos in poligonos_procesados.items():
                    if fid in fids_seleccionados_mapa:
                        inst_count = conteo_medidores_instalados.get(fid, 0)
                        med_db = int(datos['medidores_db'])
                        pct_avance_pol = round((inst_count / med_db * 100), 1) if med_db > 0 else 0.0
                        polygon_coords_lon_lat = [[coord[1], coord[0]] for coord in datos['coordenadas']]
                        
                        if inst_count == 0: color, elevation = [239, 68, 68, 185], 20
                        elif inst_count >= max_inst * 0.5: color, elevation = [34, 197, 94, 185], float(inst_count * 12 + 50)
                        else: color, elevation = [234, 179, 8, 185], float(inst_count * 12 + 30)

                        poly_geom = shapely_polygons.get(fid)
                        centroid_coord = [poly_geom.centroid.y, poly_geom.centroid.x, elevation + 15] if poly_geom else [m_p_lon, m_p_lat, 50]
                        
                        pydeck_data.append({
                            "polygon": polygon_coords_lon_lat, "elevation": elevation, "color": color,
                            "fid": str(fid), "sector": str(datos['sector']), "medidores_db": med_db,
                            "instalados": int(inst_count), "avance": f"{pct_avance_pol}%",
                            "centroid": centroid_coord,
                            "label": f"F{fid} | {pct_avance_pol}%\n({inst_count}/{med_db})"
                        })

                # Capa 3D de Polígonos
                layer_polygon = pdk.Layer("PolygonLayer", pydeck_data, get_polygon="polygon", get_elevation="elevation", get_fill_color="color", get_line_color=[255, 255, 255, 160], line_width_min_pixels=1.5, extruded=True, pickable=True, auto_highlight=True)
                
                # Capa de Texto Permanente de Alta Visibilidad
                layer_text = pdk.Layer("TextLayer", pydeck_data, get_position="centroid", get_text="label", get_size=12, get_color=[255, 255, 255, 255], get_angle=0, get_text_anchor="middle", get_alignment_baseline="center", pickable=False)

                r = pdk.Deck(layers=[layer_polygon, layer_text], initial_view_state=pdk.ViewState(latitude=m_p_lat, longitude=m_p_lon, zoom=11.2, pitch=48, bearing=0), tooltip=False)
                st.pydeck_chart(r, use_container_width=True)

                # TARJETAS FLOTANTES PERMANENTES INFERIORES (Estilo Tarjeta Detallada Fija)
                st.markdown("<p style='font-size:13px; font-weight:bold; margin-top:10px;'>📌 Tarjetas de Información Permanente por Polígono:</p>", unsafe_allow_html=True)
                cols_cards = st.columns(min(len(pydeck_data), 3) if pydeck_data else 1)
                for idx, p_item in enumerate(pydeck_data):
                    with cols_cards[idx % len(cols_cards)]:
                        st.markdown(f"""
                            <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 10px; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                                <div style="color: #38bdf8; font-weight: bold; font-size: 13px; margin-bottom: 4px;">Polígono FID: {p_item['fid']}</div>
                                <div style="color: #cbd5e1; font-size: 11px;">Sector: <b>{p_item['sector']}</b></div>
                                <div style="color: #cbd5e1; font-size: 11px;">Instalaciones: <b>{p_item['instalados']} / {p_item['medidores_db']}</b></div>
                                <div style="color: #4ade80; font-size: 11px; font-weight: bold;">Avance: {p_item['avance']}</div>
                            </div>
                        """, unsafe_allow_html=True)

            st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:20px; margin-bottom:10px;'>📋 Detalle de Polígonos de Instalación y Conteo de Medidores</p>", unsafe_allow_html=True)
            resumen_poligonos = [{'FID': fid, 'Sector Comercial': datos['sector'], 'Área (km²)': datos['area'], 'Medidores (DB)': datos['medidores_db'], 'Medidores Instalados (API)': conteo_medidores_instalados.get(fid, 0), 'Avance (%)': f"{round((conteo_medidores_instalados.get(fid, 0) / datos['medidores_db'] * 100), 2)}%" if datos['medidores_db'] > 0 else '0.0%', 'Vértices Totales': datos['vertis']} for fid, datos in poligonos_procesados.items() if fid in fids_seleccionados_mapa]
            st.dataframe(pd.DataFrame(resumen_poligonos), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # PESTAÑA: PERSONAL EXTERNO
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_externo:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>👷 Resumen de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        e1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div><div class="metric-content"><div class="metric-title">Total Instalados (Externo)</div><div class="metric-value">{len(df_externo):,}</div></div></div>', unsafe_allow_html=True)
        e2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div><div class="metric-content"><div class="metric-title">Colonias Atendidas</div><div class="metric-value">{df_externo["colonia"].nunique():,}</div></div></div>', unsafe_allow_html=True) if not df_externo.empty else None
        e3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Sin Coordenadas</div><div class="metric-value">{df_externo["latitud"].isna().sum():,}</div></div></div>', unsafe_allow_html=True) if not df_externo.empty else None

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_ex_left, col_ex_right = st.columns([1.1, 1.3])

        with col_ex_left:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día (Externo)</p>", unsafe_allow_html=True)
                df_ed = df_externo.groupby(df_externo['fecha_dt'].dt.date, as_index=False).size() if col_fecha_ref and not df_externo.empty and not df_externo['fecha_dt'].isna().all() else pd.DataFrame()
                if not df_ed.empty: df_ed['fecha_dia'] = pd.to_datetime(df_ed['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_ext_dia = px.bar(df_ed, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#f59e0b']) if not df_ed.empty else px.bar(pd.DataFrame({'Aviso': ['Sin datos'], 'Valor': [0]}), x='Aviso', y='Valor')
                fig_ext_dia.update_traces(textposition='outside', textfont_size=10)
                fig_ext_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig_ext_dia, use_container_width=True)

            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Nivel Tarifario (Externo)</p>", unsafe_allow_html=True)
                df_ext_nivel = df_externo['nivel'].fillna("SIN NIVEL").value_counts().reset_index() if 'nivel' in df_externo.columns and not df_externo.empty else pd.DataFrame()
                if not df_ext_nivel.empty: df_ext_nivel.columns = ['Nivel', 'Cantidad']
                fig_ext_niv = px.bar(df_ext_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Safe) if not df_ext_nivel.empty else px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad')
                fig_ext_niv.update_traces(textposition='outside', textfont_size=10)
                fig_ext_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_ext_niv, use_container_width=True)

        with col_ex_right:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
                df_ext_map = df_externo.dropna(subset=['latitud', 'longitud']) if not df_externo.empty else pd.DataFrame()
                mapa_ext = folium.Map(location=[df_ext_map['latitud'].mean() if not df_ext_map.empty else lat_centro, df_ext_map['longitud'].mean() if not df_ext_map.empty else lon_centro], zoom_start=12, tiles=None)
                agregar_capas_base(mapa_ext)
                for _, row in df_ext_map.iterrows():
                    folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#f59e0b', fill=True, fill_color='#f59e0b', fill_opacity=0.7).add_to(mapa_ext)
                st_folium(mapa_ext, width=None, height=460, key="mapa_externo", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal Externo</p>", unsafe_allow_html=True)
        df_tabla_ext = df_externo.drop(columns=[c for c in df_externo.columns if any(term in c.lower() for term in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore') if not df_externo.empty else pd.DataFrame()
        if not df_tabla_ext.empty and 'fechaInstalacion' in df_tabla_ext.columns: df_tabla_ext['fechaInstalacion'] = pd.to_datetime(df_tabla_ext['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
        st.dataframe(df_tabla_ext.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore'), use_container_width=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # PESTAÑA: PERSONAL MIAA
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_miaa:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🏢 Resumen de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #10b981;"><i class="fa-solid fa-building-user"></i></div><div class="metric-content"><div class="metric-title">Total Instalados (MIAA)</div><div class="metric-value">{len(df_miaa_pers):,}</div></div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div><div class="metric-content"><div class="metric-title">Colonias Atendidas</div><div class="metric-value">{df_miaa_pers["colonia"].nunique():,}</div></div></div>', unsafe_allow_html=True) if not df_miaa_pers.empty else None
        m3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Sin Coordenadas</div><div class="metric-value">{df_miaa_pers["latitud"].isna().sum():,}</div></div></div>', unsafe_allow_html=True) if not df_miaa_pers.empty else None

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_mi_left, col_mi_right = st.columns([1.1, 1.3])

        with col_mi_left:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día (MIAA)</p>", unsafe_allow_html=True)
                df_md = df_miaa_pers.groupby(df_miaa_pers['fecha_dt'].dt.date, as_index=False).size() if col_fecha_ref and not df_miaa_pers.empty and not df_miaa_pers['fecha_dt'].isna().all() else pd.DataFrame()
                if not df_md.empty: df_md['fecha_dia'] = pd.to_datetime(df_md['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_miaa_dia = px.bar(df_md, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#10b981']) if not df_md.empty else px.bar(pd.DataFrame({'Aviso': ['Sin datos'], 'Valor': [0]}), x='Aviso', y='Valor')
                fig_miaa_dia.update_traces(textposition='outside', textfont_size=10)
                fig_miaa_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig_miaa_dia, use_container_width=True)

            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Nivel Tarifario (MIAA)</p>", unsafe_allow_html=True)
                df_miaa_nivel = df_miaa_pers['nivel'].fillna("SIN NIVEL").value_counts().reset_index() if 'nivel' in df_miaa_pers.columns and not df_miaa_pers.empty else pd.DataFrame()
                if not df_miaa_nivel.empty: df_miaa_nivel.columns = ['Nivel', 'Cantidad']
                fig_miaa_niv = px.bar(df_miaa_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Pastel) if not df_miaa_nivel.empty else px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad')
                fig_miaa_niv.update_traces(textposition='outside', textfont_size=10)
                fig_miaa_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_miaa_niv, use_container_width=True)

        with col_mi_right:
            with st.container(border=True):
                st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
                df_miaa_map = df_miaa_pers.dropna(subset=['latitud', 'longitud']) if not df_miaa_pers.empty else pd.DataFrame()
                mapa_miaa_pers = folium.Map(location=[df_miaa_map['latitud'].mean() if not df_miaa_map.empty else lat_centro, df_miaa_map['longitud'].mean() if not df_miaa_map.empty else lon_centro], zoom_start=12, tiles=None)
                agregar_capas_base(mapa_miaa_pers)
                for _, row in df_miaa_map.iterrows():
                    folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#10b981', fill=True, fill_color='#10b981', fill_opacity=0.7).add_to(mapa_miaa_pers)
                st_folium(mapa_miaa_pers, width=None, height=460, key="mapa_miaa_personal", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal MIAA</p>", unsafe_allow_html=True)
        df_tabla_miaa = df_miaa_pers.drop(columns=[c for c in df_miaa_pers.columns if any(term in c.lower() for term in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore') if not df_miaa_pers.empty else pd.DataFrame()
        if not df_tabla_miaa.empty and 'fechaInstalacion' in df_tabla_miaa.columns: df_tabla_miaa['fechaInstalacion'] = pd.to_datetime(df_tabla_miaa['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
        st.dataframe(df_tabla_miaa.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore'), use_container_width=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # PESTAÑA: TABLA BASE DE DATOS COMPLETA
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_tabla:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📋 Tabla Completa de Registros de la API</p>", unsafe_allow_html=True)
        t1, t2 = st.columns(2)
        t1.markdown(f'<div class="metric-card"><div class="icon-box" style="color: #38bdf8;"><i class="fa-solid fa-table-list"></i></div><div class="metric-content"><div class="metric-title">Total de Registros</div><div class="metric-value">{len(df_filtrado):,}</div></div></div>', unsafe_allow_html=True)
        t2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-map-pin"></i></div><div class="metric-content"><div class="metric-title">Colonias Registradas</div><div class="metric-value">{df_filtrado["colonia"].nunique():,}</div></div></div>', unsafe_allow_html=True) if 'colonia' in df_filtrado.columns else None

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:4px;'>Distribución por Nivel (Comercial / Doméstico)</p>", unsafe_allow_html=True)
            df_nivel = df_filtrado['nivel'].fillna("SIN NIVEL").value_counts().reset_index() if 'nivel' in df_filtrado.columns else pd.DataFrame()
            if not df_nivel.empty: df_nivel.columns = ['Nivel', 'Cantidad']
            fig_nivel = px.bar(df_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Prism) if not df_nivel.empty else px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad')
            fig_nivel.update_traces(textposition='outside', textfont_size=11)
            fig_nivel.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_nivel, use_container_width=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=Team := None)
        df_tabla_limpia = df_filtrado.drop(columns=[c for c in df_filtrado.columns if any(term in c.lower() for term in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore')
        if 'fechaInstalacion' in df_tabla_limpia.columns: df_tabla_limpia['fechaInstalacion'] = pd.to_datetime(df_tabla_limpia['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
        if 'horaInicio' in df_tabla_limpia.columns: df_tabla_limpia['horaInicio'] = pd.to_datetime(df_tabla_limpia['horaInicio'], errors='coerce').dt.strftime('%H:%M')
        st.dataframe(df_tabla_limpia.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore'), use_container_width=True)
