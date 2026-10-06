import datetime
import json
import folium
from folium.plugins import Fullscreen
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
    /* Importar FontAwesome para los iconos */
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Forzar que la barra lateral nunca se oculte ni colapse */
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

    /* Separador visual para las pestañas de Streamlit */
    .stTabs {
        margin-top: 5px;
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

    /* Estilos para Tarjetas Contenedoras de Gráficos (st.container(border=True)) */
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

    /* Fondo transparente para los gráficos Plotly */
    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# ==============================================================================
# SECCIÓN 2: FUNCIONES DE CONEXIÓN Y DATOS (API Y BASE DE DATOS)
# ==============================================================================

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"


@st.cache_data(ttl=300)
def cargar_datos_api():
  """Conecta con la API externa de MIAA usando credenciales de st.secrets para obtener registros de instalaciones."""
  try:
    usuario = st.secrets["api"]["usuario"]
    password = st.secrets["api"]["password"]
    res_login = requests.post(
        url_login,
        json={"username": usuario, "password": password},
        headers={"Content-Type": "application/json"},
    )
    if res_login.status_code == 200:
      token = res_login.json().get("token") or res_login.json().get(
          "access_token"
      )
      if token:
        res_inst = requests.get(
            url_instalaciones,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if res_inst.status_code == 200:
          return res_inst.json()
    return None
  except Exception:
    return None


@st.cache_data(ttl=600)
def cargar_metas_db():
  """Consulta la base de datos MySQL para obtener el diccionario de metas e instalaciones por colonia."""
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
  """Consulta la base de datos MySQL para extraer los vértices y metadatos de los polígonos geográficos."""
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
  """Consulta la base de datos MySQL para obtener el catálogo de tipos de instalación."""
  try:
    engine = create_engine(st.secrets["mysql"]["connection_string"])
    query = "SELECT ID, tipo_instalacion FROM Diccionario_tipo_instalacion"
    return pd.read_sql(query, con=engine)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_anomalias_db():
  """Consulta la base de datos MySQL para obtener el diccionario de anomalías."""
  try:
    engine = create_engine(st.secrets["mysql"]["connection_string"])
    query = "SELECT ID, anomalia FROM Diccionario_anomalias"
    return pd.read_sql(query, con=engine)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_google_sheets_interno():
  """Carga los datos de Google Sheets (pestaña Instalaciones)."""
  try:
    sheet_id = "1Ovj2DZ19Y8H4BtamnVwB71c2dyHC3dyVmau-tMbWre8"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Instalaciones"
    return pd.read_csv(url_csv)
  except Exception:
    return pd.DataFrame()


# ==============================================================================
# SECCIÓN 3: FUNCIONES AUXILIARES PARA MAPAS
# ==============================================================================


def agregar_capas_base(m):
  """Agrega las capas base de mapa (Carto Dark Matter con API Key) y controles de pantalla completa."""
  api_key = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"

  folium.TileLayer(
      tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key}",
      name="Vista Nocturna",
      attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains="abcd",
      max_zoom=20,
      control=False,
  ).add_to(m)

  Fullscreen(
      position="topright",
      title="Ampliar Mapa",
      cancel_title="Salir de pantalla completa",
  ).add_to(m)


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

# Mapeo del Diccionario de Tipos de Instalación
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

# Mapeo del Diccionario de Anomalías
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
# SECCIÓN 5: CABECERA SUPERIOR DEL TÍTULO DE LA PÁGINA (DATOS YA DISPONIBLES)
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

# ------------------------------------------------------------------------------
# INDICADOR DE ESTADO DE LA API Y BOTÓN DE RECONEXIÓN
# ------------------------------------------------------------------------------
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

# CONSTRUCCIÓN DE LA TABLA DE EFICIENCIA
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
    tab_poligonos,
    tab_personal,
    tab_anomalias,
    tab_tabla,
    tab_sheets_interno,
) = st.tabs([
    "📊 Dashboard Principal",
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
          "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones"
          " por Día</p>",
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
          "<p style='font-size:12px; margin-bottom:4px;"
          " font-weight:bold;'>Distribución por Tipo de Instalación</p>",
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
          "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Cuadro"
          " vs Registro</p>",
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
        fig_cr = go.Figure(go.Pie(labels=["Sin Datos"], values=[0], hole=
