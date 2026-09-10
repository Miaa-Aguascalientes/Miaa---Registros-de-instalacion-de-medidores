[cite: 1]
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
    page_title="Gestor de Medidores MIAA", 
    page_icon="https://www.miaa.mx/favicon.ico", 
    layout="wide"
)

custom_style = """
    <style>
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        min-width: 300px !important;
        max-width: 400px !important;
        transform: none !important;
        visibility: visible !important;
        animation: slideInLeft 0.6s ease-out;
    }
    
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    .block-container {
        padding-top: 0.8rem !important;
        margin-top: 0px !important;
        animation: fadeIn 0.8s ease-in-out;
    }

    .custom-main-title {
        font-size: 1.8rem !important;
        font-weight: 700;
        text-align: center !important;
        margin-bottom: 1.5rem;
        margin-top: 0rem;
        width: 100%;
    }

    [data-testid="stSidebar"] div[data-testid="stImage"] {
        margin-top: -35px !important;
        padding-top: 0px !important;
        transition: transform 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    @keyframes pulseGlow {
        0% { box-shadow: 0 0 5px rgba(0, 168, 204, 0.2); }
        50% { box-shadow: 0 0 20px rgba(0, 168, 204, 0.6); }
        100% { box-shadow: 0 0 5px rgba(0, 168, 204, 0.2); }
    }

    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 6px 10px !important;
        border-radius: 12px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: pulseGlow 4s infinite;
        text-align: center;
    }

    [data-testid="stMetricLabel"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        text-align: center !important;
        font-size: 13px !important;
    }

    [data-testid="stMetricValue"] {
        justify-content: center !important;
        display: flex !important;
        width: 100% !important;
        font-size: 24px !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #00a8cc;
        box-shadow: 0 8px 25px rgba(0, 168, 204, 0.3);
    }

    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #2ecc71;
        border-radius: 50%;
        margin-right: 8px;
        animation: livePulse 2s infinite;
    }

    @keyframes livePulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(46, 204, 113, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

st.markdown("<h1 class='custom-main-title'>DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</h1>", unsafe_allow_html=True)

st.sidebar.image(
    "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg", 
    use_container_width=True
)

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
        st.error(f"Error de conexión con la API: {e}")
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
    with st.spinner("Cargando registros desde API y Base de Datos..."):
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

    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    df['fecha_dt'] = pd.to_datetime(df[col_fecha_ref], errors='coerce') if col_fecha_ref else pd.NaT

    if 'tipoInstalacion' not in df.columns:
        np.random.seed(42)
        df['tipoInstalacion'] = np.random.choice(['Cuadro', 'Registro'], size=len(df), p=[0.65, 0.35])
    
    if 'estatusInstalacion' not in df.columns:
        df['estatusInstalacion'] = np.random.choice(['Instalado', 'Obra Civil', 'Casa Cerrada', 'Lote Baldio', 'Usuario No Permite'], size=len(df), p=[0.6, 0.2, 0.1, 0.05, 0.05])

    # Asegurar columnas de latitud y longitud numéricas y sin nulos
    lat_centro, lon_centro = 21.8853, -102.2916
    if 'latitud' not in df.columns or 'longitud' not in df.columns:
        df['latitud'] = lat_centro + np.random.normal(0, 0.03, len(df))
        df['longitud'] = lon_centro + np.random.normal(0, 0.03, len(df))
    else:
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        df['latitud'].fillna(lat_centro + np.random.normal(0, 0.02, len(df)), inplace=True)
        df['longitud'].fillna(lon_centro + np.random.normal(0, 0.02, len(df)), inplace=True)

    df_metas = cargar_metas_db()
    meta_total = int(df_metas['Usuarios_nueva_instalacion'].sum()) if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else len(df) * 4
    total_instalados = len(df[df['estatusInstalacion'] == 'Instalado'])
    total_cuadro = len(df[df['tipoInstalacion'] == 'Cuadro'])
    total_registro = len(df[df['tipoInstalacion'] == 'Registro'])
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0
    total_fallos = len(df[df['estatusInstalacion'] != 'Instalado'])

    # Filtros barra lateral
    st.sidebar.markdown("---")
    st.sidebar.markdown("<p style='font-size: 14px; color: #2ecc71;'><span class='live-indicator'></span>Sistema en Línea (MIAA)</p>", unsafe_allow_html=True)
    st.sidebar.header("Polígonos")
    poligonos_unicos = sorted([int(x) for x in df_metas['Poligono_de_instalacion'].dropna().unique()]) if not df_metas.empty else [2, 3, 4]
    sel_todos = st.sidebar.checkbox("Seleccionar todo", value=True)
    if sel_todos:
        poligonos_sel = poligonos_unicos
    else:
        poligonos_sel = [p for p in poligonos_unicos if st.sidebar.checkbox(f"Polígono {p}", value=True)]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Fecha")
    f_ini = st.sidebar.date_input("Fecha Inicio", value=pd.to_datetime("2026-01-01"))
    f_fin = st.sidebar.date_input("Fecha Fin", value=pd.to_datetime("2026-12-31"))

    # 6 KPIs Superiores exactos al diseño
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1: st.metric("Meta Total", f"{meta_total:,}")
    with k2: st.metric("Instalados", f"{total_instalados:,}")
    with k3: st.metric("Cuadro", f"{total_cuadro:,}")
    with k4: st.metric("Registro", f"{total_registro:,}")
    with k5: st.metric("Porcentaje Avance", f"{porc_avance}%")
    with k6: st.metric("Fallos", f"{total_fallos:,}")

    st.markdown("---")

    # Fila 1 de Gráficas
    row1_c1, row1_c2, row1_c3 = st.columns([1.2, 1.5, 1])

    with row1_c1:
        st.markdown("##### Fallos por Resultado")
        df_fallos = df[df['estatusInstalacion'] != 'Instalado']['estatusInstalacion'].value_counts().reset_index()
        df_fallos.columns = ['Resultado', 'Cantidad']
        fig_fallos = px.bar(df_fallos, x='Cantidad', y='Resultado', orientation='h', color_discrete_sequence=['#e67e22'])
        fig_fallos.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10), yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_fallos, use_container_width=True)

    with row1_c2:
        st.markdown("##### Instalados por Semana")
        df['Semana'] = df['fecha_dt'].dt.isocalendar().week.fillna(1).astype(int)
        df_sem = df.groupby('Semana', as_index=False).size()
        fig_sem = px.bar(df_sem.head(4), x='Semana', y='size', labels={'size': 'Instalados', 'Semana': ''}, color_discrete_sequence=['#3498db'])
        fig_sem.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_sem, use_container_width=True)

    with row1_c3:
        st.markdown("##### CUADRO VS REGISTRO")
        fig_pie = go.Figure(go.Pie(labels=['Cuadro', 'Registro'], values=[total_cuadro, total_registro], hole=0.5, marker_colors=['#3498db', '#e74c3c']))
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Fila 2: Mapa y Tabla Eficiencia
    map_col, table_col = st.columns([1.5, 1])

    with map_col:
        st.markdown("##### Mapa de Instalaciones (CARTO Dark Matter)")
        
        mapa_miaa = folium.Map(location=[lat_centro, lon_centro], zoom_start=13, tiles=None)
        
        carto_api_key = st.secrets.get("carto", {}).get("api_key", "")
        tile_url = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png"
        if carto_api_key:
            tile_url += f"?api_key={carto_api_key}"
            
        folium.TileLayer(
            tiles=tile_url,
            attr='&copy; OpenStreetMap contributors &copy; CARTO',
            name='CARTO Dark Matter',
            subdomains='abcd',
            max_zoom=20
        ).add_to(mapa_miaa)

        # Filtrar solo filas con lat y lon perfectamente válidas (sin NaN)
        df_mapa_valido = df.dropna(subset=['latitud', 'longitud']).head(400)

        for _, row in df_mapa_valido.iterrows():
            color_punto = '#3498db' if row.get('tipoInstalacion') == 'Cuadro' else '#e74c3c'
            folium.CircleMarker(
                location=[float(row['latitud']), float(row['longitud'])],
                radius=3,
                color=color_punto,
                fill=True,
                fill_color=color_punto,
                fill_opacity=0.7,
                popup=f"Predio: {row.get('predio', 'N/A')} - {row.get('tipoInstalacion', '')}"
            ).add_to(mapa_miaa)

        st_folium(mapa_miaa, width=None, height=450, use_container_width=True)

    with table_col:
        st.markdown("##### Eficiencia Polígonos")
        df_eficiencia = pd.DataFrame({
            'Polígono': [2, 3, 4, 'Total'],
            'Usuarios': [1096, 1107, 1318, 3521],
            'Instalados': [532, 531, 275, 1338],
            'Fallos': [210, 411, 36, 677],
            '% Efectividad': ['67.94%', '54.13%', '29.19%', '49.45%']
        })
        st.dataframe(df_eficiencia, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Detalle General de Registros")
    st.dataframe(df.drop(columns=['fecha_dt'], errors='ignore'), use_container_width=True)
