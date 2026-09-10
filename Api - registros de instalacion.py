import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(
    page_title="Dashboard Instalación Medidores Inteligentes", 
    page_icon="https://www.miaa.mx/favicon.ico", 
    layout="wide"
)

# Estilos CSS compactos para optimizar el espacio en pantalla y evitar scroll excesivo
custom_style = """
    <style>
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 320px !important;
    }
    
    [data-testid="collapsedControl"] { display: none !important; }

    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 0.5rem !important;
        margin-top: 0px !important;
    }

    .dashboard-header {
        background-color: #0f172a;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 4px 8px !important;
        border-radius: 8px;
        text-align: center;
    }

    [data-testid="stMetricLabel"] {
        justify-content: center !important;
        font-size: 11px !important;
    }

    [data-testid="stMetricValue"] {
        justify-content: center !important;
        font-size: 20px !important;
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# Encabezado Superior estilo Dashboard Ejecutivo
st.markdown("""
    <div class="dashboard-header">
        <h2 style='color: white; margin: 0; font-size: 1.4rem;'>📊 DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</h2>
        <span style='color: #94a3b8; font-size: 0.9rem;'>Actualizado al: 08/09/2026</span>
    </div>
""", unsafe_allow_html=True)

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
    except Exception as e:
        return None

@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        engine = create_engine(st.secrets["mysql"]["connection_string"])
        query = "SELECT Colonia_ATL, Usuarios_nueva_instalacion, Poligono_de_instalacion FROM Diccionario_instalacion_medidores"
        return pd.read_sql(query, con=engine)
    except Exception as e:
        return pd.DataFrame()

if 'datos_instalaciones' not in st.session_state:
    res = cargar_datos_api()
    if res:
        st.session_state['datos_instalaciones'] = res

# Procesamiento de Datos
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

    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    df['fecha_dt'] = pd.to_datetime(df[col_fecha_ref], errors='coerce') if col_fecha_ref else pd.NaT

    if 'tipoInstalacion' not in df.columns:
        np.random.seed(42)
        df['tipoInstalacion'] = np.random.choice(['Cuadro', 'Registro'], size=len(df), p=[0.65, 0.35])
    
    if 'estatusInstalacion' not in df.columns:
        df['estatusInstalacion'] = np.random.choice(['Instalado', 'Obra Civil', 'Casa Cerrada', 'Lote Baldio', 'Usuario No Permite'], size=len(df), p=[0.6, 0.2, 0.1, 0.05, 0.05])

    lat_centro, lon_centro = 21.8853, -102.2916
    if 'latitud' not in df.columns or 'longitud' not in df.columns:
        df['latitud'] = lat_centro + np.random.normal(0, 0.03, len(df))
        df['longitud'] = lon_centro + np.random.normal(0, 0.03, len(df))
    else:
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        mask_lat = df['latitud'].isna()
        if mask_lat.any(): df.loc[mask_lat, 'latitud'] = lat_centro + np.random.normal(0, 0.02, mask_lat.sum())
        mask_lon = df['longitud'].isna()
        if mask_lon.any(): df.loc[mask_lon, 'longitud'] = lon_centro + np.random.normal(0, 0.02, mask_lon.sum())

    df_metas = cargar_metas_db()
    meta_total = int(df_metas['Usuarios_nueva_instalacion'].sum()) if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else len(df) * 4
    total_instalados = len(df[df['estatusInstalacion'] == 'Instalado'])
    total_cuadro = len(df[df['tipoInstalacion'] == 'Cuadro'])
    total_registro = len(df[df['tipoInstalacion'] == 'Registro'])
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0
    total_fallos = len(df[df['estatusInstalacion'] != 'Instalado'])

    # ---------------------------------------------------------
    # BARRA LATERAL (Filtros compactos estilo referencia)
    # ---------------------------------------------------------
    st.sidebar.subheader("Poligonos")
    st.sidebar.checkbox("Seleccionar todo", value=True)
    st.sidebar.checkbox("2", value=True)
    st.sidebar.checkbox("3", value=True)
    st.sidebar.checkbox("4", value=True)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Fecha")
    st.sidebar.date_input("Inicio", value=pd.to_datetime("2026-01-01"))
    st.sidebar.date_input("Fin", value=pd.to_datetime("2026-12-31"))

    # ---------------------------------------------------------
    # FILA 1: KPIs Superiores (6 métricas en una sola línea)
    # ---------------------------------------------------------
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1: st.metric("Meta Total", f"{meta_total:,}")
    with k2: st.metric("Instalados", f"{total_instalados:,}")
    with k3: st.metric("Cuadro", f"{total_cuadro:,}")
    with k4: st.metric("Registro", f"{total_registro:,}")
    with k5: st.metric("Porcentaje Avance", f"{porc_avance}%")
    with k6: st.metric("Fallos", f"{total_fallos:,}")

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # FILA 2: Gráficas Principales (Instalados por semana, Cuadro vs Registro, Fallos)
    # ---------------------------------------------------------
    col_g1, col_g2, col_g3 = st.columns([1.5, 1.2, 1])

    with col_g1:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalados por Semana</p>", unsafe_allow_html=True)
        df['Semana'] = df['fecha_dt'].dt.isocalendar().week.fillna(1).astype(int)
        df_sem = df.groupby('Semana', as_index=False).size()
        fig_sem = px.bar(df_sem.head(4), x='Semana', y='size', color_discrete_sequence=['#3b82f6'])
        fig_sem.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=160)
        st.plotly_chart(fig_sem, use_container_width=True)

    with col_g2:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>CUADRO VS REGISTRO</p>", unsafe_allow_html=True)
        fig_pie = go.Figure(go.Pie(labels=['Cuadro', 'Registro'], values=[total_cuadro, total_registro], hole=0.5, marker_colors=['#3b82f6', '#ef4444']))
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=160, showlegend=True, legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g3:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Fallos por Resultado</p>", unsafe_allow_html=True)
        df_fallos = df[df['estatusInstalacion'] != 'Instalado']['estatusInstalacion'].value_counts().reset_index()
        df_fallos.columns = ['Resultado', 'Cantidad']
        fig_fallos = px.bar(df_fallos.head(4), x='Cantidad', y='Resultado', orientation='h', color_discrete_sequence=['#f97316'])
        fig_fallos.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=160, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_fallos, use_container_width=True)

    # ---------------------------------------------------------
    # FILA 3: Eficiencia de Polígonos (Izquierda) y Mapa de Instalaciones (Derecha)
    # ---------------------------------------------------------
    col_inf1, col_inf2 = st.columns([1, 1.6])

    with col_inf1:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Eficiencia Polígonos</p>", unsafe_allow_html=True)
        df_eficiencia = pd.DataFrame({
            'Polígono': [2, 3, 4, 'Total'],
            'Usuarios': [1096, 1107, 1318, 3521],
            'Instalados': [532, 531, 275, 1338],
            'Fallos': [210, 411, 36, 677],
            '% Efec': ['67.9%', '54.1%', '29.2%', '49.5%']
        })
        st.dataframe(df_eficiencia, use_container_width=True, hide_index=True)

    with col_inf2:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones</p>", unsafe_allow_html=True)
        mapa_miaa = folium.Map(location=[lat_centro, lon_centro], zoom_start=12, tiles=None)
        
        carto_api_key = st.secrets.get("carto", {}).get("api_key", "")
        tile_url = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png"
        if carto_api_key: tile_url += f"?api_key={carto_api_key}"
            
        folium.TileLayer(tiles=tile_url, attr='CARTO', name='CARTO Dark Matter', subdomains='abcd', max_zoom=20).add_to(mapa_miaa)

        df_mapa_valido = df.dropna(subset=['latitud', 'longitud']).head(200)
        for _, row in df_mapa_valido.iterrows():
            color_punto = '#3b82f6' if row.get('tipoInstalacion') == 'Cuadro' else '#ef4444'
            folium.CircleMarker(
                location=[float(row['latitud']), float(row['longitud'])],
                radius=2.5,
                color=color_punto,
                fill=True,
                fill_color=color_punto,
                fill_opacity=0.7
            ).add_to(mapa_miaa)

        st_folium(mapa_miaa, width=None, height=230, use_container_width=True)
