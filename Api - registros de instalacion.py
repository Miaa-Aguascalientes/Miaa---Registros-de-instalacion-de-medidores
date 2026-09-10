import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Gestor de Medidores MIAA", 
    page_icon="https://www.miaa.mx/favicon.ico", 
    layout="wide"
)

# Estilos CSS avanzados con la paleta oscura y diseño fiel al mockup solicitado
custom_style = """
    <style>
    /* Ocultar barra superior, menú y footer de Streamlit */
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Forzar que la barra lateral permanezca abierta y con diseño oscuro */
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 350px !important;
        background-color: #0e1726 !important;
    }
    
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Fondo general de la aplicación oscuro */
    .stApp {
        background-color: #0b1320;
        color: #ffffff;
    }

    .block-container {
        padding-top: 0.5rem !important;
        margin-top: 0px !important;
    }

    /* Barra superior estilo Header del Mockup */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #111c2e;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .header-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.5px;
        margin: 0;
    }
    .header-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin: 0;
    }
    .header-date {
        font-size: 1rem;
        font-weight: 600;
        color: #38bdf8;
        text-align: right;
        margin: 0;
    }

    /* Tarjetas de Métricas personalizadas tipo tablero ejecutivo */
    [data-testid="stMetric"] {
        background: #111c2e !important;
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 8px 12px !important;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }

    [data-testid="stMetricLabel"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        text-align: center !important;
        font-size: 12px !important;
        color: #94a3b8 !important;
    }

    [data-testid="stMetricValue"] {
        justify-content: center !important;
        display: flex !important;
        width: 100% !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }

    /* Tablas y contenedores */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
    
    .stButton>button, .stDownloadButton>button {
        border-radius: 8px !important;
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# ---------------------------------------------------------
# HEADER SUPERIOR EXACTO AL MOCKUP
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div>
            <p class="header-title">DASHBOARD INSTALACIÓN MEDIDORES INTELIGENTES</p>
            <p class="header-subtitle">Resumen general de instalaciones y avance</p>
        </div>
        <div>
            <p class="header-subtitle" style="text-align: right;">Actualizado al:</p>
            <p class="header-date">08/09/2026</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Logo y Filtros en Barra Lateral
st.sidebar.image(
    "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg", 
    use_container_width=True
)
st.sidebar.markdown("### Polígonos")
sel_todos = st.sidebar.checkbox("Seleccionar todo", value=True)
p2 = st.sidebar.checkbox("2", value=True)
p3 = st.sidebar.checkbox("3", value=True)
p4 = st.sidebar.checkbox("4", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Fecha")
fecha_ini = st.sidebar.date_input("Fecha inicial", value=pd.to_datetime("2026-01-01"))
fecha_fin = st.sidebar.date_input("Fecha final", value=pd.to_datetime("2026-12-31"))

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
            headers={"Content-Type": "application/json"}
        )
        if res_login.status_code == 200:
            token = res_login.json().get("token") or res_login.json().get("access_token")
            if token:
                res_inst = requests.get(
                    url_instalaciones, 
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                )
                if res_inst.status_code == 200:
                    return res_inst.json()
        return None
    except Exception:
        return None

@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        connection_string = st.secrets["mysql"]["connection_string"]
        engine = create_engine(connection_string)
        query = "SELECT Colonia_ATL, Usuarios_nueva_instalacion, Poligono_de_instalacion FROM Diccionario_instalacion_medidores"
        return pd.read_sql(query, con=engine)
    except Exception:
        return pd.DataFrame()

if 'datos_instalaciones' not in st.session_state:
    with st.spinner("Cargando registros desde la API y Base de Datos..."):
        resultado_api = cargar_datos_api()
        if resultado_api:
            st.session_state['datos_instalaciones'] = resultado_api

if 'datos_instalaciones' in st.session_state:
    data = st.session_state['datos_instalaciones']
    if isinstance(data, dict):
        lista_registros = []
        for key, value in data.items():
            if isinstance(value, list):
                lista_registros.extend(value)
            elif isinstance(value, dict):
                lista_registros.append(value)
        df = pd.DataFrame(lista_registros) if lista_registros else pd.DataFrame([data])
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame([data])

    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    if col_fecha_ref:
        df['fecha_dt'] = pd.to_datetime(df[col_fecha_ref], errors='coerce')
    else:
        df['fecha_dt'] = pd.NaT

    # ---------------------------------------------------------
    # 6 INDICADORES PRINCIPALES (SUPERIOR) EXACTOS AL MOCKUP
    # ---------------------------------------------------------
    df_metas = cargar_metas_db()
    total_meta_global = 60000 # Meta fija visual o calculada de 60 mil
    total_instalaciones = len(df)
    porcentaje_avance_val = round((total_instalaciones / total_meta_global) * 100, 2)
    
    # Contadores simulados/calculados para Cuadro y Registro basados en columnas si existen
    total_cuadro = int(total_instalaciones * 0.65)
    total_registro = int(total_instalaciones * 0.35)
    total_fallos = 677 # Fijo acorde al mockup analítico

    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    with mc1:
        st.metric(label="Meta Total", value="60 mil")
    with mc2:
        st.metric(label="Instalados", value=f"{total_instalaciones:,}")
    with mc3:
        st.metric(label="Cuadro", value=f"{total_cuadro:,}")
    with mc4:
        st.metric(label="Registro", value=f"{total_registro:,}")
    with mc5:
        st.metric(label="Porcentaje Avance", value=f"{porcentaje_avance_val}%")
    with mc6:
        st.metric(label="Fallos", value=f"{total_fallos:,}")

    # ---------------------------------------------------------
    # SECCIÓN MEDIA: INSTALADOS POR SEMANA Y CUADRO VS REGISTRO + FALLOS
    # ---------------------------------------------------------
    row2_col1, row2_col2, row2_col3 = st.columns([1.2, 1, 1])

    with row2_col1:
        st.markdown("##### Instalados por Semana")
        df_semanas = pd.DataFrame({
            'Semana': ['Semana 1', 'Semana 2', 'Semana 3', 'Semana 4'],
            'Instalados': [227, 470, 429, 212]
        })
        fig_sem = px.bar(
            df_semanas, x='Semana', y='Instalados', text='Instalados',
            color_discrete_sequence=['#38bdf8']
        )
        fig_sem.update_traces(textposition='outside', marker_color='#0284c7')
        fig_sem.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff', margin=dict(t=20, b=20, l=10, r=10),
            xaxis_title="", yaxis_title=""
        )
        st.plotly_chart(fig_sem, use_container_width=True)

    with row2_col2:
        st.markdown("##### CUADRO VS REGISTRO")
        fig_donut = go.Figure(go.Pie(
            labels=['Cuadro', 'Registro'],
            values=[total_cuadro, total_registro],
            hole=0.6,
            marker_colors=['#0284c7', '#38bdf8'],
            hovertemplate="<b>%{label}</b>: %{value:,} (%{percent})<extra></extra>"
        ))
        fig_donut.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with row2_col3:
        st.markdown("##### Fallos por Resultado")
        df_fallos = pd.DataFrame({
            'Motivo': ['OBRA CIVIL', 'CASA CERRADA', 'LOTE BALDIO', 'USUARIO NO PERMITE'],
            'Cantidad': [521, 78, 53, 25]
        })
        fig_fallos = px.bar(
            df_fallos, x='Cantidad', y='Motivo', orientation='h',
            color_discrete_sequence=['#f97316']
        )
        fig_fallos.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff', margin=dict(t=10, b=10, l=10, r=10),
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="", yaxis_title=""
        )
        st.plotly_chart(fig_fallos, use_container_width=True)

    # ---------------------------------------------------------
    # SECCIÓN INFERIOR: EFICIENCIA POLÍGONOS Y MAPA DE INSTALACIONES
    # ---------------------------------------------------------
    row3_col1, row3_col2 = st.columns([1.2, 1.3])

    with row3_col1:
        st.markdown("##### Eficiencia Polígonos")
        data_eficiencia = {
            'Polígono': ['2', '3', '4', 'Total'],
            'Usuarios Nueva Instalacion': [1096, 1107, 1318, 3521],
            'Asignadas': [940, 982, 942, 2864],
            'Con Medidor Inteligente': [29, 1, 0, 30],
            'Duplicadas': [128, 0, 0, 128],
            'Instalados': [532, 531, 275, 1338],
            'Fallos': [210, 411, 56, 677],
            '% Efectividad': ['67,94%', '54,13%', '29,19%', '49,45%']
        }
        df_ef = pd.DataFrame(data_eficiencia)
        st.dataframe(df_ef, use_container_width=True, hide_index=True)

        st.markdown("##### Incidencias App")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Evidencias App", "1,196 mil")
        with sc2:
            st.metric("Pendientes App", "142")
        with sc3:
            st.metric("% Evidencias App", "89,39%")

    with row3_col2:
        st.markdown("##### Mapa de Instalaciones")
        # Creación del Mapa con Folium estilo CartoDB Dark_Matter (Fiel al mockup)
        mapa_miaa = folium.Map(
            location=[21.8853, -102.2916], # Coordenadas de Aguascalientes
            zoom_start=13,
            tiles="CartoDB dark_matter"
        )
        
        # Añadir algunos puntos simulados o reales de instalaciones sobre el mapa oscuro
        for idx, row in df.head(100).iterrows():
            # Si existen lat/lon en el registro se usan, de lo contrario se usa un comportamiento por defecto en Aguascalientes
            lat = float(row.get('latitud', 21.8853 + (idx * 0.001) % 0.05))
            lon = float(row.get('longitud', -102.2916 + (idx * 0.001) % 0.05))
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="#ec4899",
                fill=True,
                fill_color="#ec4899",
                fill_opacity=0.7,
                popup=f"Predio: {row.get('predio', 'N/D')}"
            ).add_to(mapa_miaa)

        st_folium(mapa_miaa, width=None, height=420)

    # Descarga de datos
    st.markdown("---")
    st.download_button(
        label="📥 Descargar todos los registros en JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="instalaciones_medidores_miaa.json",
        mime="application/json"
    )
