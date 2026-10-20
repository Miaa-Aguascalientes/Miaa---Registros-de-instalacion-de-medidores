import datetime
import json
import folium
from folium.plugins import Fullscreen, AntPath
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import requests
from shapely.geometry import Point, Polygon
from sqlalchemy import create_engine
import streamlit as st
from streamlit_folium import st_folium

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN GENERAL DE LA PÁGINA Y ESTILOS CSS
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Instalación Medidores Inteligentes",
    page_icon="https://www.miaa.mx/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

custom_style = """
    <style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 320px !important;
        transform: none !important;
        visibility: visible !important;
    }
    
    section[data-testid="stSidebar"] {
        display: block !important;
    }
    
    [data-testid="collapsedControl"] { display: none !important; }

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        margin-top: -30px !important;
    }

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

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
    }

    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# ==============================================================================
# SECCIÓN 2: FUNCIONES DE CONEXIÓN Y DATOS
# ==============================================================================

BASE_URL = "https://prelec.miaa.mx"
URL_LOGIN_CORRECTA = "/auth/login"
URL_INSTALACIONES = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"


@st.cache_data(ttl=300)
def cargar_datos_api():
    try:
        usuario = st.secrets["api"]["usuario"]
        password = st.secrets["api"]["password"]
        payload = {"username": usuario, "password": password}
        headers = {"Content-Type": "application/json"}
        url_login = BASE_URL + URL_LOGIN_CORRECTA

        res_login = requests.post(url_login, json=payload, headers=headers, timeout=15)
        if res_login.status_code == 200:
            data_json = res_login.json()
            token = data_json.get("token") or data_json.get("access_token")
            if token:
                res_inst = requests.get(
                    URL_INSTALACIONES,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=30,
                )
                if res_inst.status_code == 200:
                    return res_inst.json()
        return None
    except Exception as e:
        print(f"Error en cargar_datos_api: {e}")
        return None


@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = "SELECT Colonia_ATL, Usuarios_Reales, Usuarios_con_medidor_inteligente, Usuarios_nueva_instalacion, Poligono_de_instalacion FROM Diccionario_instalacion_medidores"
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_poligonos_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = "SELECT FID, Sector_comercial, Vertice, coord, Orden_inst, Area_km2, Medidores FROM Diccionario_poligonos_instalacion"
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


@st.cache_data(ttl=600)
def cargar_google_sheets_interno():
    try:
        sheet_id = "1Ovj2DZ19Y8H4BtamnVwB71c2dyHC3dyVmau-tMbWre8"
        url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Instalaciones"
        return pd.read_csv(url_csv)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_usuarios_miaa_conmedidor_db():
    try:
        cfg = st.secrets["postgres"]
        conn_str = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        engine = create_engine(conn_str)
        query = 'SELECT *, ST_AsText(geom) as geom, ST_X(geom) as utm_x, ST_Y(geom) as utm_y FROM "Usuarios"."usuarios_miaa_conmedidor" WHERE etapa::text IN (\'1\', \'2\', \'etapa 1\', \'etapa 2\')'
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()


# ==============================================================================
# SECCIÓN 3: FUNCIONES AUXILIARES PARA MAPAS
# ==============================================================================
def agregar_capas_base(m):
    api_key = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"
    folium.TileLayer(tiles="OpenStreetMap", name="OpenStreetMap", max_zoom=19).add_to(m)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Satélite con Calles",
        max_zoom=20,
    ).add_to(m)
    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key}",
        name="Vista Nocturna",
        attr="CARTO",
        subdomains="abcd",
        max_zoom=20,
    ).add_to(m)
    folium.LayerControl(position="topleft").add_to(m)
    Fullscreen(position="topright", title="Ampliar Mapa").add_to(m)


# ==============================================================================
# SECCIÓN 4: PROCESAMIENTO Y LIMPIEZA INICIAL DE DATOS
# ==============================================================================
if "datos_instalaciones" not in st.session_state:
    res = cargar_datos_api()
    if res:
        st.session_state["datos_instalaciones"] = res

if "datos_instalaciones" in st.session_state:
    data = st.session_state["datos_instalaciones"]
    lista_registros = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                lista_registros.extend(v)
            elif isinstance(v, dict):
                lista_registros.append(v)
        df = pd.DataFrame(lista_registros) if lista_registros else pd.DataFrame([data])
    else:
        df = pd.DataFrame(data if isinstance(data, list) else [data])
else:
    df = pd.DataFrame()

col_fecha_ref = "fechaRegistro" if "fechaRegistro" in df.columns else None
df["fecha_dt"] = (
    pd.to_datetime(df[col_fecha_ref], errors="coerce")
    if col_fecha_ref and not df.empty
    else pd.NaT
)

lat_centro, lon_centro = 21.8853, -102.2916
df["latitud"] = (
    pd.to_numeric(df["latitud"], errors="coerce")
    if "latitud" in df.columns
    else np.nan
)
df["longitud"] = (
    pd.to_numeric(df["longitud"], errors="coerce")
    if "longitud" in df.columns
    else np.nan
)

df_metas = cargar_metas_db()
df_poligonos = cargar_poligonos_db()
df_anomalias_db = cargar_anomalias_db()
df_sheets_interno = cargar_google_sheets_interno()

df_tipos_db = cargar_tipos_instalacion_db()
dict_tipos_map = (
    dict(zip(df_tipos_db["ID"].astype(str), df_tipos_db["tipo_instalacion"]))
    if not df_tipos_db.empty
    else {}
)

if not df.empty and "lugarInstalacionId" in df.columns:
    df["lugarInstalacion_id_str"] = (
        df["lugarInstalacionId"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
    )
    df["tipo_instalacion_nombre"] = df["lugarInstalacion_id_str"].map(
        dict_tipos_map
    ).fillna("SIN ESPECIFICAR")
else:
    if not df.empty:
        df["tipo_instalacion_nombre"] = "SIN ESPECIFICAR"

dict_anomalias_map = (
    dict(zip(df_anomalias_db["ID"].astype(str), df_anomalias_db["anomalia"]))
    if not df_anomalias_db.empty
    else {}
)
if not df.empty and "anomaliaId" in df.columns:
    df["anomalia_id_str"] = (
        df["anomaliaId"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
    )
    df["anomalia_nombre"] = df["anomalia_id_str"].map(dict_anomalias_map).fillna(
        "SIN ANOMALÍA / REGULAR"
    )
else:
    if not df.empty:
        df["anomalia_nombre"] = "SIN ANOMALÍA / REGULAR"

if not df_metas.empty:
    for col_num in [
        "Usuarios_Reales",
        "Usuarios_con_medidor_inteligente",
        "Usuarios_nueva_instalacion",
    ]:
        if col_num in df_metas.columns:
            df_metas[col_num] = pd.to_numeric(
                df_metas[col_num].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0)
    df_metas_valido = df_metas[
        df_metas["Usuarios_con_medidor_inteligente"] > 0
    ].copy()
else:
    df_metas_valido = pd.DataFrame()

# ==============================================================================
# SECCIÓN 5: CABECERA SUPERIOR
# ==============================================================================
try:
    hoy = (
        pd.to_datetime(df["fecha_dt"].max()).date()
        if not df.empty and pd.notna(df["fecha_dt"].max())
        else datetime.date.today()
    )
except:
    hoy = datetime.date.today()

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px;">
        <div style="width: 180px;"></div>
        <div style="flex-grow: 1; text-align: center;">
            <h1 style="color: white; font-size: 26px; margin: 0; font-weight: bold;">DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</h1>
        </div>
        <div style="width: 180px; text-align: right; color: #a0a0a0; font-size: 14px;">
            Actualizado al: {hoy.strftime('%d/%m/%Y')}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# SECCIÓN 6: BARRA LATERAL (FILTROS)
# ==============================================================================
logo_url = "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg"
st.sidebar.image(logo_url, use_container_width=True)
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reconectar API", use_container_width=True):
    st.cache_data.clear()
    if "datos_instalaciones" in st.session_state:
        del st.session_state["datos_instalaciones"]
    st.rerun()

st.sidebar.subheader("Periodo de Fechas")
opcion_periodo = st.sidebar.selectbox(
    "Seleccionar Rango",
    [
        "Este mes",
        "El mes pasado",
        "Últimos tres meses",
        "Últimos 6 meses",
        "Este año",
        "El año pasado",
    ],
    index=4,
)

if opcion_periodo == "Este mes":
    fecha_inicio = hoy.replace(day=1)
    fecha_fin = hoy
elif opcion_periodo == "El mes pasado":
    mes_anterior = hoy.replace(day=1) - pd.Timedelta(days=1)
    fecha_inicio = mes_anterior.replace(day=1)
    fecha_fin = mes_anterior
elif opcion_periodo == "Últimos tres meses":
    fecha_inicio = (pd.to_datetime(hoy) - pd.DateOffset(months=3)).date()
    fecha_fin = hoy
elif opcion_periodo == "Últimos 6 meses":
    fecha_inicio = (pd.to_datetime(hoy) - pd.DateOffset(months=6)).date()
    fecha_fin = hoy
elif opcion_periodo == "Este año":
    fecha_inicio = hoy.replace(month=1, day=1)
    fecha_fin = hoy
elif opcion_periodo == "El año pasado":
    fecha_inicio = hoy.replace(year=hoy.year - 1, month=1, day=1)
    fecha_fin = hoy.replace(year=hoy.year - 1, month=12, day=31)

st.sidebar.markdown("---")
st.sidebar.subheader("Polígonos")
lista_poligonos = (
    sorted(
        [
            str(p)
            for p in df_metas_valido["Poligono_de_instalacion"].dropna().unique()
        ],
        key=lambda x: int(x) if x.isdigit() else x,
    )
    if not df_metas_valido.empty
    else []
)

for p in lista_poligonos:
    if f"chk_pol_{p}" not in st.session_state:
        st.session_state[f"chk_pol_{p}"] = True

col_c1, col_c2 = st.sidebar.columns(2)
if col_c1.button("Marcar todos"):
    for p in lista_poligonos:
        st.session_state[f"chk_pol_{p}"] = True
if col_c2.button("Desmarcar"):
    for p in lista_poligonos:
        st.session_state[f"chk_pol_{p}"] = False

with st.sidebar.container(height=220):
    poligonos_seleccionados = [
        pol for pol in lista_poligonos if st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}")
    ]

df_metas_filtrado = (
    df_metas_valido[
        df_metas_valido["Poligono_de_instalacion"].astype(str).isin(poligonos_seleccionados)
    ].copy()
    if not df_metas_valido.empty
    else df_metas_valido.copy()
)

if col_fecha_ref and not df.empty and not df["fecha_dt"].isna().all():
    mask = (df["fecha_dt"].dt.date >= fecha_inicio) & (df["fecha_dt"].dt.date <= fecha_fin)
    df_filtrado = df.loc[mask].copy()
else:
    df_filtrado = df.copy()

meta_total = (
    int(df_metas["Usuarios_nueva_instalacion"].sum())
    if not df_metas.empty and "Usuarios_nueva_instalacion" in df_metas.columns
    else len(df_filtrado)
)
total_instalados = len(df_filtrado)
porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0

total_externo = (
    int(df_filtrado["usuarioExterno"].fillna(False).astype(bool).sum())
    if not df_filtrado.empty and "usuarioExterno" in df_filtrado.columns
    else 0
)
total_miaa = (
    int((~df_filtrado["usuarioExterno"].fillna(False).astype(bool)).sum())
    if not df_filtrado.empty and "usuarioExterno" in df_filtrado.columns
    else len(df_filtrado)
)

df_externo = (
    df_filtrado[df_filtrado["usuarioExterno"].fillna(False).astype(bool)].copy()
    if not df_filtrado.empty and "usuarioExterno" in df_filtrado.columns
    else pd.DataFrame()
)
df_miaa_pers = (
    df_filtrado[~df_filtrado["usuarioExterno"].fillna(False).astype(bool)].copy()
    if not df_filtrado.empty and "usuarioExterno" in df_filtrado.columns
    else df_filtrado.copy()
)

# ==============================================================================
# SECCIÓN 7: ESTRUCTURA DE PESTAÑAS (INCLUYENDO LA NUEVA PESTAÑA)
# ==============================================================================
(
    tab_principal,
    tab_hoy_inst,
    tab_poligonos,
    tab_personal,
    tab_anomalias,
    tab_tabla,
    tab_sheets_interno,
) = st.tabs([
    "📊 Dashboard Principal",
    "📍 Medidores Hoy",
    "🗺️ Mapa Polígonos",
    "👥 Personal (Externo y MIAA)",
    "⚠️ Análisis de Anomalías",
    "📋 Tabla Base de Datos Completa",
    "📑 Registro de instalaciones interno",
])

# ------------------------------------------------------------------------------
# PESTAÑA: DASHBOARD PRINCIPAL
# ------------------------------------------------------------------------------
with tab_principal:
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-bullseye"></i></div><div class="metric-content"><div class="metric-title">Meta Total</div><div class="metric-value">{meta_total:,}</div></div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-circle-check"></i></div><div class="metric-content"><div class="metric-title">Instalados</div><div class="metric-value">{total_instalados:,}</div></div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div><div class="metric-content"><div class="metric-title">Instalados Externo</div><div class="metric-value">{total_externo:,}</div></div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-building-user"></i></div><div class="metric-content"><div class="metric-title">Instalados MIAA</div><div class="metric-value">{total_miaa:,}</div></div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-chart-pie"></i></div><div class="metric-content"><div class="metric-title">% Avance</div><div class="metric-value">{porc_avance}%</div></div></div>', unsafe_allow_html=True)
    sin_coords = df_filtrado["latitud"].isna().sum() if not df_filtrado.empty and "latitud" in df_filtrado.columns else 0
    k6.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Sin Coordenadas</div><div class="metric-value">{sin_coords:,}</div></div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
    col_g1, col_g2, col_g3 = st.columns([2.6, 1.2, 0.9])

    with col_g1:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df_filtrado.empty and not df_filtrado["fecha_dt"].isna().all():
                df_filtrado["fecha_dia"] = df_filtrado["fecha_dt"].dt.date
                df_dia = df_filtrado.groupby("fecha_dia", as_index=False).size()
                df_dia["fecha_dia"] = pd.to_datetime(df_dia["fecha_dia"]).dt.strftime("%d/%m/%Y")
                fig_dia = px.bar(df_dia, x="fecha_dia", y="size", text="size", color_discrete_sequence=["#3b82f6"])
            else:
                fig_dia = px.bar(pd.DataFrame({"Aviso": ["Sin fechas"], "Valor": [0]}), x="Aviso", y="Valor", text="Valor")
            fig_dia.update_traces(textposition="outside", textfont_size=10)
            fig_dia.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#ffffff", margin=dict(t=25, b=5, l=5, r=5), height=230, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_dia, use_container_width=True, key="dash_prin_instalaciones_dia")

    with col_g2:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Tipo de Instalación</p>", unsafe_allow_html=True)
            if not df_filtrado.empty and "tipo_instalacion_nombre" in df_filtrado.columns:
                df_tipo_inst = df_filtrado["tipo_instalacion_nombre"].value_counts().reset_index()
                df_tipo_inst.columns = ["Tipo", "Cantidad"]
                fig_pie = go.Figure(go.Pie(labels=df_tipo_inst["Tipo"], values=df_tipo_inst["Cantidad"], hole=0.5, domain=dict(x=[0.0, 0.62], y=[0.05, 0.95]), textinfo="value+percent", marker=dict(colors=["#38bdf8", "#4ade80", "#f59e0b", "#a855f7", "#f43f5e", "#64748b"])))
            else:
                fig_pie = go.Figure(go.Pie(labels=["Sin Datos"], values=[len(df_filtrado)], hole=0.5))
            fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#ffffff", margin=dict(t=25, b=25, l=10, r=130), height=230, showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9)))
            st.plotly_chart(fig_pie, use_container_width=True, key="dash_prin_tipo_inst_pie")

    with col_g3:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Cuadro vs Registro</p>", unsafe_allow_html=True)
            if not df_filtrado.empty and "tipo_instalacion_nombre" in df_filtrado.columns:
                df_cr = df_filtrado.copy()
                df_cr["categoria_cr"] = df_cr["tipo_instalacion_nombre"].apply(lambda n: "CUADRO" if "CUADRO" in str(n).upper() else ("REGISTRO" if "REGISTRO" in str(n).upper() else None))
                df_cr_val = df_cr.dropna(subset=["categoria_cr"])
                if not df_cr_val.empty:
                    df_counts_cr = df_cr_val["categoria_cr"].value_counts().reset_index()
                    df_counts_cr.columns = ["Tipo", "Cantidad"]
                    tot_cr = df_counts_cr["Cantidad"].sum()
                    txt_centro = f"{tot_cr/1000:.1f} mil".replace(".", ",") if tot_cr >= 1000 else f"{tot_cr:,}"
                    fig_cr = go.Figure(go.Pie(labels=df_counts_cr["Tipo"], values=df_counts_cr["Cantidad"], hole=0.6, textinfo="value+percent", marker=dict(colors=["#0066cc", "#e83e8c"])))
                    fig_cr.update_layout(annotations=[dict(text=txt_centro, x=0.5, y=0.5, font_size=16, font_color="white", font_weight="bold", showarrow=False)], plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#ffffff", margin=dict(t=5, b=5, l=5, r=5), height=230, showlegend=True, legend=dict(orientation="h", y=-0.2, font=dict(size=9)))
                else:
                    fig_cr = go.Figure(go.Pie(labels=["Sin Datos"], values=[0], hole=0.6))
            else:
                fig_cr = go.Figure(go.Pie(labels=["Sin Datos"], values=[0], hole=0.6))
            st.plotly_chart(fig_cr, use_container_width=True, key="dash_prin_cuadro_vs_reg")

# ------------------------------------------------------------------------------
# NUEVA PESTAÑA: INSTALACIONES DEL DÍA EN CURSO CON RUTA Y MAPA
# ------------------------------------------------------------------------------
with tab_hoy_inst:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📍 Medidores Instalados del Día en Curso y Ruta de Trabajo</p>", unsafe_allow_html=True)
    
    if not df.empty and col_fecha_ref:
        max_fecha_reg = df["fecha_dt"].max()
        dia_actual_ref = pd.to_datetime(max_fecha_reg).date() if pd.notna(max_fecha_reg) else datetime.date.today()
        
        df_hoy_inst = df[df["fecha_dt"].dt.date == dia_actual_ref].copy()
        total_hoy_cant = len(df_hoy_inst)
        
        h_k1, h_k2, h_k3 = st.columns(3)
        h_k1.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-calendar-day"></i></div><div class="metric-content"><div class="metric-title">Instalados Hoy ({dia_actual_ref.strftime("%d/%m/%Y")})</div><div class="metric-value">{total_hoy_cant:,}</div></div></div>', unsafe_allow_html=True)
        colonias_hoy = df_hoy_inst["colonia"].nunique() if "colonia" in df_hoy_inst.columns else 0
        h_k2.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-map-location-dot"></i></div><div class="metric-content"><div class="metric-title">Colonias Atendidas Hoy</div><div class="metric-value">{colonias_hoy:,}</div></div></div>', unsafe_allow_html=True)
        anom_hoy = len(df_hoy_inst[df_hoy_inst["anomalia_nombre"] != "SIN ANOMALÍA / REGULAR"]) if "anomalia_nombre" in df_hoy_inst.columns else 0
        h_k3.markdown(f'<div class="metric-card"><div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="metric-content"><div class="metric-title">Anomalías Detectadas Hoy</div><div class="metric-value">{anom_hoy:,}</div></div></div>', unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        if not df_hoy_inst.empty:
            with st.container(border=True):
                st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:6px;'>🗺️ Mapa y Ruta de Instalación (Orden Horario)</p>", unsafe_allow_html=True)
                
                df_hoy_map = df_hoy_inst.dropna(subset=["latitud", "longitud"]).copy()
                if not df_hoy_map.empty:
                    df_hoy_map["_sort_dt"] = pd.to_datetime(df_hoy_map[col_fecha_ref], errors="coerce")
                    df_hoy_map = df_hoy_map.sort_values(by="_sort_dt", ascending=True)
                    
                    m_lat_h = df_hoy_map["latitud"].mean()
                    m_lon_h = df_hoy_map["longitud"].mean()
                else:
                    m_lat_h, m_lon_h = lat_centro, lon_centro
                
                mapa_hoy = folium.Map(location=[m_lat_h, m_lon_h], zoom_start=13, tiles=None)
                agregar_capas_base(mapa_hoy)
                
                puntos_ruta = []
                for _, row in df_hoy_map.iterrows():
                    lat_p = float(row["latitud"])
                    lon_p = float(row["longitud"])
                    puntos_ruta.append([lat_p, lon_p])
                    
                    nombre = str(row.get("nombreCliente", "N/A"))
                    serie = str(row.get("serieMedidor", row.get("serie", "N/A")))
                    hora_reg = str(row.get(col_fecha_ref, "N/A"))
                    
                    popup_html = f"<b>Cliente:</b> {nombre}<br><b>Serie:</b> {serie}<br><b>Hora/Fecha:</b> {hora_reg}"
                    folium.CircleMarker(
                        location=[lat_p, lon_p],
                        radius=4,
                        color="#38bdf8",
                        fill=True,
                        fill_color="#38bdf8",
                        fill_opacity=0.9,
                        popup=folium.Popup(popup_html, max_width=250),
                    ).add_to(mapa_hoy)
                
                if len(puntos_ruta) > 1:
                    AntPath(
                        locations=puntos_ruta,
                        delay=800,
                        dash_array=[10, 20],
                        weight=3,
                        color="#f59e0b",
                        pulse_color="#ffffff",
                        tooltip="Ruta de Instalación",
                    ).add_to(mapa_hoy)
                
                st_folium(mapa_hoy, width=None, height=400, key="mapa_ruta_hoy", returned_objects=[])

            with st.container(border=True):
                st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:6px;'>📋 Listado de Medidores Instalados Hoy</p>", unsafe_allow_html=True)
                busqueda_hoy = st.text_input("Buscar por Predio, Cliente o Serie (Hoy)", placeholder="Escribe para filtrar...", key="txt_busq_hoy")
                
                df_tabla_hoy = df_hoy_inst.copy()
                if busqueda_hoy:
                    b_txt = busqueda_hoy.lower()
                    mask_t = df_tabla_hoy.astype(str).apply(lambda r: r.str.lower().str.contains(b_txt).any(), axis=1)
                    df_tabla_hoy = df_tabla_hoy[mask_t]
                
                st.dataframe(df_tabla_hoy, use_container_width=True, height=300)
        else:
            st.info("No hay registros de instalaciones para el día en curso.")
    else:
        st.info("No hay datos disponibles.")

# ------------------------------------------------------------------------------
# PESTAÑA: ANÁLISIS DE ANOMALÍAS
# ------------------------------------------------------------------------------
with tab_anomalias:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>⚠️ Análisis Completo de Anomalías en Instalaciones</p>", unsafe_allow_html=True)
    df_con_anomalia = df_filtrado[df_filtrado["anomalia_nombre"] != "SIN ANOMALÍA / REGULAR"].copy() if not df_filtrado.empty and "anomalia_nombre" in df_filtrado.columns else pd.DataFrame()
    st.dataframe(df_con_anomalia, use_container_width=True, height=400)

# ------------------------------------------------------------------------------
# PESTAÑA: MAPA DE POLÍGONOS DE INSTALACIÓN
# ------------------------------------------------------------------------------
with tab_poligonos:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🗺️ Mapa de Polígonos y Avance</p>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PESTAÑA: PERSONAL (EXTERNO Y MIAA)
# ------------------------------------------------------------------------------
with tab_personal:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>👥 Resumen por Tipo de Personal</p>", unsafe_allow_html=True)
    sub_ext, sub_miaa_int = st.tabs(["👷 Personal Externo", "👤 Personal MIAA"])
    with sub_ext:
        st.dataframe(df_externo, use_container_width=True, height=350)
    with sub_miaa_int:
        st.dataframe(df_miaa_pers, use_container_width=True, height=350)

# ------------------------------------------------------------------------------
# PESTAÑA: TABLA BASE DE DATOS COMPLETA
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📋 Registros de la Tabla: usuarios_miaa_conmedidor</p>", unsafe_allow_html=True)
    df_usuarios_miaa_medidor = cargar_usuarios_miaa_conmedidor_db()
    if not df_usuarios_miaa_medidor.empty:
        df_usuarios_miaa_medidor = df_usuarios_miaa_medidor.loc[:, ~df_usuarios_miaa_medidor.columns.duplicated()]
    st.dataframe(df_usuarios_miaa_medidor, use_container_width=True, height=400)

# ------------------------------------------------------------------------------
# PESTAÑA: REGISTRO DE INSTALACIONES INTERNO (Google Sheets)
# ------------------------------------------------------------------------------
with tab_sheets_interno:
    st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📑 Registro de Instalaciones Interno (Google Sheets)</p>", unsafe_allow_html=True)
    st.dataframe(df_sheets_interno, use_container_width=True, height=400)
