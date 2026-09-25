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
# SECCIÓN 2: FUNCIONES DE CONEXIÓN Y DATOS (API, MYSQL Y GOOGLE SHEETS)
# ==============================================================================

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"


@st.cache_data(ttl=300)
def cargar_datos_api():
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
  """Carga los datos de Google Sheets de la pestaña 'Instalaciones'."""
  try:
    sheet_id = "1Ovj2DZ19Y8H4BtamnVwB71c2dyHC3dyVmau-tMbWre8"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Instalaciones"
    df_sheets = pd.read_csv(url_csv)
    return df_sheets
  except Exception:
    try:
      # Opción alternativa general si falla el nombre de pestaña específico
      sheet_id = "1Ovj2DZ19Y8H4BtamnVwB71c2dyHC3dyVmau-tMbWre8"
      url_csv_alt = (
          f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
      )
      return pd.read_csv(url_csv_alt)
    except Exception:
      return pd.DataFrame()


# ==============================================================================
# SECCIÓN 3: FUNCIONES AUXILIARES PARA MAPAS
# ==============================================================================


def agregar_capas_base(m):
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
# SECCIÓN 5: CABECERA SUPERIOR
# ==============================================================================

try:
  if not df.empty and "fecha_dt" in df.columns:
    max_dt = df["fecha_dt"].max()
    hoy = (
        pd.to_datetime(max_dt).date()
        if pd.notna(max_dt)
        else datetime.date.today()
    )
  else:
    hoy = datetime.date.today()
except Exception:
  hoy = datetime.date.today()

fecha_actual_str = pd.to_datetime(hoy).strftime("%d/%m/%Y")

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
# SECCIÓN 6: BARRA LATERAL
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
    index=0,
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
if col_c1.button("Marcar todos"):
  for p in lista_poligonos:
    st.session_state[f"chk_pol_{p}"] = True
if col_c2.button("Desmarcar"):
  for p in lista_poligonos:
    st.session_state[f"chk_pol_{p}"] = False

with st.sidebar.container(height=220):
  poligonos_seleccionados = []
  for pol in lista_poligonos:
    if st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}"):
      poligonos_seleccionados.append(pol)

df_metas_filtrado = (
    df_metas_valido[
        df_metas_valido["Poligono_de_instalacion"]
        .astype(str)
        .isin(poligonos_seleccionados)
    ].copy()
    if not df_metas_valido.empty and "Poligono_de_instalacion" in df_metas_valido.columns
    else df_metas_valido.copy()
)

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

# Tabla Eficiencia
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
# SECCIÓN 7: ESTRUCTURA DE PESTAÑAS (Con la nueva pestaña solicitada)
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
        fig_pie = go.Figure(
            go.Pie(
                labels=df_tipo_inst["Tipo"],
                values=df_tipo_inst["Cantidad"],
                hole=0.5,
                domain=dict(x=[0.0, 0.62], y=[0.05, 0.95]),
                textinfo="value+percent",
                marker=dict(
                    colors=[
                        "#38bdf8",
                        "#4ade80",
                        "#f59e0b",
                        "#a855f7",
                        "#f43f5e",
                        "#64748b",
                    ]
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
        df_cr = df_filtrado.copy()
        df_cr["categoria_cr"] = df_cr["tipo_instalacion_nombre"].apply(
            lambda x: (
                "CUADRO"
                if "CUADRO" in str(x).upper()
                else ("REGISTRO" if "REGISTRO" in str(x).upper() else None)
            )
        )
        df_cr_val = df_cr.dropna(subset=["categoria_cr"])
        if not df_cr_val.empty:
          df_counts_cr = (
              df_cr_val["categoria_cr"].value_counts().reset_index()
          )
          df_counts_cr.columns = ["Tipo", "Cantidad"]
          fig_cr = go.Figure(
              go.Pie(
                  labels=df_counts_cr["Tipo"],
                  values=df_counts_cr["Cantidad"],
                  hole=0.6,
                  marker=dict(
                      colors=[
                          "#0066cc" if t == "CUADRO" else "#e83e8c"
                          for t in df_counts_cr["Tipo"]
                      ]
                  ),
              )
          )
        else:
          fig_cr = go.Figure(
              go.Pie(labels=["Sin Datos"], values=[0], hole=0.6)
          )
      else:
        fig_cr = go.Figure(go.Pie(labels=["Sin Datos"], values=[0], hole=0.6))
      fig_cr.update_layout(
          plot_bgcolor="rgba(0,0,0,0)",
          paper_bgcolor="rgba(0,0,0,0)",
          font_color="#ffffff",
          margin=dict(t=5, b=5, l=5, r=5),
          height=230,
      )
      st.plotly_chart(
          fig_cr, use_container_width=True, key="dash_prin_cuadro_vs_reg"
      )

  col_inf1, col_inf2 = st.columns([1, 1.6])
  with col_inf1:
    with st.container(border=True):
      st.markdown(
          "<p style='font-size:12px; margin-bottom:4px;"
          " font-weight:bold;'>Eficiencia por Colonia y Polígono</p>",
          unsafe_allow_html=True,
      )
      if not df_eficiencia.empty:
        st.dataframe(
            df_eficiencia, use_container_width=True, hide_index=True, height=330
        )
      else:
        st.info("No se encontraron datos para los polígonos seleccionados.")

  with col_inf2:
    col_map_h, col_graf_h = st.columns([2.2, 1])
    with col_map_h:
      with st.container(border=True):
        st.markdown(
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Mapa"
            " de Instalaciones</p>",
            unsafe_allow_html=True,
        )
        df_mapa_valido = (
            df_filtrado.dropna(subset=["latitud", "longitud"])
            if not df_filtrado.empty
            else pd.DataFrame()
        )
        map_lat = (
            df_mapa_valido["latitud"].mean()
            if not df_mapa_valido.empty
            else lat_centro
        )
        map_lon = (
            df_mapa_valido["longitud"].mean()
            if not df_mapa_valido.empty
            else lon_centro
        )
        mapa_miaa = folium.Map(
            location=[map_lat, map_lon], zoom_start=12, tiles=None
        )
        agregar_capas_base(mapa_miaa)
        for _, row in df_mapa_valido.iterrows():
          color_punto = (
              "#f59e0b"
              if row.get("usuarioExterno", False)
              else "#a855f7"
          )
          folium.CircleMarker(
              location=[float(row["latitud"]), float(row["longitud"])],
              radius=2.5,
              color=color_punto,
              fill=True,
              fill_color=color_punto,
              fill_opacity=0.7,
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
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Instalaciones"
            " por Mes</p>",
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
        else:
          df_mes = pd.DataFrame({"Mes": ["Sin datos"], "Cantidad": [0]})
        fig_mes_h = px.bar(
            df_mes,
            x="Cantidad",
            y="Mes",
            orientation="h",
            text="Cantidad",
            color_discrete_sequence=["#3b82f6"],
        )
        fig_mes_h.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
            margin=dict(t=2, b=2, l=5, r=40),
            height=130,
            xaxis=dict(showgrid=False, showticklabels=False, title=None),
            yaxis=dict(showgrid=False, title=None),
            showlegend=False,
        )
        st.plotly_chart(
            fig_mes_h, use_container_width=True, key="dash_prin_instalaciones_mes"
        )

# ------------------------------------------------------------------------------
# PESTAÑA: ANÁLISIS DE ANOMALÍAS
# ------------------------------------------------------------------------------
with tab_anomalias:
  st.markdown(
      "<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>⚠️"
      " Análisis Completo de Anomalías</p>",
      unsafe_allow_html=True,
  )
  df_con_anomalia = (
      df_filtrado[
          df_filtrado["anomalia_nombre"] != "SIN ANOMALÍA / REGULAR"
      ].copy()
      if not df_filtrado.empty and "anomalia_nombre" in df_filtrado.columns
      else pd.DataFrame()
  )
  st.metric(
      "Total Registros con Anomalía",
      f"{len(df_con_anomalia):,}" if not df_con_anomalia.empty else "0",
  )
  if not df_con_anomalia.empty:
    st.dataframe(df_con_anomalia, use_container_width=True)
  else:
    st.success("No hay anomalías registradas para los filtros seleccionados.")

# ------------------------------------------------------------------------------
# PESTAÑA: MAPA DE POLÍGONOS DE INSTALACIÓN
# ------------------------------------------------------------------------------
shapely_polygons = {}
lat_acumuladas, lon_acumuladas = [], []
with tab_poligonos:
  st.markdown(
      "<p style='font-size:16px; font-weight:bold;'>🗺️ Mapa de Polígonos de"
      " Instalación</p>",
      unsafe_allow_html=True,
  )
  if not df_poligonos.empty:
    st.dataframe(df_poligonos.head(20), use_container_width=True)
  else:
    st.info("Sin datos de polígonos disponibles.")

# ------------------------------------------------------------------------------
# PESTAÑA: PERSONAL (EXTERNO Y MIAA)
# ------------------------------------------------------------------------------
with tab_personal:
  st.markdown(
      "<p style='font-size:16px; font-weight:bold;'>👥 Personal (Externo y"
      " MIAA)</p>",
      unsafe_allow_html=True,
  )
  sub_ext, sub_miaa_int = st.tabs(["👷 Personal Externo", "👤 Personal MIAA"])
  with sub_ext:
    st.dataframe(df_externo, use_container_width=True)
  with sub_miaa_int:
    st.dataframe(df_miaa_pers, use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA: TABLA BASE DE DATOS COMPLETA
# ------------------------------------------------------------------------------
with tab_tabla:
  st.markdown(
      "<p style='font-size:16px; font-weight:bold;'>📋 Tabla Base de Datos"
      " Completa</p>",
      unsafe_allow_html=True,
  )
  st.dataframe(df_filtrado, use_container_width=True)

# ------------------------------------------------------------------------------
# NUEVA PESTAÑA: REGISTRO DE INSTALACIONES INTERNO (Google Sheets)
# ------------------------------------------------------------------------------
with tab_sheets_interno:
  st.markdown(
      "<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📑"
      " Registro de Instalaciones Interno (Google Sheets)</p>",
      unsafe_allow_html=True,
  )

  if not df_sheets_interno.empty:
    # Limpieza de nombres de columnas y conversión numérica
    df_sheets_interno.columns = [
        str(c).strip() for c in df_sheets_interno.columns
    ]
    cols_numericas = [
        "Instalados",
        "Cuadro",
        "Registro",
        "Retirados",
        "sin medidor",
    ]
    for col in cols_numericas:
      if col in df_sheets_interno.columns:
        df_sheets_interno[col] = pd.to_numeric(
            df_sheets_interno[col].astype(str).str.replace(",", ""),
            errors="coerce",
        ).fillna(0)

    # Tarjetas KPI con los totales del Google Sheets
    tot_inst = (
        int(df_sheets_interno["Instalados"].sum())
        if "Instalados" in df_sheets_interno.columns
        else 0
    )
    tot_cuadro = (
        int(df_sheets_interno["Cuadro"].sum())
        if "Cuadro" in df_sheets_interno.columns
        else 0
    )
    tot_reg = (
        int(df_sheets_interno["Registro"].sum())
        if "Registro" in df_sheets_interno.columns
        else 0
    )
    tot_ret = (
        int(df_sheets_interno["Retirados"].sum())
        if "Retirados" in df_sheets_interno.columns
        else 0
    )
    tot_sin = (
        int(df_sheets_interno["sin medidor"].sum())
        if "sin medidor" in df_sheets_interno.columns
        else 0
    )

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
      st.markdown(
          f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-circle-check"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Instalados</div>
                        <div class="metric-value">{tot_inst:,}</div>
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )
    with sc2:
      st.markdown(
          f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-square"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Cuadro</div>
                        <div class="metric-value">{tot_cuadro:,}</div>
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )
    with sc3:
      st.markdown(
          f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-book"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Registro</div>
                        <div class="metric-value">{tot_reg:,}</div>
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )
    with sc4:
      st.markdown(
          f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-rotate-left"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Retirados</div>
                        <div class="metric-value">{tot_ret:,}</div>
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )
    with sc5:
      st.markdown(
          f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Sin Medidor</div>
                        <div class="metric-value">{tot_sin:,}</div>
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )

    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

    # Gráficos interactivos Plotly basados en los requerimientos y captura de imagen
    g_col1, g_col2 = st.columns(2)

    with g_col1:
      with st.container(border=True):
        st.markdown(
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Evolución"
            " Diaria: Cuadro vs Registro</p>",
            unsafe_allow_html=True,
        )
        if (
            "Fecha de Instalacion" in df_sheets_interno.columns
            and "Cuadro" in df_sheets_interno.columns
            and "Registro" in df_sheets_interno.columns
        ):
          fig_ev_cr = px.bar(
              df_sheets_interno,
              x="Fecha de Instalacion",
              y=["Cuadro", "Registro"],
              barmode="stack",
              color_discrete_map={"Cuadro": "#0066cc", "Registro": "#e83e8c"},
          )
          fig_ev_cr.update_layout(
              plot_bgcolor="rgba(0,0,0,0)",
              paper_bgcolor="rgba(0,0,0,0)",
              font_color="#ffffff",
              margin=dict(t=20, b=5, l=5, r=5),
              height=300,
              xaxis_title=None,
              yaxis_title=None,
              legend=dict(orientation="h", y=1.1, x=0),
          )
          st.plotly_chart(
              fig_ev_cr, use_container_width=True, key="sheets_cuadro_registro"
          )

    with g_col2:
      with st.container(border=True):
        st.markdown(
            "<p style='font-size:12px; margin-bottom:4px; font-weight:bold;'>Evolución"
            " Diaria: Retirados y Sin Medidor</p>",
            unsafe_allow_html=True,
        )
        if (
            "Fecha de Instalacion" in df_sheets_interno.columns
            and "Retirados" in df_sheets_interno.columns
            and "sin medidor" in df_sheets_interno.columns
        ):
          fig_ev_rs = px.line(
              df_sheets_interno,
              x="Fecha de Instalacion",
              y=["Retirados", "sin medidor"],
              markers=True,
              color_discrete_map={
                  "Retirados": "#f59e0b",
                  "sin medidor": "#f43f5e",
              },
          )
          fig_ev_rs.update_layout(
              plot_bgcolor="rgba(0,0,0,0)",
              paper_bgcolor="rgba(0,0,0,0)",
              font_color="#ffffff",
              margin=dict(t=20, b=5, l=5, r=5),
              height=300,
              xaxis_title=None,
              yaxis_title=None,
              legend=dict(orientation="h", y=1.1, x=0),
          )
          st.plotly_chart(
              fig_ev_rs, use_container_width=True, key="sheets_retirados_sin"
          )

    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
      st.markdown(
          "<p style='font-size:13px; font-weight:bold; margin-bottom:8px;'>📋"
          " Tabla de Datos - Google Sheets (Instalaciones)</p>",
          unsafe_allow_html=True,
      )
      st.dataframe(df_sheets_interno, use_container_width=True, height=350)
  else:
    st.warning(
        "No se pudo cargar la información del archivo de Google Sheets"
        " especificado. Verifica que sea público o accesible."
    )
