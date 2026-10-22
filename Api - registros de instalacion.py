import datetime
import json
import math
import folium
from folium.plugins import Fullscreen
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

    .stTabs {
        margin-top: 5px;
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

# ==============================================================================
# SECCIÓN 2: FUNCIONES DE CONEXIÓN Y DATOS (API Y BASE DE DATOS)
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

        res_login = requests.post(
            url_login, json=payload, headers=headers, timeout=15
        )

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
        
        query = """
            SELECT *, 
                   ST_AsText(geom) as geom,
                   ST_X(geom) as utm_x, 
                   ST_Y(geom) as utm_y 
            FROM "Usuarios"."usuarios_miaa_conmedidor"
            WHERE etapa::text IN ('1', '2', 'etapa 1', 'etapa 2')
        """
        return pd.read_sql(query, con=engine)
    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        try:
            cfg = st.secrets["postgres"]
            conn_str = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
            engine = create_engine(conn_str)
            query = """
                SELECT *, 
                       ST_AsText(geom) as geom,
                       ST_X(geom) as utm_x, 
                       ST_Y(geom) as utm_y 
                FROM usuarios_miaa_conmedidor
                WHERE etapa::text IN ('1', '2', 'etapa 1', 'etapa 2')
            """
            return pd.read_sql(query, con=engine)
        except Exception as ex:
            print(f"Error en respaldo de conexión: {ex}")
            return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_todas_las_colonias():
    query = """
        SELECT ST_AsText(geom) as geom_wkt, Pozos, Col_atl, Sector, Distrito, Supervisor,
               Pozo_1, Afectacion_1, Pozo_2, Afectacion_2, 
               Pozo_3, Afectacion_3, Pozo_4, Afectacion_4, 
               Pozo_5, Afectacion_5, Pozo_6, Afectacion_6, 
               Pozo_7, Afectacion_7, Pozo_8, Afectacion_8, 
               Pozo_9, Afectacion_9, Pozo_10, Afectacion_10 
        FROM Diccionario_colonias
    """
    try:
        df = pd.read_sql(query, get_mysql_telemetria_engine())
        if not df.empty and df['geom_wkt'].iloc[0] is not None:
            df['geometry'] = df['geom_wkt'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            gdf.set_crs(epsg=32613, inplace=True)
            return gdf.to_crs(epsg=4326)
    except Exception as e:
        st.error(f"Error cargando polígonos: {e}")
    return None


# ==============================================================================
# SECCIÓN 3: FUNCIONES AUXILIARES PARA MAPAS
# ==============================================================================


def agregar_capas_base(m):
    api_key = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        max_zoom=19,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Satélite con Calles",
        max_zoom=20,
    ).add_to(m)

    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key}",
        name="Vista Nocturna",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains="abcd",
        max_zoom=20,
    ).add_to(m)

    folium.LayerControl(position="topleft").add_to(m)

    Fullscreen(
        position="topright",
        title="Ampliar Mapa",
        cancel_title="Salir de pantalla completa",
    ).add_to(m)

    # ==============================================================================
    # INYECCIÓN DE CSS PARA OCULTAR LA BARRA DE ATRIBUCIÓN Y ESTILIZAR POPUPS
    # ==============================================================================
    css_quitar_atribucion = """
    <style>
        /* Oculta la barra de texto de atribución de Leaflet en la esquina inferior izquierda */
        .leaflet-control-attribution {
            display: none !important;
        }
        /* Estilo coherente para los popups en modo oscuro */
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css_quitar_atribucion))


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
        df = (
            pd.DataFrame(lista_registros)
            if lista_registros
            else pd.DataFrame([data])
        )
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

# Garantizar campos para seguimiento por usuario y tipo de personal
if not df.empty:
    if "usuarioNombre" not in df.columns:
        df["usuarioNombre"] = "NO ESPECIFICADO"
    else:
        df["usuarioNombre"] = df["usuarioNombre"].fillna("NO ESPECIFICADO").astype(str).str.strip().str.upper()

    if "usuarioExterno" not in df.columns:
        df["usuarioExterno"] = False
    else:
        df["usuarioExterno"] = df["usuarioExterno"].fillna(False).astype(bool)

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

# ==============================================================================
# SECCION 4.1 CREACIÓN Y FORMATEO DE LA COLUMNA PREDIO_VIV (PREDIO + UNIDAD)
# ==============================================================================
col_p_orig = next((c for c in ["predio", "numeroPredio"] if c in df.columns), None)
col_u_orig = next((c for c in ["unidad", "numeroUnidad"] if c in df.columns), None)

def formatear_predio(row):
    val_p = str(row[col_p_orig]).strip() if col_p_orig and pd.notna(row[col_p_orig]) else "0"
    val_p = val_p.split(".")[0] if val_p.endswith(".0") else val_p
    if val_p in ["nan", "None", "", "nat"]: 
        val_p = "0"
    
    if col_u_orig and col_u_orig in row and pd.notna(row[col_u_orig]):
        val_u = str(row[col_u_orig]).strip()
        val_u = val_u.split(".")[0] if val_u.endswith(".0") else val_u
        if val_u in ["nan", "None", "", "nat"]: 
            val_u = "0"
    else:
        val_u = "0"
    
    return f"{val_p}-{val_u}"

if not df.empty and col_p_orig:
    df["predio_viv"] = df.apply(formatear_predio, axis=1)
elif not df.empty:
    df["predio_viv"] = "0-0"

df_metas = cargar_metas_db()
df_poligonos = cargar_poligonos_db()
df_anomalias_db = cargar_anomalias_db()
df_sheets_interno = cargar_google_sheets_interno()

df_tipos_db = cargar_tipos_instalacion_db()
if not df_tipos_db.empty:
    dict_tipos_map = dict(
        zip(df_tipos_db["ID"].astype(str), df_tipos_db["tipo_instalacion"])
    )
else:
    dict_tipos_map = {
        "1": "CAJA DE VALVULAS",
        "2": "CUADRO DENTRO",
        "3": "CUADRO FUERA",
        "4": "REGISTRO",
        "5": "EMPOTRADO DENTRO",
        "6": "EMPOTRADO FUERA",
    }

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

if not df_anomalias_db.empty:
    dict_anomalias_map = dict(
        zip(df_anomalias_db["ID"].astype(str), df_anomalias_db["anomalia"])
    )
else:
    dict_anomalias_map = {}

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
# SECCIÓN 5: CABECERA SUPERIOR DEL TÍTULO DE LA PÁGINA
# ==============================================================================

try:
    if not df.empty and "fecha_dt" in df.columns:
        max_dt = df["fecha_dt"].max()
        if pd.notna(max_dt):
            hoy = pd.to_datetime(max_dt).date()
        else:
            hoy = datetime.date.today()
    else:
        hoy = datetime.date.today()
except Exception:
    hoy = datetime.date.today()

try:
    fecha_actual_str = pd.to_datetime(hoy).strftime("%d/%m/%Y")
except Exception:
    fecha_actual_str = datetime.date.today().strftime("%d/%m/%Y")

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px;">
        <div style="width: 180px;"></div>
        <div style="flex-grow: 1; text-align: center;">
            <h1 style="color: white; font-size: 26px; margin: 0; font-weight: bold;">DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</h1>
        </div>
        <div style="width: 180px; text-align: right; color: #a0a0a0; font-size: 14px;">
            Actualizado al: {fecha_actual_str}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# SECCIÓN 6: BARRA LATERAL (FILTROS Y CONTROLES)
# ==============================================================================

logo_url = "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg"
st.sidebar.image(logo_url, use_container_width=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Estado de Conexión API")

if st.sidebar.button("🔄 Reconectar API", use_container_width=True):
    st.cache_data.clear()
    if "datos_instalaciones" in st.session_state:
        del st.session_state["datos_instalaciones"]
    res = cargar_datos_api()
    if res:
        st.session_state["datos_instalaciones"] = res
    st.rerun()

api_conectada = (
    "datos_instalaciones" in st.session_state
    and st.session_state["datos_instalaciones"] is not None
)

if api_conectada:
    st.sidebar.success("API Conectada Correctamente", icon="🟢")
else:
    st.sidebar.error("Error de Conexión con la API", icon="🔴")

st.sidebar.markdown("---")
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

if not df.empty and "fecha_dt" in df.columns and not df["fecha_dt"].isna().all():
    hoy = df["fecha_dt"].max().date()
else:
    hoy = datetime.date.today()

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

lista_poligonos = []
if not df_metas_valido.empty and "Poligono_de_instalacion" in df_metas_valido.columns:
    lista_poligonos = sorted(
        [str(p) for p in df_metas_valido["Poligono_de_instalacion"].dropna().unique()],
        key=lambda x: int(x) if x.isdigit() else x,
    )

for p in lista_poligonos:
    if f"chk_pol_{p}" not in st.session_state:
        st.session_state[f"chk_pol_{p}"] = True

col_c1, col_c2 = st.sidebar.columns(2)
seleccionar_todos = col_c1.button("Marcar todos")
deseleccionar_todos = col_c2.button("Desmarcar")

if seleccionar_todos:
    for p in lista_poligonos:
        st.session_state[f"chk_pol_{p}"] = True

if deseleccionar_todos:
    for p in lista_poligonos:
        st.session_state[f"chk_pol_{p}"] = False

with st.sidebar.container(height=220):
    poligonos_seleccionados = []
    for pol in lista_poligonos:
        estado = st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}")
        if estado:
            poligonos_seleccionados.append(pol)

if not df_metas_valido.empty and "Poligono_de_instalacion" in df_metas_valido.columns:
    df_metas_filtrado = df_metas_valido[
        df_metas_valido["Poligono_de_instalacion"]
        .astype(str)
        .isin(poligonos_seleccionados)
    ].copy()
else:
    df_metas_filtrado = df_metas_valido.copy()

if col_fecha_ref and not df.empty and not df["fecha_dt"].isna().all():
    mask = (df["fecha_dt"].dt.date >= fecha_inicio) & (
        df["fecha_dt"].dt.date <= fecha_fin
    )
    df_filtrado = df.loc[mask].copy()
else:
    df_filtrado = df.copy()

meta_total = (
    int(df_metas["Usuarios_nueva_instalacion"].sum())
    if not df_metas.empty and "Usuarios_nueva_instalacion" in df_metas.columns
    else len(df_filtrado)
)
total_instalados = len(df_filtrado)
porc_avance = (
    round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0
)

if not df_filtrado.empty and "usuarioExterno" in df_filtrado.columns:
    total_externo = int(
        df_filtrado["usuarioExterno"].fillna(False).astype(bool).sum()
    )
    total_miaa = int(
        (~df_filtrado["usuarioExterno"].fillna(False).astype(bool)).sum()
    )

    df_externo = df_filtrado[
        df_filtrado["usuarioExterno"].fillna(False).astype(bool)
    ].copy()
    df_miaa_pers = df_filtrado[
        ~df_filtrado["usuarioExterno"].fillna(False).astype(bool)
    ].copy()
else:
    total_externo = 0
    total_miaa = len(df_filtrado)
    df_externo = pd.DataFrame(
        columns=df_filtrado.columns if not df_filtrado.empty else []
    )
    df_miaa_pers = df_filtrado.copy()

if not df_metas_filtrado.empty:
    df_tabla_eficiencia = df_metas_filtrado.copy()

    df_eficiencia = df_tabla_eficiencia.groupby(
        ["Colonia_ATL", "Poligono_de_instalacion"], as_index=False
    ).agg({"Usuarios_nueva_instalacion": "sum"})

    df_eficiencia["colonia_key"] = (
        df_eficiencia["Colonia_ATL"].astype(str).str.strip().str.upper()
    )

    if not df_filtrado.empty and "colonia" in df_filtrado.columns:
        df_api_colonia = df_filtrado.copy()
        df_api_colonia["colonia_key"] = (
            df_api_colonia["colonia"].astype(str).str.strip().str.upper()
        )
        conteo_api_colonia = (
            df_api_colonia.groupby("colonia_key", as_index=False)
            .size()
            .rename(columns={"size": "Med_Instalados_API"})
        )
    else:
        conteo_api_colonia = pd.DataFrame(
            columns=["colonia_key", "Med_Instalados_API"]
        )

    df_eficiencia = pd.merge(
        df_eficiencia, conteo_api_colonia, on="colonia_key", how="left"
    )
    df_eficiencia["Med_Instalados_API"] = (
        df_eficiencia["Med_Instalados_API"].fillna(0).astype(int)
    )

    df_eficiencia["pct_sort"] = np.where(
        df_eficiencia["Usuarios_nueva_instalacion"] > 0,
        (
            df_eficiencia["Med_Instalados_API"]
            / df_eficiencia["Usuarios_nueva_instalacion"]
        )
        * 100,
        0.0,
    )

    df_eficiencia = df_eficiencia.sort_values(
        by="pct_sort", ascending=False
    ).reset_index(drop=True)
    df_eficiencia["%"] = df_eficiencia["pct_sort"].round(2).astype(str) + "%"

    df_eficiencia = df_eficiencia.rename(
        columns={
            "Colonia_ATL": "Colonia",
            "Usuarios_nueva_instalacion": "Med. a instalar",
            "Med_Instalados_API": "Med. instalados",
            "Poligono_de_instalacion": "Polígono",
        }
    )

    df_eficiencia = df_eficiencia[
        ["Colonia", "Med. a instalar", "Med. instalados", "%", "Polígono"]
    ]
else:
    df_eficiencia = pd.DataFrame(
        columns=["Colonia", "Med. a instalar", "Med. instalados", "%", "Polígono"]
    )

# ==============================================================================
# SECCIÓN 7: ESTRUCTURA DE PESTAÑAS PRINCIPALES
# ==============================================================================

(
    tab_principal,
    tab_rutas_diarias,
    tab_poligonos,
    tab_personal,
    tab_anomalias,
    tab_tabla,
    tab_sheets_interno,
) = st.tabs([
    "📊 Dashboard Principal",
    "🛣️ Seguimiento Diario por Usuario / Ruta",
    "🗺️ Mapa Polígonos",
    "👥 Personal (Externo y MIAA)",
    "⚠️ Análisis de Anomalías",
    "📋 Tabla Base de Datos Completa",
    "📑 Registro de instalaciones interno",
])

# ------------------------------------------------------------------------------
# SECCIÓN 8 PESTAÑA: DASHBOARD PRINCIPAL
# ------------------------------------------------------------------------------
with tab_principal:
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-bullseye"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Meta Total</div>
                        <div class="metric-value">{meta_total:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-circle-check"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados</div>
                        <div class="metric-value">{total_instalados:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados Externo</div>
                        <div class="metric-value">{total_externo:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-building-user"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados MIAA</div>
                        <div class="metric-value">{total_miaa:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    with k5:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-chart-pie"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">% Avance</div>
                        <div class="metric-value">{porc_avance}%</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    with k6:
        sin_coords = (
            df_filtrado["latitud"].isna().sum()
            if not df_filtrado.empty and "latitud" in df_filtrado.columns
            else 0
        )
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{sin_coords:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    col_g1, col_g2, col_g3 = st.columns([2.6, 1.2, 0.9])

    with col_g1:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día</p>",
                unsafe_allow_html=True,
            )
            if (
                col_fecha_ref
                and not df_filtrado.empty
                and not df_filtrado["fecha_dt"].isna().all()
            ):
                df_filtrado["fecha_dia"] = df_filtrado["fecha_dt"].dt.date
                df_dia = df_filtrado.groupby("fecha_dia", as_index=False).size()
                df_dia["fecha_dia"] = pd.to_datetime(df_dia["fecha_dia"]).dt.strftime(
                    "%d/%m/%Y"
                )
                fig_dia = px.bar(
                    df_dia,
                    x="fecha_dia",
                    y="size",
                    text="size",
                    color_discrete_sequence=["#3b82f6"],
                )
            else:
                fig_dia = px.bar(
                    pd.DataFrame({"Aviso": ["Sin fechas"], "Valor": [0]}),
                    x="Aviso",
                    y="Valor",
                    text="Valor",
                )

            fig_dia.update_traces(textposition="outside", textfont_size=10)
            fig_dia.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff",
                margin=dict(t=25, b=5, l=5, r=5),
                height=230,
                xaxis_title=None,
                yaxis_title=None,
                yaxis=dict(range=[0, 500]),
            )
            st.plotly_chart(
                fig_dia, use_container_width=True, key="dash_prin_instalaciones_dia"
            )

    with col_g2:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Tipo de Instalación</p>",
                unsafe_allow_html=True,
            )
            if not df_filtrado.empty and "tipo_instalacion_nombre" in df_filtrado.columns:
                df_tipo_inst = (
                    df_filtrado["tipo_instalacion_nombre"].value_counts().reset_index()
                )
                df_tipo_inst.columns = ["Tipo", "Cantidad"]

                colores_pie = [
                    "#38bdf8",
                    "#4ade80",
                    "#f59e0b",
                    "#a855f7",
                    "#f43f5e",
                    "#64748b",
                ]

                fig_pie = go.Figure(
                    go.Pie(
                        labels=df_tipo_inst["Tipo"],
                        values=df_tipo_inst["Cantidad"],
                        hole=0.5,
                        domain=dict(x=[0.0, 0.62], y=[0.05, 0.95]),
                        textinfo="value+percent",
                        texttemplate="%{value} (%{percent})",
                        textposition="outside",
                        textfont=dict(color="#ffffff", size=9),
                        marker=dict(colors=colores_pie),
                        hovertemplate=(
                            "<b>%{label}</b><br>Cantidad: %{value:,}<br>Porcentaje:"
                            " %{percent}<extra></extra>"
                        ),
                    )
                )
            else:
                fig_pie = go.Figure(
                    go.Pie(labels=["Sin Datos"], values=[len(df_filtrado)], hole=0.5)
                )

            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff",
                margin=dict(t=25, b=25, l=10, r=130),
                height=230,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=9),
                ),
            )
            st.plotly_chart(
                fig_pie, use_container_width=True, key="dash_prin_tipo_inst_pie"
            )

    with col_g3:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Cuadro vs Registro</p>",
                unsafe_allow_html=True,
            )
            if not df_filtrado.empty and "tipo_instalacion_nombre" in df_filtrado.columns:

                def clasificar_cuadro_registro(nombre):
                    n_str = str(nombre).upper()
                    if "CUADRO" in n_str:
                        return "CUADRO"
                    elif "REGISTRO" in n_str:
                        return "REGISTRO"
                    return None

                df_cr = df_filtrado.copy()
                df_cr["categoria_cr"] = df_cr["tipo_instalacion_nombre"].apply(
                    clasificar_cuadro_registro
                )
                df_cr_val = df_cr.dropna(subset=["categoria_cr"])

                if not df_cr_val.empty:
                    df_counts_cr = (
                        df_cr_val["categoria_cr"].value_counts().reset_index()
                    )
                    df_counts_cr.columns = ["Tipo", "Cantidad"]

                    tot_cr = df_counts_cr["Cantidad"].sum()
                    txt_centro = (
                        f"{tot_cr/1000:.1f} mil".replace(".", ",")
                        if tot_cr >= 1000
                        else f"{tot_cr:,}"
                    )

                    color_cr_map = {"CUADRO": "#0066cc", "REGISTRO": "#e83e8c"}
                    colores_cr = [
                        color_cr_map.get(t, "#3b82f6") for t in df_counts_cr["Tipo"]
                    ]

                    fig_cr = go.Figure(
                        go.Pie(
                            labels=df_counts_cr["Tipo"],
                            values=df_counts_cr["Cantidad"],
                            hole=0.6,
                            textinfo="value+percent",
                            marker=dict(colors=colores_cr),
                        )
                    )

                    fig_cr.update_layout(
                        annotations=[
                            dict(
                                text=txt_centro,
                                x=0.5,
                                y=0.5,
                                font_size=16,
                                font_color="white",
                                font_weight="bold",
                                showarrow=False,
                            )
                        ],
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#ffffff",
                        margin=dict(t=5, b=5, l=5, r=5),
                        height=230,
                        showlegend=True,
                        legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
                    )
                else:
                    fig_cr = go.Figure(
                        go.Pie(labels=["Sin Datos"], values=[0], hole=0.6)
                    )
                    fig_cr.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#ffffff",
                        height=230,
                    )
            else:
                fig_cr = go.Figure(go.Pie(labels=["Sin Datos"], values=[0], hole=0.6))
                fig_cr.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    height=230,
                )

            st.plotly_chart(
                fig_cr, use_container_width=True, key="dash_prin_cuadro_vs_reg"
            )

    col_inf1, col_inf2 = st.columns([1, 1.6])

    with col_inf1:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Eficiencia por Colonia y Polígono</p>",
                unsafe_allow_html=True,
            )
            if not df_eficiencia.empty:
                st.dataframe(
                    df_eficiencia, use_container_width=True, hide_index=True, height=330
                )
            else:
                st.info("No se encontraron datos para los polígonos seleccionados.")

    # ==============================================================================
    # SECCIÓN 9: LISTADO GENERAL DE INSTALACIONES (BUSCADOR ARRIBA PARA QUE EL MAPA LO LEA)
    # ==============================================================================
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "<p style='font-size:14px; font-weight:bold; margin-bottom:6px;'>📍 Listado General de Instalaciones de Medidores</p>",
            unsafe_allow_html=True,
        )

        if not df.empty:
            df_todos_inst = df_filtrado.copy()

            col_p_orig = next((c for c in ["predio", "numeroPredio"] if c in df_todos_inst.columns), None)
            col_u_orig = next((c for c in ["unidad", "numeroUnidad"] if c in df_todos_inst.columns), None)

            def formatear_predio_tabla(row):
                val_p = str(row[col_p_orig]).strip() if col_p_orig and pd.notna(row[col_p_orig]) else "0"
                val_p = val_p.split(".")[0] if val_p.endswith(".0") else val_p
                if val_p in ["nan", "None", "", "nat"]: val_p = "0"
                
                if col_u_orig and col_u_orig in row and pd.notna(row[col_u_orig]):
                    val_u = str(row[col_u_orig]).strip()
                    val_u = val_u.split(".")[0] if val_u.endswith(".0") else val_u
                    if val_u in ["nan", "None", "", "nat"]: 
                        val_u = "0"
                else:
                    val_u = "0"
                
                if val_u != "0" and val_u != "":
                    return f"{val_p}-{val_u}"
                else:
                    return f"{val_p}-0"

            if col_p_orig and "predio_viv" not in df_todos_inst.columns:
                df_todos_inst["predio_viv"] = df_todos_inst.apply(formatear_predio_tabla, axis=1)

            col_cli_orig = next((c for c in ["numeroCliente", "cliente"] if c in df_todos_inst.columns), None)
            if col_cli_orig:
                df_todos_inst["Num_Cliente"] = df_todos_inst[col_cli_orig].astype(str).str.replace(r"\.0$", "", regex=True)
                df_todos_inst["Num_Cliente"] = df_todos_inst["Num_Cliente"].replace(["nan", "None", "", "nat"], "0")
            else:
                df_todos_inst["Num_Cliente"] = "0"

            # BARRA DE BÚSQUEDA
            busqueda_global_inst = st.text_input(
                "Buscar en cualquier registro (Predio, Cliente, Serie, Domicilio, etc.)",
                placeholder="Ej. 502934-1, VAZQUEZ, 222608...",
                key="filtro_texto_global_inst",
            )

            df_filtrado_global = df_todos_inst.copy()
            if busqueda_global_inst:
                b_txt = busqueda_global_inst.lower()
                mask_txt = df_filtrado_global.astype(str).apply(
                    lambda row: row.str.lower().str.contains(b_txt).any(), axis=1
                )
                df_filtrado_global = df_filtrado_global[mask_txt]
        else:
            df_filtrado_global = pd.DataFrame()

    with col_inf2:
        col_map_h, col_graf_h = st.columns([2.2, 1])

        with col_map_h:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones (Externo vs MIAA)</p>",
                    unsafe_allow_html=True,
                )

                # EL MAPA AHORA SÍ LEE EL FILTRADO GLOBAL QUE ESTÁ ARRIBA
                df_fuente_mapa = df_filtrado_global if not df_filtrado_global.empty else df_filtrado

                df_mapa_valido = (
                    df_fuente_mapa.dropna(subset=["latitud", "longitud"])
                    if not df_fuente_mapa.empty
                    else pd.DataFrame()
                )
                if not df_mapa_valido.empty:
                    map_lat = df_mapa_valido["latitud"].mean()
                    map_lon = df_mapa_valido["longitud"].mean()
                else:
                    map_lat, map_lon = lat_centro, lon_centro

                mapa_miaa = folium.Map(
                    location=[map_lat, map_lon], zoom_start=12, tiles=None
                )
                agregar_capas_base(mapa_miaa)

                for _, row in df_mapa_valido.iterrows():
                    es_externo = (
                        bool(row["usuarioExterno"])
                        if "usuarioExterno" in df_mapa_valido.columns
                        else False
                    )
                    color_punto = "#f59e0b" if es_externo else "#a855f7"

                    def get_clean(keys, default=""):
                        if isinstance(keys, str):
                            keys = [keys]
                        for k in keys:
                            if k in row:
                                val = row[k]
                                if (
                                    pd.notna(val)
                                    and str(val).strip().lower()
                                    not in [
                                        "nan",
                                        "none",
                                        "nat",
                                        "",
                                    ]
                                ):
                                    return str(val).strip()
                        return default

                    nombre = get_clean("nombreCliente")
                    
                    predio = row.get("predio_viv", get_clean(["numeroPredio", "predio"]))
                    if pd.isna(predio) or str(predio).strip() in ["nan", "None", "", "nat"]:
                        predio = get_clean(["numeroPredio", "predio"])

                    raw_cliente = get_clean(["cliente", "numeroCliente"])
                    if pd.notna(raw_cliente) and str(raw_cliente).strip() not in ["nan", "None", "", "nat"]:
                        cliente = str(raw_cliente).split(".")[0]
                    else:
                        cliente = "N/A"

                    domicilio = get_clean("domicilio")
                    colonia = get_clean("colonia")
                    nivel = get_clean("nivel")
                    giro = get_clean("giro")
                    serie = get_clean(["serieMedidor", "serie"])
                    lugar_inst = get_clean(
                        ["tipo_instalacion_nombre", "lugarInstalacion"]
                    )
                    anomalia_str = get_clean(["anomalia_nombre"])

                    raw_fecha = row.get("fechaInstalacion", None)
                    fecha_inst = ""
                    if (
                        pd.notna(raw_fecha)
                        and str(raw_fecha).strip().lower()
                        not in [
                            "nan",
                            "none",
                            "nat",
                            "",
                        ]
                    ):
                        dt_obj = pd.to_datetime(raw_fecha, errors="coerce")
                        if pd.notna(dt_obj):
                            fecha_inst = dt_obj.strftime("%d/%m/%Y")
                        else:
                            fecha_inst = str(raw_fecha).strip()

                    raw_hora = row.get("horaInicio", None)
                    hora_inst = ""
                    if (
                        pd.notna(raw_hora)
                        and str(raw_hora).strip().lower()
                        not in [
                            "nan",
                            "none",
                            "nat",
                            "",
                        ]
                    ):
                        hora_str = str(raw_hora).strip()
                        if "T" in hora_str:
                            time_part = hora_str.split("T")[1]
                            hora_inst = time_part[:5]
                        elif " " in hora_str:
                            time_part = hora_str.split(" ")[1]
                            hora_inst = time_part[:5]
                        else:
                            hora_inst = hora_str[:5]

                    info_popup = f"""
                    <div style="font-size: 11px; line-height: 1.4; color: #000000;">
                        <b>Información del Servicio</b><br>
                        <b>Nombre:</b> {nombre}<br>
                        <b>Número de Predio:</b> {predio}<br>
                        <b>Cliente:</b> {cliente}<br>
                        <b>Domicilio:</b> {domicilio}<br>
                        <b>Colonia:</b> {colonia}<br>
                        <b>Nivel:</b> {nivel}<br>
                        <b>Giro:</b> {giro}<br>
                        <b>Serie del Medidor:</b> {serie}<br>
                        <b>Fecha de Instalación:</b> {fecha_inst}<br>
                        <b>Hora de Instalación:</b> {hora_inst}<br>
                        <b>Lugar de Instalación:</b> {lugar_inst}<br>
                        <b>Anomalía:</b> {anomalia_str}
                    </div>
                    """

                    popup_obj = folium.Popup(info_popup, max_width=300)

                    folium.CircleMarker(
                        location=[float(row["latitud"]), float(row["longitud"])],
                        radius=2.5,
                        color=color_punto,
                        fill=True,
                        fill_color=color_punto,
                        fill_opacity=0.7,
                        popup=popup_obj,
                    ).add_to(mapa_miaa)

                st_folium(
                    mapa_miaa,
                    width=None,
                    height=320,
                    key="mapa_estatico_instalaciones",
                    returned_objects=[],
                )

        with col_graf_h:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Mes</p>",
                    unsafe_allow_html=True,
                )

                if (
                    col_fecha_ref
                    and not df.empty
                    and not df["fecha_dt"].isna().all()
                ):
                    df_mes_total = df.copy()
                    df_mes_total["periodo_mes"] = df_mes_total["fecha_dt"].dt.to_period(
                        "M"
                    )
                    df_mes = (
                        df_mes_total.groupby("periodo_mes", as_index=False).size()
                    )
                    df_mes.columns = ["Periodo", "Cantidad"]

                    meses_es = {
                        1: "Enero",
                        2: "Febrero",
                        3: "Marzo",
                        4: "Abril",
                        5: "Mayo",
                        6: "Junio",
                        7: "Julio",
                        8: "Agosto",
                        9: "Septiembre",
                        10: "Octubre",
                        11: "Noviembre",
                        12: "Diciembre",
                    }

                    df_mes["Mes"] = df_mes["Periodo"].apply(
                        lambda x: f"{meses_es[x.month]} {x.year}"
                    )
                    df_mes = df_mes.sort_values(by="Periodo", ascending=True)
                else:
                    df_mes = pd.DataFrame({"Mes": ["Sin datos"], "Cantidad": [0]})

                colores_barras = ["#1e3a8a", "#3b82f6"] * ((len(df_mes) // 2) + 1)
                max_cant = df_mes["Cantidad"].max() if not df_mes.empty else 10

                fig_mes_h = px.bar(
                    df_mes,
                    x="Cantidad",
                    y="Mes",
                    orientation="h",
                    text="Cantidad",
                    color="Mes",
                    color_discrete_sequence=colores_barras,
                )

                fig_mes_h.update_traces(textposition="outside", textfont_size=10)
                fig_mes_h.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=2, b=2, l=5, r=40),
                    height=130,
                    xaxis=dict(
                        showgrid=False,
                        showticklabels=False,
                        title=None,
                        range=[0, max_cant * 1.25],
                    ),
                    yaxis=dict(
                        showgrid=False,
                        title=None,
                        tickfont=dict(size=10),
                        categoryorder="array",
                        categoryarray=df_mes["Mes"].tolist(),
                    ),
                    showlegend=False,
                )
                st.plotly_chart(
                    fig_mes_h, use_container_width=True, key="dash_prin_instalaciones_mes"
                )

            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:8px; font-weight:bold;'>Total de Anomalías</p>",
                    unsafe_allow_html=True,
                )
                total_anomalias_actual = (
                    len(
                        df_filtrado[
                            df_filtrado["anomalia_nombre"] != "SIN ANOMALÍA / REGULAR"
                        ]
                    )
                    if not df_filtrado.empty and "anomalia_nombre" in df_filtrado.columns
                    else 0
                )

                st.markdown(
                    f"""
                            <div style="display: flex; align-items: center; justify-content: center; gap: 20px; padding: 32px 0;">
                                <div style="font-size: 38px; color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                                <div style="font-size: 36px; font-weight: bold; color: #ffffff;">{total_anomalias_actual:,}</div>
                            </div>
                        """,
                    unsafe_allow_html=True,
                )

    # ==============================================================================
    # SECCIÓN 9.1 (CONT.) RENDERIZADO DE LA TABLA PAGINADA ABAJO
    # ==============================================================================
    with st.container(border=True):
        total_registros_filtrados = len(df_filtrado_global)

        if total_registros_filtrados > 0:
            TAMANO_PAGINA = 10
            total_paginas = math.ceil(total_registros_filtrados / TAMANO_PAGINA)

            col_pag1, col_pag2 = st.columns([2, 1])
            with col_pag1:
                pagina_actual = st.selectbox(
                    f"Seleccionar Hoja / Página (Total registros: {total_registros_filtrados:,})",
                    options=list(range(1, total_paginas + 1)),
                    format_func=lambda x: f"Hoja {x} de {total_paginas} (Registros {(x-1)*TAMANO_PAGINA + 1} al {min(x*TAMANO_PAGINA, total_registros_filtrados)})",
                    key="select_pagina_registros",
                )
            with col_pag2:
                st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: #38bdf8; font-weight: bold;'>Mostrando 10 por hoja</div>", unsafe_allow_html=True)

            inicio_idx = (pagina_actual - 1) * TAMANO_PAGINA
            fin_idx = inicio_idx + TAMANO_PAGINA
            df_pagina_actual = df_filtrado_global.iloc[inicio_idx:fin_idx].copy()

            if "usuarioExterno" in df_pagina_actual.columns:
                df_pagina_actual["Instalador"] = np.where(
                    df_pagina_actual["usuarioExterno"].fillna(False).astype(bool),
                    "Externo",
                    "MIAA",
                )
            else:
                df_pagina_actual["Instalador"] = "MIAA"

            cols_mostrar = []
            candidatos_cols = [
                "nombreCliente",
                "predio_viv",
                "Num_Cliente",
                "domicilio",
                "colonia",
                "serie",
                "serieMedidor",
                "tipo_instalacion_nombre",
                "Instalador",
                "anomalia_nombre",
                "fechaRegistro",
            ]
            for c in candidatos_cols:
                if c in df_pagina_actual.columns and c not in cols_mostrar:
                    cols_mostrar.append(c)

            df_tabla_final_hoja = df_pagina_actual[cols_mostrar].copy()

            if "fechaRegistro" in df_tabla_final_hoja.columns:
                df_tabla_final_hoja["fechaRegistro"] = pd.to_datetime(
                    df_tabla_final_hoja["fechaRegistro"], errors="coerce"
                ).dt.strftime("%d/%m/%Y %H:%M:%S")

            st.dataframe(
                df_tabla_final_hoja, use_container_width=True, hide_index=True
            )
        else:
            st.info("No se encontraron registros que coincidan con la búsqueda.")

# ------------------------------------------------------------------------------
# SECCIÓN 9.2 PESTAÑA: SEGUIMIENTO DIARIO DE RUTAS E INSTALADORES
# ------------------------------------------------------------------------------
with tab_rutas_diarias:
    st.markdown(
        "<p style='font-size:16px; font-weight:bold; margin-bottom:5px;'>🛣️ Seguimiento Diario de Rutas e Instalaciones por Personal</p>",
        unsafe_allow_html=True,
    )

    if not df.empty and "fecha_dt" in df.columns and not df["fecha_dt"].isna().all():
        df_rutas_base = df.dropna(subset=["fecha_dt"]).copy()
        fechas_disponibles_rutas = sorted(df_rutas_base["fecha_dt"].dt.date.unique(), reverse=True)
        max_fecha_ruta = fechas_disponibles_rutas[0] if fechas_disponibles_rutas else datetime.date.today()
    else:
        df_rutas_base = pd.DataFrame()
        fechas_disponibles_rutas = [datetime.date.today()]
        max_fecha_ruta = datetime.date.today()

    with st.container(border=True):
        st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:8px;'>🔍 Filtros de Fecha y Tipo de Personal</p>", unsafe_allow_html=True)
        col_r1, col_r2 = st.columns([1.2, 1])

        with col_r1:
            fecha_sel_rutas = st.date_input(
                "Seleccionar Fecha para Ruta",
                value=max_fecha_ruta,
                key="filtro_fecha_diaria_rutas",
            )

        with col_r2:
            tipo_personal_sel = st.selectbox(
                "Tipo de Personal",
                options=["Todos", "Interno MIAA", "Externo"],
                index=0,
                key="filtro_tipo_personal_rutas",
            )

        df_rutas_dia = df_rutas_base[df_rutas_base["fecha_dt"].dt.date == fecha_sel_rutas].copy()

        if tipo_personal_sel == "Interno MIAA":
            df_rutas_dia = df_rutas_dia[~df_rutas_dia["usuarioExterno"]]
        elif tipo_personal_sel == "Externo":
            df_rutas_dia = df_rutas_dia[df_rutas_dia["usuarioExterno"]]

    # ==============================================================================
    # EXPANDER CON LISTBOX DE CHECKBOXES PARA FILTRAR INSTALADORES (SIN BOTONES)
    # ==============================================================================
    usuarios_disponibles = sorted(df_rutas_dia["usuarioNombre"].unique().tolist()) if not df_rutas_dia.empty else []

    with st.expander("👷‍♂️ Filtrar y Seleccionar Instaladores en el Mapa", expanded=False):
        if usuarios_disponibles:
            cols_check = st.columns(4)
            usuarios_seleccionados_manual = []
            
            for i, usr in enumerate(usuarios_disponibles):
                session_key = f"chk_map_usr_{usr}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = False
                
                with cols_check[i % 4]:
                    estado_chk = st.checkbox(f"{usr}", key=session_key)
                    if estado_chk:
                        usuarios_seleccionados_manual.append(usr)
        else:
            usuarios_seleccionados_manual = []
            st.info("No hay instaladores disponibles para la fecha seleccionada.")

    if usuarios_seleccionados_manual and not df_rutas_dia.empty:
        df_rutas_filtrada = df_rutas_dia[df_rutas_dia["usuarioNombre"].isin(usuarios_seleccionados_manual)].copy()
        usuarios_activos_mapa = usuarios_seleccionados_manual
    else:
        df_rutas_filtrada = df_rutas_dia.copy()
        usuarios_activos_mapa = usuarios_disponibles

    tot_inst_ruta = len(df_rutas_filtrada)
    tot_instaladores_act = len(usuarios_activos_mapa)
    prom_inst_persona = round(tot_inst_ruta / tot_instaladores_act, 1) if tot_instaladores_act > 0 else 0.0

    if not df_rutas_filtrada.empty:
        hora_primera = df_rutas_filtrada["fecha_dt"].min().strftime("%H:%M")
        hora_ultima = df_rutas_filtrada["fecha_dt"].max().strftime("%H:%M")
        rango_horario_str = f"{hora_primera} - {hora_ultima}"
    else:
        rango_horario_str = "N/A"

    rk1, rk2, rk3, rk4 = st.columns(4)
    with rk1:
        st.markdown(f"""<div class="metric-card"><div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-route"></i></div><div class="metric-content"><div class="metric-title">Instalaciones del Día</div><div class="metric-value">{tot_inst_ruta:,}</div></div></div>""", unsafe_allow_html=True)
    with rk2:
        st.markdown(f"""<div class="metric-card"><div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-user-check"></i></div><div class="metric-content"><div class="metric-title">Instaladores Activos</div><div class="metric-value">{tot_instaladores_act:,}</div></div></div>""", unsafe_allow_html=True)
    with rk3:
        st.markdown(f"""<div class="metric-card"><div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-calculator"></i></div><div class="metric-content"><div class="metric-title">Prom. por Instalador</div><div class="metric-value">{prom_inst_persona}</div></div></div>""", unsafe_allow_html=True)
    with rk4:
        st.markdown(f"""<div class="metric-card"><div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-clock"></i></div><div class="metric-content"><div class="metric-title">Jornada Detectada</div><div class="metric-value">{rango_horario_str}</div></div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    col_m_ruta, col_t_ruta = st.columns([1.7, 1.3])

    with col_m_ruta:
        with st.container(border=True):
            st.markdown(
                f"<p style='font-size:13px; font-weight:bold; margin-bottom:4px;'>🗺️ Mapa de Rutas Diarias por Personal ({fecha_sel_rutas.strftime('%d/%m/%Y') if fecha_sel_rutas else ''})</p>",
                unsafe_allow_html=True,
            )

            df_mapa_ruta = df_rutas_filtrada.dropna(subset=["latitud", "longitud"]).sort_values("fecha_dt").copy() if not df_rutas_filtrada.empty else pd.DataFrame()

            if not df_mapa_ruta.empty:
                r_lat_c = df_mapa_ruta["latitud"].mean()
                r_lon_c = df_mapa_ruta["longitud"].mean()
            else:
                r_lat_c, r_lon_c = lat_centro, lon_centro

            mapa_rutas = folium.Map(location=[r_lat_c, r_lon_c], zoom_start=13, tiles=None)
            agregar_capas_base(mapa_rutas)

            paleta_colores_ext = [
                "#38bdf8", "#4ade80", "#f59e0b", "#a855f7", "#f43f5e",
                "#06b6d4", "#84cc16", "#ec4899", "#6366f1", "#14b8a6",
                "#ff7043", "#ab47bc", "#26a69a", "#d4e157", "#ffa726",
                "#78909c", "#8d6e63", "#26c6da", "#9ccc65", "#ffca28"
            ]
            usuarios_unicos_mapa = df_mapa_ruta["usuarioNombre"].unique().tolist() if not df_mapa_ruta.empty else []
            mapa_color_usuario = {usr: paleta_colores_ext[i % len(paleta_colores_ext)] for i, usr in enumerate(usuarios_unicos_mapa)}

            for usr in usuarios_unicos_mapa:
                df_usr = df_mapa_ruta[df_mapa_ruta["usuarioNombre"] == usr].sort_values("fecha_dt")
                c_usr = mapa_color_usuario[usr]
                puntos_linea = []

                for _, row_r in df_usr.iterrows():
                    puntos_linea.append([float(row_r["latitud"]), float(row_r["longitud"])])

                if len(puntos_linea) > 1:
                    folium.PolyLine(puntos_linea, color=c_usr, weight=2.5, opacity=0.4, tooltip=f"Ruta de {usr}").add_to(mapa_rutas)
                    AntPath(locations=puntos_linea, color=c_usr, pulse_color="#ffffff", weight=4, opacity=0.9, dash_array=[15, 25], delay=800, symbol="▶", tooltip=f"Recorrido: {usr}").add_to(mapa_rutas)

                for orden_i, (_, row_r) in enumerate(df_usr.iterrows(), start=1):
                    lat_i, lon_i = float(row_r["latitud"]), float(row_r["longitud"])
                    nombre_usr = str(row_r.get("usuarioNombre", "N/A"))
                    predio_r = str(row_r.get("predio_viv", "N/A"))
                    
                    col_cli_p = next((c for c in ["cliente", "numeroCliente", "nombreCliente"] if c in row_r), None)
                    cliente_r = str(row_r[col_cli_p]) if col_cli_p and pd.notna(row_r[col_cli_p]) else "N/A"
                    
                    col_ser_p = next((c for c in ["serieMedidor", "serie"] if c in row_r), None)
                    serie_r = str(row_r[col_ser_p]) if col_ser_p and pd.notna(row_r[col_ser_p]) else "N/A"
                    
                    domicilio_r = str(row_r.get("domicilio", "N/A"))
                    colonia_r = str(row_r.get("colonia", "N/A"))
                    lugar_r = str(row_r.get("tipo_instalacion_nombre", row_r.get("lugarInstalacion", "N/A")))
                    
                    anom_raw = row_r["anomalia_nombre"] if "anomalia_nombre" in row_r else "SIN ANOMALÍA / REGULAR"
                    if isinstance(anom_raw, pd.Series):
                        anom_raw = anom_raw.iloc[0]
                    anomalia_r = str(anom_raw).strip() if pd.notna(anom_raw) else "SIN ANOMALÍA / REGULAR"
                    
                    hora_r = row_r["fecha_dt"].strftime("%H:%M:%S") if pd.notna(row_r["fecha_dt"]) else "N/A"

                    anom_upper = anomalia_r.upper()
                    es_normal = (
                        anom_upper == "" 
                        or anom_upper == "NAN" 
                        or anom_upper == "NONE" 
                        or "SIN" in anom_upper 
                        or "REGULAR" in anom_upper 
                        or "BUENO" in anom_upper
                    )
                    tiene_anomalia = not es_normal

                    popup_html = f"""
                    <div style="font-size: 11px; line-height: 1.4; color: #000000; min-width: 180px;">
                        <b>📍 Detalle de Instalación (#{orden_i})</b><br>
                        <b>Instalador:</b> {nombre_usr}<br>
                        <b>Hora:</b> {hora_r}<br>
                        <b>Predio:</b> {predio_r}<br>
                        <b>Cliente:</b> {cliente_r}<br>
                        <b>Serie:</b> {serie_r}<br>
                        <b>Domicilio:</b> {domicilio_r}<br>
                        <b>Colonia:</b> {colonia_r}<br>
                        <b>Lugar:</b> {lugar_r}<br>
                        <b>Anomalía:</b> <span style="color: {'#d97706' if tiene_anomalia else '#059669'}; font-weight: bold;">{anomalia_r}</span>
                    </div>
                    """
                    popup_obj = folium.Popup(popup_html, max_width=280)

                    if orden_i == 1:
                        icon_inicio = folium.DivIcon(
                            html=f'''<div style="display: flex; align-items: center; gap: 4px;"><div style="background-color: #10b981; width: 22px; height: 22px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.4);"><i class="fa-solid fa-play" style="color: white; font-size: 9px;"></i></div><span style="background: rgba(15,23,42,0.85); color: #10b981; padding: 1px 5px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid rgba(255,255,255,0.2);">{orden_i}</span></div>''',
                            icon_size=(50, 24),
                            icon_anchor=(11, 12)
                        )
                        folium.Marker([lat_i, lon_i], popup=popup_obj, tooltip=f"Inicio Ruta #{orden_i}: {usr}", icon=icon_inicio).add_to(mapa_rutas)
                    elif orden_i == len(df_usr):
                        icon_fin = folium.DivIcon(
                            html=f'''<div style="display: flex; align-items: center; gap: 4px;"><div style="background-color: #f43f5e; width: 22px; height: 22px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.4);"><i class="fa-solid fa-flag-checkered" style="color: white; font-size: 9px;"></i></div><span style="background: rgba(15,23,42,0.85); color: #f43f5e; padding: 1px 5px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid rgba(255,255,255,0.2);">{orden_i}</span></div>''',
                            icon_size=(50, 24),
                            icon_anchor=(11, 12)
                        )
                        folium.Marker([lat_i, lon_i], popup=popup_obj, tooltip=f"Fin Ruta #{orden_i}: {usr}", icon=icon_fin).add_to(mapa_rutas)
                    else:
                        if tiene_anomalia:
                            icon_anomalia = folium.DivIcon(
                                html=f'''<div style="display: flex; align-items: center; gap: 4px;"><div style="background-color: #eab308; width: 20px; height: 20px; border-radius: 50%; border: 2px solid #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.5);"><i class="fa-solid fa-triangle-exclamation" style="color: #000000; font-size: 8px;"></i></div><span style="background: rgba(15,23,42,0.85); color: #eab308; padding: 1px 5px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid rgba(255,255,255,0.2);">{orden_i}</span></div>''',
                                icon_size=(50, 22),
                                icon_anchor=(10, 11)
                            )
                            folium.Marker([lat_i, lon_i], popup=popup_obj, tooltip=f"⚠️ Anomalía #{orden_i} ({usr}): {anomalia_r}", icon=icon_anomalia).add_to(mapa_rutas)
                        else:
                            icon_num = folium.DivIcon(
                                html=f'''<div style="display: flex; align-items: center; gap: 4px;"><div style="background-color: {c_usr}; width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.4);"></div><span style="background: rgba(15,23,42,0.85); color: #ffffff; padding: 1px 5px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid rgba(255,255,255,0.2);">{orden_i}</span></div>''',
                                icon_size=(45, 20),
                                icon_anchor=(6, 10)
                            )
                            folium.Marker([lat_i, lon_i], popup=popup_obj, tooltip=f"Punto #{orden_i}: {usr}", icon=icon_num).add_to(mapa_rutas)

            st_folium(mapa_rutas, width=None, height=450, key="mapa_rutas_diarias_instaladores", returned_objects=[])

            # LEYENDA INFERIOR DENTRO DEL RECUADRO DEL MAPA
            st.markdown(
                """
                <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 11px; color: #cbd5e1; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="background-color: #10b981; width: 12px; height: 12px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa-solid fa-play" style="color: white; font-size: 5px;"></i>
                        </div>
                        <span><b>Inicio (#1)</b></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="background-color: #f43f5e; width: 12px; height: 12px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa-solid fa-flag-checkered" style="color: white; font-size: 5px;"></i>
                        </div>
                        <span><b>Meta / Fin</b></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="background-color: #3b82f6; width: 8px; height: 8px; border-radius: 50%; border: 1px solid white;"></div>
                        <span><b>Secuencia numérica</b></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="background-color: #eab308; width: 12px; height: 12px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa-solid fa-triangle-exclamation" style="color: black; font-size: 5px;"></i>
                        </div>
                        <span><b>Anomalía</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_t_ruta:
        with st.container(border=True):
            st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:4px;'>📊 Resumen de Instalaciones por Usuario</p>", unsafe_allow_html=True)

            if not df_rutas_filtrada.empty:
                # ------------------------------------------------------------------
                # CÁLCULO DE DISTANCIA ESPACIAL Y EFICIENCIA DE RUTA (CON VALIDACIÓN DE COORDENADAS)
                # ------------------------------------------------------------------
                def evaluar_eficiencia_usuario(df_sub):
                    # Filtrar únicamente registros que SÍ tengan coordenadas válidas
                    df_geo = df_sub.dropna(subset=["latitud", "longitud"]).copy()
                    
                    # Convertir a numérico por si vienen como strings sucios
                    df_geo["latitud"] = pd.to_numeric(df_geo["latitud"], errors="coerce")
                    df_geo["longitud"] = pd.to_numeric(df_geo["longitud"], errors="coerce")
                    df_geo = df_geo.dropna(subset=["latitud", "longitud"])

                    # Si no hay coordenadas geográficas registradas para este instalador
                    if df_geo.empty:
                        return "Sin registro de puntos"

                    # Si solo tiene 1 o 2 puntos geográficos, no hay ruta suficiente para evaluar trazo
                    if len(df_geo) <= 2:
                        return "Alta (Óptima)"

                    df_orden = df_geo.sort_values("fecha_dt")

                    lats = df_orden["latitud"].to_numpy()
                    lons = df_orden["longitud"].to_numpy()

                    # Fórmula de Haversine en metros
                    R = 6371000.0
                    phi = np.radians(lats)
                    lam = np.radians(lons)
                    dphi = phi[1:] - phi[:-1]
                    dlam = lam[1:] - lam[:-1]
                    a = np.sin(dphi/2.0)**2 + np.cos(phi[:-1])*np.cos(phi[1:])*np.sin(dlam/2.0)**2
                    distancias_m = R * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
                    
                    distancia_total = np.sum(distancias_m)
                    distancia_promedio = np.mean(distancias_m)

                    if distancia_promedio > 150 or (np.std(distancias_m) > 120 and distancia_total > 500):
                        return "Baja (Cruzada / Ineficiente)"
                    elif distancia_promedio > 80:
                        return "Media (Sinuosa)"
                    else:
                        return "Alta (Secuencial)"

                dict_eficiencias = {}
                for usr_k, df_u in df_rutas_filtrada.groupby("usuarioNombre"):
                    dict_eficiencias[usr_k] = evaluar_eficiencia_usuario(df_u)

                df_resumen_usr = df_rutas_filtrada.groupby(["usuarioNombre", "usuarioExterno"], as_index=False).agg(
                    Total_Instalaciones=("fecha_dt", "count"),
                    Primera_Instalacion=("fecha_dt", lambda x: x.min().strftime("%H:%M")),
                    Ultima_Instalacion=("fecha_dt", lambda x: x.max().strftime("%H:%M")),
                )
                
                df_resumen_usr["Tipo Personal"] = np.where(df_resumen_usr["usuarioExterno"], "Externo", "Interno MIAA")
                df_resumen_usr["Eficiencia"] = df_resumen_usr["usuarioNombre"].map(dict_eficiencias).fillna("Sin registro de puntos")
                
                df_resumen_usr = df_resumen_usr.sort_values(by="Total_Instalaciones", ascending=False)
                
                df_tabla_mostrar = df_resumen_usr[[
                    "usuarioNombre", "Total_Instalaciones", "Primera_Instalacion", "Ultima_Instalacion", "Eficiencia"
                ]].rename(columns={
                    "usuarioNombre": "Instalador", 
                    "Total_Instalaciones": "Total", 
                    "Primera_Instalacion": "Inicio", 
                    "Ultima_Instalacion": "Fin"
                })

                st.dataframe(df_tabla_mostrar, use_container_width=True, hide_index=True, height=220)

                df_grafica_usr = df_resumen_usr.rename(columns={"usuarioNombre": "Instalador", "Total_Instalaciones": "Total"})

                fig_usr_bar = px.bar(
                    df_grafica_usr, 
                    x="Total", 
                    y="Instalador", 
                    orientation="h", 
                    text="Total", 
                    color="Tipo Personal", 
                    color_discrete_map={"Externo": "#f59e0b", "Interno MIAA": "#10b981"}
                )
                fig_usr_bar.update_traces(textposition="outside", textfont_size=9)
                fig_usr_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    font_color="#ffffff", 
                    margin=dict(t=25, b=10, l=5, r=15), 
                    height=245, 
                    xaxis=dict(showgrid=False, title=None), 
                    yaxis=dict(showgrid=False, title=None, categoryorder="total ascending"), 
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.05, 
                        xanchor="left", 
                        x=0,
                        title=dict(text="")
                    )
                )
                st.plotly_chart(fig_usr_bar, use_container_width=True, key="grafico_barras_instaladores_ruta")
            else:
                st.info("No hay instaladores activos en el mapa.")

    # ==============================================================================
    # TABLA: DETALLE CRONOLÓGICO DE INSTALACIONES DE LA RUTA (CON NÚMERO DE PUNTO)
    # ==============================================================================
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "<p style='font-size:14px; font-weight:bold; margin-bottom:6px;'>📑 Detalle Cronológico de Instalaciones de la Ruta</p>",
            unsafe_allow_html=True,
        )

        if not df_rutas_filtrada.empty:
            df_cronologico = df_rutas_filtrada.copy()
            
            # CÁLCULO DEL NÚMERO DE PUNTO POR INSTALADOR EN ORDEN CRONOLÓGICO ASCENDENTE
            df_cronologico = df_cronologico.sort_values(by=["usuarioNombre", "fecha_dt"], ascending=[True, True])
            df_cronologico["#"] = df_cronologico.groupby("usuarioNombre").cumcount() + 1
            
            df_cronologico["Hora"] = df_cronologico["fecha_dt"].dt.strftime("%H:%M:%S")
            df_cronologico["Instalador"] = df_cronologico["usuarioNombre"]
            df_cronologico["Personal"] = np.where(df_cronologico["usuarioExterno"], "Externo", "Interno MIAA")
            
            col_cli_c = next((c for c in ["cliente", "numeroCliente", "nombreCliente"] if c in df_cronologico.columns), None)
            df_cronologico["Cliente"] = df_cronologico[col_cli_c].astype(str) if col_cli_c else "N/A"
            
            col_ser_c = next((c for c in ["serieMedidor", "serie"] if c in df_cronologico.columns), None)
            df_cronologico["Serie"] = df_cronologico[col_ser_c].astype(str) if col_ser_c else "N/A"
            
            df_cronologico["Predio"] = df_cronologico["predio_viv"] if "predio_viv" in df_cronologico.columns else "N/A"
            df_cronologico["Domicilio"] = df_cronologico["domicilio"].astype(str) if "domicilio" in df_cronologico.columns else "N/A"
            df_cronologico["Colonia"] = df_cronologico["colonia"].astype(str) if "colonia" in df_cronologico.columns else "N/A"
            df_cronologico["Lugar"] = df_cronologico["tipo_instalacion_nombre"].astype(str) if "tipo_instalacion_nombre" in df_cronologico.columns else "N/A"
            df_cronologico["Anomalía"] = df_cronologico["anomalia_nombre"].astype(str) if "anomalia_nombre" in df_cronologico.columns else "N/A"
            
            df_cronologico["Latitud"] = pd.to_numeric(df_cronologico["latitud"], errors="coerce")
            df_cronologico["Longitud"] = pd.to_numeric(df_cronologico["longitud"], errors="coerce")

            # REORDENAMOS LA TABLA PARA MOSTRAR PRIMERO LA COLUMNA `#` SEGUIDA DE `Hora`
            df_tabla_final_cron = df_cronologico[[
                "#", "Hora", "Instalador", "Personal", "Cliente", "Predio", 
                "Domicilio", "Colonia", "Serie", "Lugar", "Anomalía", 
                "Latitud", "Longitud"
            ]].sort_values(by=["Instalador", "#"], ascending=[True, False])

            st.dataframe(
                df_tabla_final_cron, 
                use_container_width=True, 
                hide_index=True, 
                height=300,
                column_config={
                    "#": st.column_config.NumberColumn("#", format="%d", width="small")
                }
            )
        else:
            st.info("No hay registros cronológicos para mostrar con los filtros actuales.")

# ------------------------------------------------------------------------------
# SECCIÓN 10 PESTAÑA: ANÁLISIS DE ANOMALÍAS
# ------------------------------------------------------------------------------
with tab_anomalias:
    st.markdown(
        "<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>⚠️ Análisis Completo de Anomalías en Instalaciones</p>",
        unsafe_allow_html=True,
    )

    df_con_anomalia = (
        df_filtrado[
            df_filtrado["anomalia_nombre"] != "SIN ANOMALÍA / REGULAR"
        ].copy()
        if not df_filtrado.empty and "anomalia_nombre" in df_filtrado.columns
        else pd.DataFrame()
    )

    total_anomalias_reg = len(df_con_anomalia)
    total_registros_filtrados = len(df_filtrado)
    pct_anomalias = (
        round((total_anomalias_reg / total_registros_filtrados) * 100, 2)
        if total_registros_filtrados > 0
        else 0.0
    )
    tipos_unicos_anomalias = (
        df_con_anomalia["anomalia_nombre"].nunique()
        if not df_con_anomalia.empty
        else 0
    )

    a_k1, a_k2, a_k3, a_k4 = st.columns(4)
    with a_k1:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total con Anomalía</div>
                        <div class="metric-value">{total_anomalias_reg:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
    with a_k2:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-list-check"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Tipos de Anomalías</div>
                        <div class="metric-value">{tipos_unicos_anomalias:,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
    with a_k3:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-percent"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">% Incidencia</div>
                        <div class="metric-value">{pct_anomalias}%</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
    with a_k4:
        st.markdown(
            f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-clipboard-check"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalaciones Regulares</div>
                        <div class="metric-value">{(total_registros_filtrados - total_anomalias_reg):,}</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

    col_anom_g1, col_anom_g2 = st.columns([1.5, 1])

    with col_anom_g1:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Tipo de Anomalía</p>",
                unsafe_allow_html=True,
            )
            if not df_con_anomalia.empty:
                df_counts_anom = (
                    df_con_anomalia["anomalia_nombre"].value_counts().reset_index()
                )
                df_counts_anom.columns = ["Anomalía", "Cantidad"]

                fig_anom_bar = px.bar(
                    df_counts_anom,
                    x="Cantidad",
                    y="Anomalía",
                    orientation="h",
                    text="Cantidad",
                    color="Anomalía",
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                fig_anom_bar.update_traces(textposition="outside", textfont_size=10)
                fig_anom_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=10, b=10, l=10, r=30),
                    height=270,
                    xaxis=dict(showgrid=True, title=None),
                    yaxis=dict(
                        showgrid=False, title=None, categoryorder="total ascending"
                    ),
                    showlegend=False,
                )
                st.plotly_chart(
                    fig_anom_bar, use_container_width=True, key="anomalias_dist_bar"
                )
            else:
                st.info("No se registran anomalías en el periodo o filtros seleccionados.")

    with col_anom_g2:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Proporción: Con Anomalía vs Regular</p>",
                unsafe_allow_html=True,
            )
            if total_registros_filtrados > 0:
                df_prop = pd.DataFrame({
                    "Estado": ["Con Anomalía", "Regular / Sin Anomalía"],
                    "Cantidad": [
                        total_anomalias_reg,
                        total_registros_filtrados - total_anomalias_reg,
                    ],
                })

                fig_prop_pie = px.pie(
                    df_prop,
                    names="Estado",
                    values="Cantidad",
                    hole=0.5,
                    color="Estado",
                    color_discrete_map={
                        "Con Anomalía": "#f43f5e",
                        "Regular / Sin Anomalía": "#3b82f6",
                    },
                )
                fig_prop_pie.update_traces(textinfo="value+percent", textfont=dict(size=11))
                fig_prop_pie.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=270,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
                )
                st.plotly_chart(
                    fig_prop_pie, use_container_width=True, key="anomalias_prop_pie"
                )
            else:
                st.info("Sin datos para mostrar proporción.")

    st.markdown(
        "<p style='font-size:14px; font-weight:bold; margin-top:20px; margin-bottom:8px;'>📋 Detalle de Registros con Anomalías Detectadas</p>",
        unsafe_allow_html=True,
    )
    if not df_con_anomalia.empty:
        df_tabla_anom = df_con_anomalia.copy()
        terminos_excluidos = [
            "foto",
            "fecharegistro",
            "fechamodificacion",
            "uuid",
            "horafin",
            "lecturaanterior",
            "lecturaactual",
            "folio",
        ]
        cols_ex = [
            c
            for c in df_tabla_anom.columns
            if any(term in c.lower() for term in terminos_excluidos)
        ]
        df_tabla_anom = df_tabla_anom.drop(columns=cols_ex, errors="ignore")
        if "fechaInstalacion" in df_tabla_anom.columns:
            df_tabla_anom["fechaInstalacion"] = pd.to_datetime(
                df_tabla_anom["fechaInstalacion"], errors="coerce"
            ).dt.strftime("%d/%m/%Y %H:%M:%S")
        df_tabla_anom = df_tabla_anom.drop(
            columns=[
                "fecha_dt",
                "Semana",
                "fecha_dia",
                "anio_mes",
                "periodo_mes",
            ],
            errors="ignore",
        )
        st.dataframe(df_tabla_anom, use_container_width=True)
    else:
        st.success(
            "¡Excelente! No hay registros con anomalías reportadas para los filtros seleccionados."
        )

# ------------------------------------------------------------------------------
# SECCIÓN 11 PESTAÑA: MAPA DE POLÍGONOS DE INSTALACIÓN
# ------------------------------------------------------------------------------
script_poligonos_procesados = {}
shapely_polygons = {}
lat_acumuladas, lon_acumuladas = [], []

with tab_poligonos:
    if not df_poligonos.empty:
        raw_fids_sucios = df_poligonos["FID"].dropna().unique().tolist()
        try:
            raw_fids = sorted(raw_fids_sucios, key=lambda x: float(x))
        except:
            raw_fids = sorted(raw_fids_sucios, key=str)

        tot_poligonos_val = len(raw_fids)
        fids_disponibles = [
            (
                str(int(float(f)))
                if str(f).replace(".", "", 1).isdigit()
                else str(f)
            )
            for f in raw_fids
        ]
    else:
        raw_fids = []
        fids_disponibles = []
        tot_poligonos_val = 0

    poligonos_procesados = {}
    if not df_poligonos.empty:
        for raw_fid in raw_fids:
            fid_str = (
                str(int(float(raw_fid)))
                if str(raw_fid).replace(".", "", 1).isdigit()
                else str(raw_fid)
            )
            df_pol_sel = df_poligonos[
                df_poligonos["FID"].astype(str).str.contains(fid_str)
            ]

            coordenadas_poligono = []
            df_ordenado = df_pol_sel.sort_values(by="Orden_inst", ascending=True)
            sec_comercial = (
                df_pol_sel["Sector_comercial"].iloc[0]
                if "Sector_comercial" in df_pol_sel.columns
                else "N/A"
            )
            area_val = (
                df_pol_sel["Area_km2"].iloc[0]
                if "Area_km2" in df_pol_sel.columns
                else 0
            )
            med_val = (
                df_pol_sel["Medidores"].iloc[0]
                if "Medidores" in df_pol_sel.columns
                else 0
            )

            for _, r_vertice in df_ordenado.iterrows():
                c_val = r_vertice["coord"]
                if pd.isna(c_val):
                    continue
                c_str = str(c_val).strip()
                for char in ["[", "]", '"', "'", "POINT", "POLYGON"]:
                    c_str = c_str.replace(char, "")
                pares = [p.strip() for p in c_str.split(",") if p.strip()]

                if len(pares) >= 2 and len(pares) % 2 == 0:
                    for i in range(0, len(pares), 2):
                        try:
                            p1, p2 = float(pares[i]), float(pares[i + 1])
                            lat, lon = (p2, p1) if abs(p1) > abs(p2) else (p1, p2)
                            coordenadas_poligono.append([lat, lon])
                            lat_acumuladas.append(lat)
                            lon_acumuladas.append(lon)
                        except:
                            pass

            if coordenadas_poligono:
                poligonos_procesados[fid_str] = {
                    "fid": fid_str,
                    "coordenadas": coordenadas_poligono,
                    "sector": sec_comercial,
                    "area": area_val,
                    "medidores_db": med_val,
                    "vertis": len(coordenadas_poligono),
                }
                try:
                    poly_geom = Polygon(coordenadas_poligono)
                    if not poly_geom.is_valid:
                        poly_geom = poly_geom.buffer(0)
                    shapely_polygons[fid_str] = poly_geom
                except:
                    pass

    conteo_medidores_instalados = {f_id: 0 for f_id in fids_disponibles}
    if (
        shapely_polygons
        and not df_filtrado.empty
        and "latitud" in df_filtrado.columns
    ):
        try:
            for _, row_m in df_filtrado.dropna(
                subset=["latitud", "longitud"]
            ).iterrows():
                pt = Point(row_m["latitud"], row_m["longitud"])
                for f_id, poly in shapely_polygons.items():
                    if poly.contains(pt):
                        conteo_medidores_instalados[f_id] += 1
                        break
        except:
            pass

    counts_list = list(conteo_medidores_instalados.values())
    max_inst_val = max(counts_list) if counts_list and max(counts_list) > 0 else 1

    col_c_izq, col_c_centro, col_c_der = st.columns([0.22, 0.52, 0.26])

    with col_c_izq:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; font-weight:bold; margin-bottom:4px;'>Seleccionar Polígonos (FID)</p>",
                unsafe_allow_html=True,
            )

            b_col1, b_col2 = st.columns(2)
            if b_col1.button("Todos", key="btn_all_fids_ref"):
                for f_id in fids_disponibles:
                    st.session_state[f"map_fid_chk_{f_id}"] = True
            if b_col2.button("Ninguno", key="btn_none_fids_ref"):
                for f_id in fids_disponibles:
                    st.session_state[f"map_fid_chk_{f_id}"] = False

            busqueda_fid = st.text_input(
                "Buscar FID...",
                placeholder="Buscar FID...",
                label_visibility="collapsed",
            )
            st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)

            with st.container(height=390):
                fids_seleccionados_mapa = []
                for f_id in fids_disponibles:
                    if f"map_fid_chk_{f_id}" not in st.session_state:
                        st.session_state[f"map_fid_chk_{f_id}"] = True

                    if busqueda_fid and busqueda_fid.lower() not in str(f_id).lower():
                        continue

                    inst_cnt_local = conteo_medidores_instalados.get(f_id, 0)
                    chk_estado = st.checkbox(
                        f"FID {f_id} ({inst_cnt_local})", key=f"map_fid_chk_{f_id}"
                    )
                    if chk_estado:
                        fids_seleccionados_mapa.append(f_id)

    with col_c_centro:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; font-weight:bold; margin-bottom:2px;'>Mapa de Polígonos de Instalación</p>",
                unsafe_allow_html=True,
            )

            m_p_lat = (
                sum(lat_acumuladas) / len(lat_acumuladas)
                if lat_acumuladas
                else 21.8853
            )
            m_p_lon = (
                sum(lon_acumuladas) / len(lon_acumuladas)
                if lon_acumuladas
                else -102.2916
            )

            pydeck_data = []
            for f_id, datos in poligonos_procesados.items():
                if f_id in fids_seleccionados_mapa:
                    inst_count = conteo_medidores_instalados.get(f_id, 0)
                    polygon_coords_lon_lat = [
                        [coord[1], coord[0]] for coord in datos["coordenadas"]
                    ]

                    if inst_count == 0:
                        color = [239, 68, 68, 190]
                        elevation = 15
                    elif inst_count >= max_inst_val * 0.5:
                        color = [34, 197, 94, 190]
                        elevation = float(inst_count * 10 + 40)
                    else:
                        color = [234, 179, 8, 190]
                        elevation = float(inst_count * 10 + 25)

                    pydeck_data.append({
                        "polygon": polygon_coords_lon_lat,
                        "elevation": elevation,
                        "color": color,
                        "fid": str(f_id),
                        "sector": str(datos["sector"]),
                        "instalados": int(inst_count),
                        "medidores_db": int(datos["medidores_db"]),
                    })

            layer = pdk.Layer(
                "PolygonLayer",
                pydeck_data,
                get_polygon="polygon",
                get_elevation="elevation",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 140],
                line_width_min_pixels=1,
                extruded=True,
                pickable=True,
                auto_highlight=True,
            )

            r = pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(
                    latitude=m_p_lat, longitude=m_p_lon, zoom=11.5, pitch=45, bearing=0
                ),
                tooltip={
                    "html": (
                        "<b>Polígono FID: {fid}</b><br/>Sector:"
                        " {sector}<br/>Medidores Instalados:"
                        " {instalados}<br/>Medidores DB: {medidores_db}"
                    ),
                    "style": {
                        "backgroundColor": "rgba(15, 23, 42, 0.95)",
                        "color": "white",
                        "fontSize": "11px",
                        "padding": "6px",
                        "borderRadius": "4px",
                    },
                },
            )

            st.pydeck_chart(r, use_container_width=True, height=520)

    with col_c_der:
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:14px; font-weight:bold; margin-bottom:8px;'>Resumen por Sector</p>",
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 6px; margin-bottom: 8px;">
                    <div style="width: 25%;">Sector</div>
                    <div style="width: 25%; text-align: center;">Medidores (BD)</div>
                    <div style="width: 25%; text-align: center;">Instalados (API)</div>
                    <div style="width: 25%; text-align: right;">Avance</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

            if not df_poligonos.empty and "Sector_comercial" in df_poligonos.columns:
                df_fids_unicos = df_poligonos.groupby(["FID", "Sector_comercial"]).agg(
                    {"Medidores": "first", "Area_km2": "first"}
                ).reset_index()

                df_fids_unicos["f_id"] = df_fids_unicos["FID"].apply(
                    lambda x: (
                        str(int(float(x)))
                        if str(x).replace(".", "", 1).isdigit()
                        else str(x)
                    )
                )
                sectores_unicos = df_fids_unicos["Sector_comercial"].dropna().unique()

                lista_sectores_datos = []
                for s_nombre in sectores_unicos:
                    df_sec_subset = df_fids_unicos[
                        df_fids_unicos["Sector_comercial"] == s_nombre
                    ]

                    s_med_db = int(
                        pd.to_numeric(df_sec_subset["Medidores"], errors="coerce").sum()
                    )
                    fids_del_sector = df_sec_subset["f_id"].tolist()
                    s_med_instalados = int(
                        sum(conteo_medidores_instalados.get(f, 0) for f in fids_del_sector)
                    )

                    s_avance = (
                        round((s_med_instalados / s_med_db * 100), 1)
                        if s_med_db > 0
                        else 0.0
                    )

                    lista_sectores_datos.append({
                        "sector": s_nombre,
                        "med_db": s_med_db,
                        "med_inst": s_med_instalados,
                        "avance": s_avance,
                    })

                df_resumen_sectores = pd.DataFrame(lista_sectores_datos)
                if not df_resumen_sectores.empty:
                    df_resumen_sectores = df_resumen_sectores.sort_values(
                        by="avance", ascending=False
                    )

                    for _, row_sec in df_resumen_sectores.iterrows():
                        s_nombre = row_sec["sector"]
                        s_med_db = row_sec["med_db"]
                        s_med_instalados = row_sec["med_inst"]
                        s_avance = row_sec["avance"]
                        s_avance_cap = min(s_avance, 100.0)

                        dot_color = (
                            "#22c55e"
                            if s_avance >= 80.0
                            else ("#ef4444" if s_avance <= 40.0 else "#eab308")
                        )

                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 8px;">
                                <div style="width: 25%; display: flex; align-items: center; gap: 8px; color: white; font-weight: bold; font-size: 14px;">
                                    <span style="width: 10px; height: 10px; background-color: {dot_color}; border-radius: 50%; display: inline-block;"></span>
                                    {s_nombre}
                                </div>
                                <div style="width: 25%; color: #cbd5e1; text-align: center; font-weight: 600; font-size: 13px;">{s_med_db:,}</div>
                                <div style="width: 25%; color: #ffffff; text-align: center; font-weight: bold; font-size: 13px;">{s_med_instalados:,}</div>
                                <div style="width: 25%; text-align: right;">
                                    <div style="font-size: 12px; color: white; font-weight: bold; margin-bottom: 3px;">{s_avance}%</div>
                                    <div style="background-color: rgba(255,255,255,0.12); border-radius: 4px; width: 100%; height: 8px; overflow: hidden;">
                                        <div style="background-color: {dot_color}; width: {s_avance_cap}%; height: 100%; border-radius: 4px;"></div>
                                    </div>
                                </div>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )
            else:
                st.info("Sin datos de sectores disponibles.")

    with st.container(border=True):
        st.markdown(
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Detalle de Polígonos de Instalación y Conteo de Medidores</p>",
            unsafe_allow_html=True,
        )

        resumen_poligonos = []
        for f_id, datos in poligonos_procesados.items():
            if f_id in fids_seleccionados_mapa:
                med_db = datos["medidores_db"]
                inst_count = conteo_medidores_instalados.get(f_id, 0)
                pct_avance_pol = (
                    round((inst_count / med_db * 100), 2) if med_db > 0 else 0.0
                )

                try:
                    fid_val = int(float(datos.get("fid")))
                except:
                    fid_val = datos.get("fid")

                resumen_poligonos.append({
                    "FID": fid_val,
                    "Sector Comercial": datos["sector"],
                    "Área (km²)": datos["area"],
                    "Medidores (DB)": med_db,
                    "Medidores Instalados (API)": inst_count,
                    "Avance (%)": f"{pct_avance_pol}%",
                    "Vértices Totales": datos["vertis"],
                })

        if resumen_poligonos:
            df_resumen_tabla = pd.DataFrame(resumen_poligonos)
            df_resumen_tabla["FID_num"] = pd.to_numeric(
                df_resumen_tabla["FID"], errors="coerce"
            )
            df_resumen_tabla = df_resumen_tabla.sort_values(by="FID_num").drop(
                columns=["FID_num"]
            )
        else:
            df_resumen_tabla = pd.DataFrame(
                columns=[
                    "FID",
                    "Sector Comercial",
                    "Área (km²)",
                    "Medidores (DB)",
                    "Medidores Instalados (API)",
                    "Avance (%)",
                    "Vértices Totales",
                ]
            )

        st.dataframe(
            df_resumen_tabla, use_container_width=True, hide_index=True, height=250
        )

# ------------------------------------------------------------------------------
# SECCIÓN 12 PESTAÑA: PERSONAL (EXTERNO Y MIAA)
# ------------------------------------------------------------------------------
with tab_personal:
    st.markdown(
        "<p style='font-size:16px; font-weight:bold; margin-bottom:5px;'>👥 Resumen General de Instalaciones por Tipo de Personal</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:13px; color: #94a3b8; margin-bottom:15px;'>Comparativa y desglose operacional entre Personal Externo y Personal Interno MIAA.</p>",
        unsafe_allow_html=True,
    )

    sub_ext, sub_miaa_int = st.tabs(["👷 Personal Externo", "👤 Personal MIAA"])

    with sub_ext:
        ext_total = len(df_externo)
        ext_sin_coord = (
            df_externo["latitud"].isna().sum()
            if not df_externo.empty and "latitud" in df_externo.columns
            else 0
        )
        ext_colonias = (
            df_externo["colonia"].nunique()
            if not df_externo.empty and "colonia" in df_externo.columns
            else 0
        )

        e_k1, e_k2, e_k3 = st.columns(3)
        with e_k1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Instalados (Externo)</div>
                        <div class="metric-value">{ext_total:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        with e_k2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Colonias Atendidas</div>
                        <div class="metric-value">{ext_colonias:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        with e_k3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{ext_sin_coord:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_ex_left, col_ex_right = st.columns([1.1, 1.3])

        with col_ex_left:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día (Externo)</p>",
                    unsafe_allow_html=True,
                )
                if (
                    col_fecha_ref
                    and not df_externo.empty
                    and not df_externo["fecha_dt"].isna().all()
                ):
                    df_ext_dia = df_externo.copy()
                    df_ext_dia["fecha_dia"] = df_ext_dia["fecha_dt"].dt.date
                    df_ed = df_ext_dia.groupby("fecha_dia", as_index=False).size()
                    df_ed["fecha_dia"] = pd.to_datetime(df_ed["fecha_dia"]).dt.strftime(
                        "%d/%m/%Y"
                    )
                    fig_ext_dia = px.bar(
                        df_ed,
                        x="fecha_dia",
                        y="size",
                        text="size",
                        color_discrete_sequence=["#f59e0b"],
                    )
                else:
                    fig_ext_dia = px.bar(
                        pd.DataFrame({"Aviso": ["Sin datos"], "Valor": [0]}),
                        x="Aviso",
                        y="Valor",
                        text="Valor",
                    )

                fig_ext_dia.update_traces(textposition="outside", textfont_size=10)
                fig_ext_dia.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=30, b=5, l=5, r=5),
                    height=210,
                    xaxis_title=None,
                    yaxis_title=None,
                )
                st.plotly_chart(
                    fig_ext_dia, use_container_width=True, key="ext_instalaciones_dia"
                )

            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Nivel Tarifario (Externo)</p>",
                    unsafe_allow_html=True,
                )
                if not df_externo.empty and "nivel" in df_externo.columns:
                    df_ext_nivel = (
                        df_externo["nivel"].fillna("SIN NIVEL").value_counts().reset_index()
                    )
                    df_ext_nivel.columns = ["Nivel", "Cantidad"]
                    fig_ext_niv = px.bar(
                        df_ext_nivel,
                        x="Nivel",
                        y="Cantidad",
                        text="Cantidad",
                        color="Nivel",
                        color_discrete_sequence=px.colors.qualitative.Safe,
                    )
                    fig_ext_niv.update_traces(textposition="outside", textfont_size=10)
                else:
                    fig_ext_niv = px.bar(
                        pd.DataFrame({"Nivel": ["Sin datos"], "Cantidad": [0]}),
                        x="Nivel",
                        y="Cantidad",
                        text="Cantidad",
                    )

                fig_ext_niv.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=30, b=5, l=5, r=5),
                    height=210,
                    xaxis_title=None,
                    yaxis_title=None,
                    showlegend=False,
                )
                st.plotly_chart(
                    fig_ext_niv, use_container_width=True, key="ext_nivel_tarifario"
                )

        with col_ex_right:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones - Personal Externo</p>",
                    unsafe_allow_html=True,
                )
                df_ext_map = (
                    df_externo.dropna(subset=["latitud", "longitud"])
                    if not df_externo.empty and "latitud" in df_externo.columns
                    else pd.DataFrame()
                )
                m_lat = (
                    df_ext_map["latitud"].mean()
                    if not df_ext_map.empty
                    else lat_centro
                )
                m_lon = (
                    df_ext_map["longitud"].mean()
                    if not df_ext_map.empty
                    else lon_centro
                )

                mapa_ext = folium.Map(location=[m_lat, m_lon], zoom_start=12, tiles=None)
                agregar_capas_base(mapa_ext)

                for _, row in df_ext_map.iterrows():
                    folium.CircleMarker(
                        location=[float(row["latitud"]), float(row["longitud"])],
                        radius=2.5,
                        color="#f59e0b",
                        fill=True,
                        fill_color="#f59e0b",
                        fill_opacity=0.7,
                    ).add_to(mapa_ext)

                st_folium(
                    mapa_ext,
                    width=None,
                    height=460,
                    key="mapa_externo_unificado",
                    returned_objects=[],
                )

        st.markdown(
            "<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal Externo</p>",
            unsafe_allow_html=True,
        )
        df_tabla_ext = df_externo.copy()
        if not df_tabla_ext.empty:
            terminos_excluidos = [
                "foto",
                "fecharegistro",
                "fechamodificacion",
                "uuid",
                "horafin",
                "lecturaanterior",
                "lecturaactual",
                "folio",
            ]
            cols_ex = [
                c
                for c in df_tabla_ext.columns
                if any(term in c.lower() for term in terminos_excluidos)
            ]
            df_tabla_ext = df_tabla_ext.drop(columns=cols_ex, errors="ignore")
            if "fechaInstalacion" in df_tabla_ext.columns:
                df_tabla_ext["fechaInstalacion"] = pd.to_datetime(
                    df_tabla_ext["fechaInstalacion"], errors="coerce"
                ).dt.strftime("%d/%m/%Y %H:%M:%S")
            df_tabla_ext = df_tabla_ext.drop(
                columns=[
                    "fecha_dt",
                    "Semana",
                    "fecha_dia",
                    "anio_mes",
                    "periodo_mes",
                ],
                errors="ignore",
            )

            busqueda_ext = st.text_input("Buscar en Personal Externo...", placeholder="Ej. Predio, Nombre, Serie...", key="filtro_ext_global")
            if busqueda_ext:
                b_ext_txt = busqueda_ext.lower()
                mask_ext = df_tabla_ext.astype(str).apply(lambda row: row.str.lower().str.contains(b_ext_txt).any(), axis=1)
                df_tabla_ext = df_tabla_ext[mask_ext]

            total_reg_ext = len(df_tabla_ext)
            if total_reg_ext > 0:
                tam_pag_ext = 10
                tot_pag_ext = math.ceil(total_reg_ext / tam_pag_ext)
                col_p1, col_p2 = st.columns([2, 1])
                with col_p1:
                    pag_ext_act = st.selectbox("Hoja / Página (Externo)", options=list(range(1, tot_pag_ext + 1)), format_func=lambda x: f"Hoja {x} de {tot_pag_ext} (Registros {(x-1)*tam_pag_ext + 1} al {min(x*tam_pag_ext, total_reg_ext)})", key="pag_ext_sel")
                with col_p2:
                    st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: #38bdf8; font-weight: bold;'>Mostrando 10 por hoja</div>", unsafe_allow_html=True)

                i_ini = (pag_ext_act - 1) * tam_pag_ext
                i_fin = i_ini + tam_pag_ext
                st.dataframe(df_tabla_ext.iloc[i_ini:i_fin], use_container_width=True, hide_index=True)
            else:
                st.info("No se encontraron registros en Personal Externo.")
        else:
            st.info("No hay registros disponibles para Personal Externo.")

    with sub_miaa_int:
        miaa_total = len(df_miaa_pers)
        miaa_sin_coord = (
            df_miaa_pers["latitud"].isna().sum()
            if not df_miaa_pers.empty and "latitud" in df_miaa_pers.columns
            else 0
        )
        miaa_colonias = (
            df_miaa_pers["colonia"].nunique()
            if not df_miaa_pers.empty and "colonia" in df_miaa_pers.columns
            else 0
        )

        m_k1, m_k2, m_k3 = st.columns(3)
        with m_k1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #10b981;"><i class="fa-solid fa-building-user"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Instalados (MIAA)</div>
                        <div class="metric-value">{miaa_total:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        with m_k2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Colonias Atendidas</div>
                        <div class="metric-value">{miaa_colonias:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        with m_k3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{miaa_sin_coord:,}</div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_mi_left, col_mi_right = st.columns([1.1, 1.3])

        with col_mi_left:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día (MIAA)</p>",
                    unsafe_allow_html=True,
                )
                if (
                    col_fecha_ref
                    and not df_miaa_pers.empty
                    and not df_miaa_pers["fecha_dt"].isna().all()
                ):
                    df_miaa_dia = df_miaa_pers.copy()
                    df_miaa_dia["fecha_dia"] = df_miaa_dia["fecha_dt"].dt.date
                    df_md = df_miaa_dia.groupby("fecha_dia", as_index=False).size()
                    df_md["fecha_dia"] = pd.to_datetime(df_md["fecha_dia"]).dt.strftime(
                        "%d/%m/%Y"
                    )
                    fig_miaa_dia = px.bar(
                        df_md,
                        x="fecha_dia",
                        y="size",
                        text="size",
                        color_discrete_sequence=["#10b981"],
                    )
                else:
                    fig_miaa_dia = px.bar(
                        pd.DataFrame({"Aviso": ["Sin datos"], "Valor": [0]}),
                        x="Aviso",
                        y="Valor",
                        text="Valor",
                    )

                fig_miaa_dia.update_traces(textposition="outside", textfont_size=10)
                fig_miaa_dia.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=30, b=5, l=5, r=5),
                    height=210,
                    xaxis_title=None,
                    yaxis_title=None,
                )
                st.plotly_chart(
                    fig_miaa_dia, use_container_width=True, key="grafico_miaa_dia_unico"
                )

            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Distribución por Nivel Tarifario (MIAA)</p>",
                    unsafe_allow_html=True,
                )
                if not df_miaa_pers.empty and "nivel" in df_miaa_pers.columns:
                    df_miaa_nivel = (
                        df_miaa_pers["nivel"]
                        .fillna("SIN NIVEL")
                        .value_counts()
                        .reset_index()
                    )
                    df_miaa_nivel.columns = ["Nivel", "Cantidad"]
                    fig_miaa_niv = px.bar(
                        df_miaa_nivel,
                        x="Nivel",
                        y="Cantidad",
                        text="Cantidad",
                        color="Nivel",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                    )
                    fig_miaa_niv.update_traces(textposition="outside", textfont_size=10)
                else:
                    fig_miaa_niv = px.bar(
                        pd.DataFrame({"Nivel": ["Sin datos"], "Cantidad": [0]}),
                        x="Nivel",
                        y="Cantidad",
                        text="Cantidad",
                    )

                fig_miaa_niv.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=30, b=5, l=5, r=5),
                    height=210,
                    xaxis_title=None,
                    yaxis_title=None,
                    showlegend=False,
                )
                st.plotly_chart(
                    fig_miaa_niv, use_container_width=True, key="grafico_miaa_nivel_unico"
                )

        with col_mi_right:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa de Instalaciones - Personal MIAA</p>",
                    unsafe_allow_html=True,
                )
                df_miaa_map = (
                    df_miaa_pers.dropna(subset=["latitud", "longitud"])
                    if not df_miaa_pers.empty and "latitud" in df_miaa_pers.columns
                    else pd.DataFrame()
                )
                mm_lat = (
                    df_miaa_map["latitud"].mean()
                    if not df_miaa_map.empty
                    else lat_centro
                )
                mm_lon = (
                    df_miaa_map["longitud"].mean()
                    if not df_miaa_map.empty
                    else lon_centro
                )

                mapa_miaa_pers = folium.Map(
                    location=[mm_lat, mm_lon], zoom_start=12, tiles=None
                )
                agregar_capas_base(mapa_miaa_pers)

                for _, row in df_miaa_map.iterrows():
                    folium.CircleMarker(
                        location=[float(row["latitud"]), float(row["longitud"])],
                        radius=2.5,
                        color="#10b981",
                        fill=True,
                        fill_color="#10b981",
                        fill_opacity=0.7,
                    ).add_to(mapa_miaa_pers)

                st_folium(
                    mapa_miaa_pers,
                    width=None,
                    height=460,
                    key="mapa_miaa_personal_unificado",
                    returned_objects=[],
                )

        st.markdown(
            "<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal MIAA</p>",
            unsafe_allow_html=True,
        )
        df_tabla_miaa = df_miaa_pers.copy()
        if not df_tabla_miaa.empty:
            terminos_excluidos = [
                "foto",
                "fecharegistro",
                "fechamodificacion",
                "uuid",
                "horafin",
                "lecturaanterior",
                "lecturaactual",
                "folio",
            ]
            cols_ex = [
                c
                for c in df_tabla_miaa.columns
                if any(term in c.lower() for term in terminos_excluidos)
            ]
            df_tabla_miaa = df_tabla_miaa.drop(columns=cols_ex, errors="ignore")
            if "fechaInstalacion" in df_tabla_miaa.columns:
                df_tabla_miaa["fechaInstalacion"] = pd.to_datetime(
                    df_tabla_miaa["fechaInstalacion"], errors="coerce"
                ).dt.strftime("%d/%m/%Y %H:%M:%S")
            df_tabla_miaa = df_tabla_miaa.drop(
                columns=[
                    "fecha_dt",
                    "Semana",
                    "fecha_dia",
                    "anio_mes",
                    "periodo_mes",
                ],
                errors="ignore",
            )

            busqueda_miaa_p = st.text_input("Buscar en Personal MIAA...", placeholder="Ej. Predio, Nombre, Serie...", key="filtro_miaa_global")
            if busqueda_miaa_p:
                b_miaa_txt = busqueda_miaa_p.lower()
                mask_miaa = df_tabla_miaa.astype(str).apply(lambda row: row.str.lower().str.contains(b_miaa_txt).any(), axis=1)
                df_tabla_miaa = df_tabla_miaa[mask_miaa]

            total_reg_miaa = len(df_tabla_miaa)
            if total_reg_miaa > 0:
                tam_pag_miaa = 10
                tot_pag_miaa = math.ceil(total_reg_miaa / tam_pag_miaa)
                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    pag_miaa_act = st.selectbox("Hoja / Página (MIAA)", options=list(range(1, tot_pag_miaa + 1)), format_func=lambda x: f"Hoja {x} de {tot_pag_miaa} (Registros {(x-1)*tam_pag_miaa + 1} al {min(x*tam_pag_miaa, total_reg_miaa)})", key="pag_miaa_sel")
                with col_m2:
                    st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: #38bdf8; font-weight: bold;'>Mostrando 10 por hoja</div>", unsafe_allow_html=True)

                i_ini_m = (pag_miaa_act - 1) * tam_pag_miaa
                i_fin_m = i_ini_m + tam_pag_miaa
                st.dataframe(df_tabla_miaa.iloc[i_ini_m:i_fin_m], use_container_width=True, hide_index=True)
            else:
                st.info("No se encontraron registros en Personal MIAA.")
        else:
            st.info("No hay registros disponibles para Personal MIAA.")

# ==============================================================================
# SECCIÓN 13 CARGAR DATOS DESDE POSTGRESQL USANDO GEOM Y ETAPA
# ==============================================================================
df_usuarios_miaa_medidor = cargar_usuarios_miaa_conmedidor_db()

if not df_usuarios_miaa_medidor.empty:
    lats, lons = [], []
    for _, row in df_usuarios_miaa_medidor.iterrows():
        try:
            x_val = float(row["utm_x"])
            y_val = float(row["utm_y"])
            
            if abs(x_val) > 360 or abs(y_val) > 90:
                lon_deg = -102.2916 + (x_val - 780000) / 111000.0
                lat_deg = 21.8853 + (y_val - 2420000) / 110500.0
                lats.append(lat_deg)
                lons.append(lon_deg)
            else:
                lats.append(y_val)
                lons.append(x_val)
        except:
            lats.append(np.nan)
            lons.append(np.nan)
            
    df_usuarios_miaa_medidor["lat_calc"] = lats
    df_usuarios_miaa_medidor["lon_calc"] = lons
else:
    df_usuarios_miaa_medidor["lat_calc"] = []
    df_usuarios_miaa_medidor["lon_calc"] = []

# ------------------------------------------------------------------------------
# SECCIÓN 14 PESTAÑA: TABLA BASE DE DATOS COMPLETA
# ------------------------------------------------------------------------------
with tab_tabla:
    st.markdown(
        "<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📋 Registros de la Tabla: usuarios_miaa_conmedidor</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            "<p style='font-size:13px; font-weight:bold; margin-bottom:8px;'>🔍 Filtros de Búsqueda Global en toda la Base de Datos</p>",
            unsafe_allow_html=True,
        )
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_serie = st.text_input(
                "Filtrar por Número de Serie",
                placeholder="Ej. _Serie...",
                key="filtro_tab_serie_miaa",
            )
        with col_f2:
            filtro_medidor = st.text_input(
                "Filtrar por Número de Medidor",
                placeholder="Ej. Medidor...",
                key="filtro_tab_medidor_miaa",
            )
        with col_f3:
            filtro_predio = st.text_input(
                "Filtrar por Predio",
                placeholder="Ej. Predio_Viv...",
                key="filtro_tab_predio_miaa",
            )

    df_tabla_filtrada = df_usuarios_miaa_medidor.copy()
    
    if not df_tabla_filtrada.empty:
        if filtro_serie:
            col_s = next((c for c in ["_Serie", "serie", "serieMedidor"] if c in df_tabla_filtrada.columns), None)
            if col_s:
                df_tabla_filtrada = df_tabla_filtrada[
                    df_tabla_filtrada[col_s].astype(str).str.contains(filtro_serie, case=False, na=False)
                ]

        if filtro_medidor:
            col_m = next((c for c in ["Medidor", "medidorId", "medidor"] if c in df_tabla_filtrada.columns), None)
            if col_m:
                df_tabla_filtrada = df_tabla_filtrada[
                    df_tabla_filtrada[col_m].astype(str).str.contains(filtro_medidor, case=False, na=False)
                ]

        if filtro_predio:
            col_p = next((c for c in ["Predio_Viv", "predio", "numeroPredio"] if c in df_tabla_filtrada.columns), None)
            if col_p:
                df_tabla_filtrada = df_tabla_filtrada[
                    df_tabla_filtrada[col_p].astype(str).str.contains(filtro_predio, case=False, na=False)
                ]

    total_registros_tabla = len(df_tabla_filtrada)

    if not df_tabla_filtrada.empty and "etapa" in df_tabla_filtrada.columns:
        etapa_serie_limpia = df_tabla_filtrada["etapa"].astype(str).str.strip().str.lower()
        total_etapa_1 = int(etapa_serie_limpia.isin(["1", "etapa 1"]).sum())
        total_etapa_2 = int(etapa_serie_limpia.isin(["2", "etapa 2"]).sum())
    else:
        total_etapa_1 = 0
        total_etapa_2 = 0

    k_col1, k_col2, k_col3 = st.columns(3)

    with k_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-table-list"></i></div>
                <div class="metric-content">
                    <div class="metric-title">Total Registros (1 y 2)</div>
                    <div class="metric-value">{total_registros_tabla:,}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k_col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon-box" style="color: #eab308;"><i class="fa-solid fa-circle-dot"></i></div>
                <div class="metric-content">
                    <div class="metric-title">Etapa 1</div>
                    <div class="metric-value">{total_etapa_1:,}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k_col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon-box" style="color: #22c55e;"><i class="fa-solid fa-circle-dot"></i></div>
                <div class="metric-content">
                    <div class="metric-title">Etapa 2</div>
                    <div class="metric-value">{total_etapa_2:,}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>🗺️ Mapa de Registros — 🟡 Etapa 1 (Amarillo) | 🟢 Etapa 2 (Verde)</p>",
            unsafe_allow_html=True,
        )

        df_mapa_tabla = (
            df_tabla_filtrada.dropna(subset=["lat_calc", "lon_calc"])
            if not df_tabla_filtrada.empty and "lat_calc" in df_tabla_filtrada.columns
            else pd.DataFrame()
        )
        
        if not df_mapa_tabla.empty:
            m_lat_t = pd.to_numeric(df_mapa_tabla["lat_calc"], errors="coerce").mean()
            m_lon_t = pd.to_numeric(df_mapa_tabla["lon_calc"], errors="coerce").mean()
            if pd.isna(m_lat_t) or pd.isna(m_lon_t):
                m_lat_t, m_lon_t = 21.8853, -102.2916
        else:
            m_lat_t, m_lon_t = 21.8853, -102.2916

        mapa_tabla_tab = folium.Map(location=[m_lat_t, m_lon_t], zoom_start=12, tiles=None)
        agregar_capas_base(mapa_tabla_tab)

        for _, row in df_mapa_tabla.iterrows():
            try:
                lat_val = float(row["lat_calc"])
                lon_val = float(row["lon_calc"])
                if pd.isna(lat_val) or pd.isna(lon_val):
                    continue
            except:
                continue

            etapa_val = str(row.get("etapa", "")).strip().lower()
            if etapa_val in ["1", "etapa 1"]:
                color_punto = "#eab308"
            else:
                color_punto = "#22c55e"

            nombre = str(row.get("Nombre", "N/A"))
            predio_val = str(row.get("Predio_Viv", "N/A"))
            serie_val = str(row.get("_Serie", "N/A"))
            medidor_val = str(row.get("Medidor", "N/A"))
            colonia_val = str(row.get("Colonia", "N/A"))
            etapa_txt = str(row.get("etapa", "N/A"))

            popup_html = f"""
            <div style="font-size: 11px; line-height: 1.4; color: #000000;">
                <b>Cliente:</b> {nombre}<br>
                <b>Predio:</b> {predio_val}<br>
                <b>Serie:</b> {serie_val}<br>
                <b>Medidor:</b> {medidor_val}<br>
                <b>Colonia:</b> {colonia_val}<br>
                <b>Etapa:</b> {etapa_txt}
            </div>
            """
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=3.5,
                color=color_punto,
                fill=True,
                fill_color=color_punto,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(mapa_tabla_tab)

        st_folium(
            mapa_tabla_tab,
            width=None,
            height=350,
            key="mapa_usuarios_miaa_conmedidor_geom_final",
            returned_objects=[],
        )

    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    if total_registros_tabla > 0:
        TAMANO_PAGINA_BD = 10
        total_paginas_bd = math.ceil(total_registros_tabla / TAMANO_PAGINA_BD)

        col_p_bd1, col_p_bd2 = st.columns([2, 1])
        with col_p_bd1:
            pagina_actual_bd = st.selectbox(
                f"Seleccionar Hoja / Página (Total registros filtrados: {total_registros_tabla:,})",
                options=list(range(1, total_paginas_bd + 1)),
                format_func=lambda x: f"Hoja {x} de {total_paginas_bd} (Registros {(x-1)*TAMANO_PAGINA_BD + 1} al {min(x*TAMANO_PAGINA_BD, total_registros_tabla)})",
                key="select_pagina_bd_completa",
            )
        with col_p_bd2:
            st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: #38bdf8; font-weight: bold;'>Mostrando 10 por hoja</div>", unsafe_allow_html=True)

        inicio_idx_bd = (pagina_actual_bd - 1) * TAMANO_PAGINA_BD
        fin_idx_bd = inicio_idx_bd + TAMANO_PAGINA_BD
        
        df_tabla_filtrada = df_tabla_filtrada.loc[:, ~df_tabla_filtrada.columns.duplicated()]
        df_pagina_bd_final = df_tabla_filtrada.iloc[inicio_idx_bd:fin_idx_bd].copy()

        st.dataframe(df_pagina_bd_final, use_container_width=True, height=350, hide_index=True)
    else:
        st.info("No se encontraron registros en la base de datos con los filtros aplicados.")

# ------------------------------------------------------------------------------
# SECCIÓN 15 PESTAÑA: REGISTRO DE INSTALACIONES INTERNO (Google Sheets)
# ------------------------------------------------------------------------------
with tab_sheets_interno:
    st.markdown(
        "<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📑 Registro de Instalaciones Interno (Google Sheets)</p>",
        unsafe_allow_html=True,
    )

    if not df_sheets_interno.empty:
        df_sheets_interno.columns = [str(c).strip() for c in df_sheets_interno.columns]
        
        cols_lower = {c.lower(): c for c in df_sheets_interno.columns}
        
        col_fecha_sheets = cols_lower.get("fecha de instalacion", cols_lower.get("fecha", None))
        col_inst_sheets = cols_lower.get("instalados", None)
        col_cuadro_sheets = cols_lower.get("cuadro", None)
        col_reg_sheets = cols_lower.get("registro", None)
        col_ret_sheets = cols_lower.get("retirados", None)
        col_sin_sheets = cols_lower.get("sin medidor", cols_lower.get("sin_medidor", None))

        if col_fecha_sheets and col_fecha_sheets in df_sheets_interno.columns:
            df_sheets_interno["_fecha_dt_sheets"] = pd.to_datetime(
                df_sheets_interno[col_fecha_sheets], dayfirst=True, errors="coerce"
            )
        else:
            df_sheets_interno["_fecha_dt_sheets"] = pd.NaT

        for col_name in [col_inst_sheets, col_cuadro_sheets, col_reg_sheets, col_ret_sheets, col_sin_sheets]:
            if col_name and col_name in df_sheets_interno.columns:
                df_sheets_interno[col_name] = pd.to_numeric(
                    df_sheets_interno[col_name].astype(str).str.replace(",", ""),
                    errors="coerce",
                ).fillna(0)

        if col_inst_sheets and col_inst_sheets in df_sheets_interno.columns:
            total_medidores_sheets = int(df_sheets_interno[col_inst_sheets].sum())
            df_con_instalacion = df_sheets_interno[df_sheets_interno[col_inst_sheets] > 0]
            
            if not df_con_instalacion.empty:
                promedio_diario = round(df_con_instalacion[col_inst_sheets].mean(), 1)
                max_diario = int(df_con_instalacion[col_inst_sheets].max())
                min_diario = int(df_con_instalacion[col_inst_sheets].min())
            else:
                promedio_diario = 0.0
                max_diario = 0
                min_diario = 0
        else:
            total_medidores_sheets = 0
            promedio_diario = 0.0
            max_diario = 0
            min_diario = 0

        k_s1, k_s2, k_s3, k_s4 = st.columns(4)

        with k_s1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-gauge"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Medidores Instalados</div>
                        <div class="metric-value">{total_medidores_sheets:,}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with k_s2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-chart-line"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Promedio Diario</div>
                        <div class="metric-value">{promedio_diario:,.1f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with k_s3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-arrow-trend-up"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Máximo en un Día</div>
                        <div class="metric-value">{max_diario:,}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with k_s4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-arrow-trend-down"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Mínimo en un Día</div>
                        <div class="metric-value">{min_diario:,}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(
                "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Día</p>",
                unsafe_allow_html=True,
            )
            if col_fecha_sheets and col_inst_sheets:
                fig_bar_inst = px.bar(
                    df_sheets_interno,
                    x=col_fecha_sheets,
                    y=col_inst_sheets,
                    text=col_inst_sheets,
                    color_discrete_sequence=["#3b82f6"],
                )
                fig_bar_inst.update_traces(textposition="outside", textfont_size=10)
                fig_bar_inst.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    margin=dict(t=20, b=5, l=5, r=5),
                    height=300,
                    xaxis_title=None,
                    yaxis_title=None,
                )
                st.plotly_chart(
                    fig_bar_inst, use_container_width=True, key="sheets_inst_dia"
                )

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        g_col1, g_col2, g_col3 = st.columns(3)

        with g_col1:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones por Mes</p>",
                    unsafe_allow_html=True,
                )
                if not df_sheets_interno["_fecha_dt_sheets"].isna().all() and col_inst_sheets:
                    df_mes_sheets = df_sheets_interno.dropna(subset=["_fecha_dt_sheets"]).copy()
                    df_mes_sheets["periodo_mes"] = df_mes_sheets["_fecha_dt_sheets"].dt.to_period("M")
                    
                    df_mes_group = df_mes_sheets.groupby("periodo_mes", as_index=False)[col_inst_sheets].sum()
                    df_mes_group.columns = ["Periodo", "Cantidad"]
                    
                    df_mes_group = df_mes_group[df_mes_group["Cantidad"] > 0]

                    meses_es = {
                        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                    }
                    df_mes_group["Mes"] = df_mes_group["Periodo"].apply(
                        lambda x: f"{meses_es[x.month]} {x.year}"
                    )
                    df_mes_group = df_mes_group.sort_values(by="Periodo", ascending=True)

                    colores_barras_mes = ["#1e3a8a", "#3b82f6"] * ((len(df_mes_group) // 2) + 1)
                    max_cant_mes = df_mes_group["Cantidad"].max() if not df_mes_group.empty else 10

                    fig_mes_h_sheets = px.bar(
                        df_mes_group,
                        x="Cantidad",
                        y="Mes",
                        orientation="h",
                        text="Cantidad",
                        color="Mes",
                        color_discrete_sequence=colores_barras_mes,
                    )
                    fig_mes_h_sheets.update_traces(textposition="outside", textfont_size=10)
                    fig_mes_h_sheets.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#ffffff",
                        margin=dict(t=10, b=5, l=5, r=30),
                        height=280,
                        xaxis=dict(showgrid=False, showticklabels=False, title=None, range=[0, max_cant_mes * 1.25]),
                        yaxis=dict(showgrid=False, title=None, tickfont=dict(size=10), categoryorder="array", categoryarray=df_mes_group["Mes"].tolist()),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_mes_h_sheets, use_container_width=True, key="sheets_instalaciones_mes")
                else:
                    st.info("No hay datos de fechas válidos para agrupar por mes.")

        with g_col2:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Medidores en Cuadro vs Registro</p>",
                    unsafe_allow_html=True,
                )
                if col_cuadro_sheets and col_reg_sheets:
                    sum_cuadro = df_sheets_interno[col_cuadro_sheets].sum()
                    sum_registro = df_sheets_interno[col_reg_sheets].sum()
                    df_pie_cr = pd.DataFrame({
                        "Tipo": ["Cuadro", "Registro"],
                        "Cantidad": [sum_cuadro, sum_registro],
                    })

                    fig_pie_cr = px.pie(
                        df_pie_cr,
                        names="Tipo",
                        values="Cantidad",
                        hole=0.5,
                        color="Tipo",
                        color_discrete_map={"Cuadro": "#0066cc", "Registro": "#e83e8c"},
                    )
                    fig_pie_cr.update_traces(textinfo="value+percent", textfont=dict(size=11))
                    fig_pie_cr.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#ffffff",
                        margin=dict(t=20, b=5, l=5, r=5),
                        height=280,
                        legend=dict(orientation="h", y=-0.1, x=0),
                    )
                    st.plotly_chart(
                        fig_pie_cr, use_container_width=True, key="sheets_pie_cuadro_reg"
                    )

        with g_col3:
            with st.container(border=True):
                st.markdown(
                    "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Evolución de Retirados y Sin Medidor</p>",
                    unsafe_allow_html=True,
                )
                if col_fecha_sheets and col_ret_sheets and col_sin_sheets:
                    fig_ret_sin = px.bar(
                        df_sheets_interno,
                        x=col_fecha_sheets,
                        y=[col_ret_sheets, col_sin_sheets],
                        barmode="group",
                        color_discrete_map={
                            col_ret_sheets: "#f59e0b",
                            col_sin_sheets: "#f43f5e",
                        },
                    )
                    fig_ret_sin.for_each_trace(lambda t: t.update(name="Retirados" if t.name == col_ret_sheets else "Sin Medidor"))
                    
                    fig_ret_sin.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#ffffff",
                        margin=dict(t=20, b=5, l=5, r=5),
                        height=280,
                        xaxis_title=None,
                        yaxis_title=None,
                        legend=dict(orientation="h", y=1.1, x=0),
                    )
                    st.plotly_chart(
                        fig_ret_sin, use_container_width=True, key="sheets_retirados_sin"
                    )
                else:
                    st.info("No se encontraron las columnas 'Retirados' o 'sin medidor' en el archivo.")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(
                "<p style='font-size:13px; font-weight:bold; margin-bottom:8px;'>📋 Tabla de Datos - Google Sheets (Instalaciones)</p>",
                unsafe_allow_html=True,
            )

            columnas_deseadas = [
                col_fecha_sheets,
                col_inst_sheets,
                col_cuadro_sheets,
                col_reg_sheets,
                col_ret_sheets,
                col_sin_sheets,
            ]
            cols_existentes = [c for c in columnas_deseadas if c and c in df_sheets_interno.columns]
            df_tabla_filtrada_sheets = df_sheets_interno[cols_existentes].copy()

            st.dataframe(df_tabla_filtrada_sheets, use_container_width=True, height=320)
    else:
        st.warning(
            "No se pudo cargar la información de la hoja 'Instalaciones' del archivo de Google Sheets."
        )
