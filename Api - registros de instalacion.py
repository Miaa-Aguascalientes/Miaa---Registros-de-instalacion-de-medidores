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

    /* Cabecera Superior: Título a la izquierda, Fecha a la derecha en la misma línea */
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

    /* Tarjetas Compactas: Icono a la izquierda y textos centrados a la derecha */
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
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# SECCIÓN 2: ------------------------------------------------------------------- Cabecera superior del titulo de la pagina  ------------------------------------------------------------------------------------

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


# SECCIÓN 3: ------------------------------------------------------------ FUNCIONES DE CONEXIÓN Y DATOS (API Y BASE DE DATOS) ------------------------------------------------------------------------------------

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

@st.cache_data(ttl=300)
def cargar_datos_api():
    """Conecta con la API externa de MIAA usando credenciales de st.secrets para obtener registros de instalaciones."""
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
    except Exception as e:
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
    except Exception as e:
        return pd.DataFrame()



# SECCIÓN 4: --------------------------------------------------------------------- FUNCIONES AUXILIARES PARA MAPAS -----------------------------------------------------------------------------------------------

def agregar_capas_base(m):
    """Agrega las capas base de mapa (Carto Dark Matter con API Key) y controles de pantalla completa."""
    api_key = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"
    
    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key}",
        name="Vista Nocturna",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains="abcd",
        max_zoom=20,
        control=False
    ).add_to(m)

    Fullscreen(position="topright", title="Ampliar Mapa", cancel_title="Salir de pantalla completa").add_to(m)


# SECCIÓN 5: ----------------------------------------------------------------------- PROCESAMIENTO Y LIMPIEZA INICIAL DE DATOS --------------------------------------------------------------------------------------

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
    
    if not df_metas.empty:
        for col_num in ['Usuarios_Reales', 'Usuarios_con_medidor_inteligente', 'Usuarios_nueva_instalacion']:
            if col_num in df_metas.columns:
                df_metas[col_num] = pd.to_numeric(df_metas[col_num].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        df_metas_valido = df_metas[df_metas['Usuarios_con_medidor_inteligente'] > 0].copy()
    else:
        df_metas_valido = pd.DataFrame()

    # SECCIÓN 6: ----------------------------------------------------------------- BARRA LATERAL (FILTROS Y CONTROLES) --------------------------------------------------------------------------------------------
    
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
    if not df_metas_valido.empty and 'Poligono_de_instalacion' in df_metas_valido.columns:
        lista_poligonos = sorted([str(p) for p in df_metas_valido['Poligono_de_instalacion'].dropna().unique()], key=lambda x: int(x) if x.isdigit() else x)

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

    if not df_metas_valido.empty and 'Poligono_de_instalacion' in df_metas_valido.columns:
        df_metas_filtrado = df_metas_valido[df_metas_valido['Poligono_de_instalacion'].astype(str).isin(poligonos_seleccionados)].copy()
    else:
        df_metas_filtrado = df_metas_valido.copy()

    if col_fecha_ref and not df['fecha_dt'].isna().all():
        mask = (df['fecha_dt'].dt.date >= fecha_inicio) & (df['fecha_dt'].dt.date <= fecha_fin)
        df_filtrado = df.loc[mask].copy()
    else:
        df_filtrado = df.copy()

    meta_total = int(df_metas['Usuarios_nueva_instalacion'].sum()) if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else len(df_filtrado)
    total_instalados = len(df_filtrado)
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0

    if 'usuarioExterno' in df_filtrado.columns:
        total_externo = int(df_filtrado['usuarioExterno'].fillna(False).astype(bool).sum())
        total_miaa = int((~df_filtrado['usuarioExterno'].fillna(False).astype(bool)).sum())
        
        df_externo = df_filtrado[df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy()
        df_miaa_pers = df_filtrado[~df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy()
    else:
        total_externo = 0
        total_miaa = len(df_filtrado)
        df_externo = pd.DataFrame(columns=df_filtrado.columns)
        df_miaa_pers = df_filtrado.copy()

    if not df_metas_filtrado.empty:
        df_tabla_eficiencia = df_metas_filtrado.copy()

        df_eficiencia = df_tabla_eficiencia.groupby(['Colonia_ATL', 'Poligono_de_instalacion'], as_index=False).agg({
            'Usuarios_Reales': 'sum',
            'Usuarios_con_medidor_inteligente': 'sum'
        })
        
        df_eficiencia['pct_sort'] = np.where(
            df_eficiencia['Usuarios_Reales'] > 0, 
            (df_eficiencia['Usuarios_con_medidor_inteligente'] / df_eficiencia['Usuarios_Reales']) * 100, 
            0.0
        )
        
        df_eficiencia = df_eficiencia.sort_values(by='pct_sort', ascending=False).reset_index(drop=True)
        df_eficiencia['%'] = df_eficiencia['pct_sort'].round(2).astype(str) + '%'
        
        df_eficiencia = df_eficiencia.rename(columns={
            'Colonia_ATL': 'Colonia',
            'Usuarios_Reales': 'Med. tot',
            'Usuarios_con_medidor_inteligente': 'Med. inst',
            'Poligono_de_instalacion': 'Polígono'
        })
        
        df_eficiencia = df_eficiencia[['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono']]
    else:
        df_eficiencia = pd.DataFrame(columns=['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono'])


    # SECCIÓN 7: ----------------------------------------------------------------- ESTRUCTURA DE PESTAÑAS PRINCIPALES ------------------------------------------------------------------------------------------------
    
    tab_principal, tab_poligonos, tab_externo, tab_miaa, tab_tabla = st.tabs([
        "📊 Dashboard Principal", 
        "🗺️ Mapa Polígonos",
        "👷 Personal Externo", 
        "🏢 Personal MIAA", 
        "📋 Tabla Base de Datos Completa"
    ])

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # SECCION - PESTAÑA 7.1: DASHBOARD PRINCIPAL
    # -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_principal:
        # Fila de Indicadores KPI Superiores
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        
        with k1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-bullseye"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Meta Total</div>
                        <div class="metric-value">{meta_total:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with k2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-circle-check"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados</div>
                        <div class="metric-value">{total_instalados:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with k3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados Externo</div>
                        <div class="metric-value">{total_externo:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with k4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #a855f7;"><i class="fa-solid fa-building-user"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Instalados MIAA</div>
                        <div class="metric-value">{total_miaa:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with k5:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f43f5e;"><i class="fa-solid fa-chart-pie"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">% Avance</div>
                        <div class="metric-value">{porc_avance}%</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with k6:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{df_filtrado['latitud'].isna().sum():,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

        # SECCION 7.2: --------------------------------------------- Fila de Gráficos Principales (Instalaciones por Día y Distribución de Personal) ------------------------------------------------------------------
        col_g1, col_g2 = st.columns([1.8, 1.2])

        with col_g1:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Día</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df_filtrado['fecha_dt'].isna().all():
                df_filtrado['fecha_dia'] = df_filtrado['fecha_dt'].dt.date
                df_dia = df_filtrado.groupby('fecha_dia', as_index=False).size()
                df_dia['fecha_dia'] = pd.to_datetime(df_dia['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_dia = px.bar(df_dia, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#3b82f6'])
            else:
                fig_dia = px.bar(pd.DataFrame({'Aviso': ['Sin fechas'], 'Valor': [0]}), x='Aviso', y='Valor', text='Valor')
            
            fig_dia.update_traces(textposition='outside', textfont_size=10)
            fig_dia.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='#ffffff', 
                margin=dict(t=40, b=5, l=5, r=5), 
                height=230, 
                xaxis_title=None, 
                yaxis_title=None,
                yaxis=dict(range=[0, 500])
            )
            st.plotly_chart(fig_dia, use_container_width=True)

        with col_g2:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Distribución por Usuario Externo</p>", unsafe_allow_html=True)
            if 'usuarioExterno' in df_filtrado.columns:
                df_ext = df_filtrado['usuarioExterno'].value_counts().reset_index()
                df_ext.columns = ['Externo', 'Cantidad']
                fig_pie = go.Figure(go.Pie(labels=df_ext['Externo'], values=df_ext['Cantidad'], hole=0.5))
            else:
                fig_pie = go.Figure(go.Pie(labels=['Total'], values=[len(df_filtrado)], hole=0.5))
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='#ffffff', 
                margin=dict(t=5, b=5, l=5, r=5), 
                height=230, 
                showlegend=True, 
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # SECCION 7.3: ---------------------------------------------------  Fila Inferior: Tabla de Eficiencia, Mapa de Puntos y Gráfico Mensual Horizontal ---------------------------------------------------------------
        col_inf1, col_inf2 = st.columns([1, 1.6])

        with col_inf1:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Eficiencia por Colonia y Polígono</p>", unsafe_allow_html=True)
            if not df_eficiencia.empty:
                st.dataframe(df_eficiencia, use_container_width=True, hide_index=True)
            else:
                st.info("No se encontraron datos para los polígonos seleccionados.")

        with col_inf2:
            col_map_h, col_graf_h = st.columns([2.2, 1])

            with col_map_h:
                st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones </p>", unsafe_allow_html=True)
                
                df_mapa_valido = df_filtrado.dropna(subset=['latitud', 'longitud'])
                if not df_mapa_valido.empty:
                    map_lat = df_mapa_valido['latitud'].mean()
                    map_lon = df_mapa_valido['longitud'].mean()
                else:
                    map_lat, map_lon = lat_centro, lon_centro

                mapa_miaa = folium.Map(location=[map_lat, map_lon], zoom_start=12, tiles=None)
                agregar_capas_base(mapa_miaa)

                for _, row in df_mapa_valido.iterrows():
                    folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#3b82f6', fill=True, fill_color='#3b82f6', fill_opacity=0.7).add_to(mapa_miaa)

                st_folium(mapa_miaa, width=None, height=340, use_container_width=True, key="mapa_estatico_instalaciones", returned_objects=[])

            with col_graf_h:
                st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Mes</p>", unsafe_allow_html=True)
                
                if col_fecha_ref and not df['fecha_dt'].isna().all():
                    df_mes_total = df.copy()
                    df_mes_total['periodo_mes'] = df_mes_total['fecha_dt'].dt.to_period('M')
                    df_mes = df_mes_total.groupby('periodo_mes', as_index=False).size()
                    df_mes.columns = ['Periodo', 'Cantidad']
                    
                    meses_es = {
                        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 
                        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 
                        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                    }
                    
                    df_mes['Mes'] = df_mes['Periodo'].apply(lambda x: f"{meses_es[x.month]} {x.year}")
                    df_mes = df_mes.sort_values(by='Periodo', ascending=True)
                else:
                    df_mes = pd.DataFrame({'Mes': ['Sin datos'], 'Cantidad': [0]})

                colores_barras = ['#1e3a8a', '#3b82f6'] * ((len(df_mes) // 2) + 1)
                max_cant = df_mes['Cantidad'].max() if not df_mes.empty else 10

                fig_mes_h = px.bar(
                    df_mes, 
                    x='Cantidad', 
                    y='Mes', 
                    orientation='h',
                    text='Cantidad',
                    color='Mes',
                    color_discrete_sequence=colores_barras
                )
                
                fig_mes_h.update_traces(textposition='outside', textfont_size=10)
                fig_mes_h.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font_color='#ffffff', 
                    margin=dict(t=5, b=5, l=5, r=40),  
                    height=130, 
                    xaxis=dict(showgrid=False, showticklabels=False, title=None, range=[0, max_cant * 1.25]), 
                    yaxis=dict(showgrid=False, title=None, tickfont=dict(size=10), categoryorder='array', categoryarray=df_mes['Mes'].tolist()),
                    showlegend=False
                )
                st.plotly_chart(fig_mes_h, use_container_width=True)

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # SECCION 8: PESTAÑA MAPA DE POLÍGONOS GEOGRÁFICOS
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_poligonos:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🗺️ Mapa Detallado de Polígonos de Instalación</p>", unsafe_allow_html=True)
        
        if not df_poligonos.empty:
            fids_disponibles = sorted(df_poligonos['FID'].dropna().unique().tolist(), key=lambda x: int(x) if str(x).isdigit() else str(x))
            
            for fid in fids_disponibles:
                if f"sel_map_fid_{fid}" not in st.session_state:
                    st.session_state[f"sel_map_fid_{fid}"] = True

            col_sel_izq, col_map_der = st.columns([0.3, 0.7])

            with col_sel_izq:
                st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:5px;'>Seleccionar Polígonos (FID):</p>", unsafe_allow_html=True)
                
                b_col1, b_col2 = st.columns(2)
                if b_col1.button("Todos", key="btn_all_fids"):
                    for fid in fids_disponibles:
                        st.session_state[f"sel_map_fid_{fid}"] = True
                if b_col2.button("Ninguno", key="btn_none_fids"):
                    for fid in fids_disponibles:
                        st.session_state[f"sel_map_fid_{fid}"] = False

                with st.container(height=420):
                    fids_seleccionados_mapa = []
                    for fid in fids_disponibles:
                        chk = st.checkbox(f"Polígono {fid}", key=f"sel_map_fid_{fid}")
                        if chk:
                            fids_seleccionados_mapa.append(fid)

            with col_map_der:
                lat_acumuladas = []
                lon_acumuladas = []
                
                poligonos_procesados = {}
                for fid in fids_disponibles:
                    df_pol_sel = df_poligonos[df_poligonos['FID'] == fid]
                    coordenadas_poligono = []
                    
                    # Ordenamiento robusto para evitar cruces en los trazos
                    if 'Vertice' in df_pol_sel.columns:
                        df_ordenado = df_pol_sel.sort_values(by=['Vertice', 'Orden_inst'], ascending=[True, True])
                    else:
                        df_ordenado = df_pol_sel.sort_values(by='Orden_inst', ascending=True)
                    
                    sec_comercial = df_pol_sel['Sector_comercial'].iloc[0] if 'Sector_comercial' in df_pol_sel.columns else "N/A"
                    area_val = df_pol_sel['Area_km2'].iloc[0] if 'Area_km2' in df_pol_sel.columns else 0
                    med_val = df_pol_sel['Medidores'].iloc[0] if 'Medidores' in df_pol_sel.columns else 0

                    for _, r_vertice in df_ordenado.iterrows():
                        c_val = r_vertice['coord']
                        if pd.isna(c_val):
                            continue
                        c_str = str(c_val).strip()
                        
                        for char in ['(', ')', '[', ']', '"', "'", 'POINT', 'POLYGON']:
                            c_str = c_str.replace(char, '')
                        c_str = c_str.strip()
                        
                        # Corrección específica para el FID 913 si agrupa múltiples pares o requiere limpieza especial
                        if str(fid) == "913":
                            c_str = c_str.replace(';', ',')
                        
                        pares = [p.strip() for p in c_str.split(',') if p.strip()]
                        
                        if len(pares) >= 2 and len(pares) % 2 == 0:
                            for i in range(0, len(pares), 2):
                                try:
                                    p1 = float(pares[i])
                                    p2 = float(pares[i+1])
                                    if abs(p1) > abs(p2):
                                        lon, lat = p1, p2
                                    else:
                                        lat, lon = p1, p2
                                    coordenadas_poligono.append([lat, lon])
                                    if fid in fids_seleccionados_mapa:
                                        lat_acumuladas.append(lat)
                                        lon_acumuladas.append(lon)
                                except Exception:
                                    pass
                        else:
                            if ',' in c_str:
                                partes = c_str.split(',')
                            elif ' ' in c_str:
                                partes = c_str.split()
                            else:
                                continue
                                
                            if len(partes) >= 2:
                                try:
                                    p1 = float(partes[0].strip())
                                    p2 = float(partes[1].strip())
                                    
                                    if abs(p1) > abs(p2):
                                        lon, lat = p1, p2
                                    else:
                                        lat, lon = p1, p2
                                        
                                    coordenadas_poligono.append([lat, lon])
                                    if fid in fids_seleccionados_mapa:
                                        lat_acumuladas.append(lat)
                                        lon_acumuladas.append(lon)
                                except Exception:
                                    pass
                    
                    if coordenadas_poligono:
                        poligonos_procesados[fid] = {
                            'coordenadas': coordenadas_poligono,
                            'sector': sec_comercial,
                            'area': area_val,
                            'medidores': med_val,
                            'vertis': len(coordenadas_poligono)
                        }

                if lat_acumuladas and lon_acumuladas:
                    m_p_lat = sum(lat_acumuladas) / len(lat_acumuladas)
                    m_p_lon = sum(lon_acumuladas) / len(lon_acumuladas)
                else:
                    m_p_lat, m_p_lon = lat_centro, lon_centro

                mapa_poligonos_tab = folium.Map(location=[m_p_lat, m_p_lon], zoom_start=12, tiles=None)
                agregar_capas_base(mapa_poligonos_tab)

                for fid, datos in poligonos_procesados.items():
                    if fid in fids_seleccionados_mapa:
                        # Estilo condicional para resaltar o depurar el polígono 913 si lo deseas
                        is_913 = str(fid) == "913"
                        color_borde = "#ef4444" if is_913 else "#2563eb"
                        color_relleno = "#f87171" if is_913 else "#3b82f6"
                        opacidad_relleno = 0.5 if is_913 else 0.3

                        folium.Polygon(
                            locations=datos['coordenadas'],
                            color=color_borde,
                            weight=3 if is_913 else 2.5,
                            fill=True,
                            fill_color=color_relleno,
                            fill_opacity=opacidad_relleno,
                            popup=f"Polígono FID: {fid} | Sector: {datos['sector']} | Área: {datos['area']} km² | Medidores: {datos['medidores']}"
                        ).add_to(mapa_poligonos_tab)

                st_folium(mapa_poligonos_tab, width=None, height=450, use_container_width=True, key="mapa_selector_poligonos", returned_objects=[])

            st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:20px; margin-bottom:10px;'>📋 Detalle de Polígonos de Instalación</p>", unsafe_allow_html=True)
            
            resumen_poligonos = []
            for fid, datos in poligonos_procesados.items():
                if fid in fids_seleccionados_mapa:
                    resumen_poligonos.append({
                        'FID': fid,
                        'Sector Comercial': datos['sector'],
                        'Área (km²)': datos['area'],
                        'Medidores': datos['medidores'],
                        'Vértices Totales': datos['vertis']
                    })
            
            df_resumen_tabla = pd.DataFrame(resumen_poligonos)
            st.dataframe(df_resumen_tabla, use_container_width=True, hide_index=True)
        else:
            st.warning("No se pudo cargar la tabla `Diccionario_poligonos_instalacion` desde la base de datos.")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # SECCION 9: PESTAÑA PERSONAL EXTERNO
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_externo:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>👷 Resumen de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
        
        ext_total = len(df_externo)
        ext_sin_coord = df_externo['latitud'].isna().sum() if not df_externo.empty else 0
        ext_colonias = df_externo['colonia'].nunique() if 'colonia' in df_externo.columns and not df_externo.empty else 0

        e_k1, e_k2, e_k3 = st.columns(3)
        with e_k1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #f59e0b;"><i class="fa-solid fa-hard-hat"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Instalados (Externo)</div>
                        <div class="metric-value">{ext_total:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with e_k2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Colonias Atendidas</div>
                        <div class="metric-value">{ext_colonias:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with e_k3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{ext_sin_coord:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # Dos columnas principales: Izquierda (Gráficas apiladas), Derecha (Mapa grande)
        col_ex_left, col_ex_right = st.columns([1.1, 1.3])

        with col_ex_left:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Día (Externo)</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df_externo.empty and not df_externo['fecha_dt'].isna().all():
                df_ext_dia = df_externo.copy()
                df_ext_dia['fecha_dia'] = df_ext_dia['fecha_dt'].dt.date
                df_ed = df_ext_dia.groupby('fecha_dia', as_index=False).size()
                df_ed['fecha_dia'] = pd.to_datetime(df_ed['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_ext_dia = px.bar(df_ed, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#f59e0b'])
            else:
                fig_ext_dia = px.bar(pd.DataFrame({'Aviso': ['Sin datos'], 'Valor': [0]}), x='Aviso', y='Valor', text='Valor')
            
            fig_ext_dia.update_traces(textposition='outside', textfont_size=10)
            fig_ext_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_ext_dia, use_container_width=True)

            st.markdown("<p style='font-size:12px; margin-top:5px; margin-bottom:0; font-weight:bold;'>Distribución por Nivel Tarifario (Externo)</p>", unsafe_allow_html=True)
            if 'nivel' in df_externo.columns and not df_externo.empty:
                df_ext_nivel = df_externo['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
                df_ext_nivel.columns = ['Nivel', 'Cantidad']
                fig_ext_niv = px.bar(df_ext_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_ext_niv.update_traces(textposition='outside', textfont_size=10)
            else:
                fig_ext_niv = px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad', text='Cantidad')
            
            fig_ext_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_ext_niv, use_container_width=True)

        with col_ex_right:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
            df_ext_map = df_externo.dropna(subset=['latitud', 'longitud']) if not df_externo.empty else pd.DataFrame()
            m_lat = df_ext_map['latitud'].mean() if not df_ext_map.empty else lat_centro
            m_lon = df_ext_map['longitud'].mean() if not df_ext_map.empty else lon_centro
            
            mapa_ext = folium.Map(location=[m_lat, m_lon], zoom_start=12, tiles=None)
            agregar_capas_base(mapa_ext)

            for _, row in df_ext_map.iterrows():
                folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#f59e0b', fill=True, fill_color='#f59e0b', fill_opacity=0.7).add_to(mapa_ext)
            
            st_folium(mapa_ext, width=None, height=460, use_container_width=True, key="mapa_externo", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal Externo</p>", unsafe_allow_html=True)
        df_tabla_ext = df_externo.copy()
        if not df_tabla_ext.empty:
            terminos_excluidos = ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio']
            cols_ex = [c for c in df_tabla_ext.columns if any(term in c.lower() for term in terminos_excluidos)]
            df_tabla_ext = df_tabla_ext.drop(columns=cols_ex, errors='ignore')
            if 'fechaInstalacion' in df_tabla_ext.columns:
                df_tabla_ext['fechaInstalacion'] = pd.to_datetime(df_tabla_ext['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
            df_tabla_ext = df_tabla_ext.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')
        st.dataframe(df_tabla_ext, use_container_width=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # SECCION 10: PESTAÑA PERSONAL MIAA
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_miaa:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🏢 Resumen de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
        
        miaa_total = len(df_miaa_pers)
        miaa_sin_coord = df_miaa_pers['latitud'].isna().sum() if not df_miaa_pers.empty else 0
        miaa_colonias = df_miaa_pers['colonia'].nunique() if 'colonia' in df_miaa_pers.columns and not df_miaa_pers.empty else 0

        m_k1, m_k2, m_k3 = st.columns(3)
        with m_k1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #10b981;"><i class="fa-solid fa-building-user"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total Instalados (MIAA)</div>
                        <div class="metric-value">{miaa_total:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with m_k2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-map-location-dot"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Colonias Atendidas</div>
                        <div class="metric-value">{miaa_colonias:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with m_k3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #94a3b8;"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Sin Coordenadas</div>
                        <div class="metric-value">{miaa_sin_coord:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # Dos columnas principales: Izquierda (Gráficas apiladas), Derecha (Mapa grande)
        col_mi_left, col_mi_right = st.columns([1.1, 1.3])

        with col_mi_left:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Día (MIAA)</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df_miaa_pers.empty and not df_miaa_pers['fecha_dt'].isna().all():
                df_miaa_dia = df_miaa_pers.copy()
                df_miaa_dia['fecha_dia'] = df_miaa_dia['fecha_dt'].dt.date
                df_md = df_miaa_dia.groupby('fecha_dia', as_index=False).size()
                df_md['fecha_dia'] = pd.to_datetime(df_md['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_miaa_dia = px.bar(df_md, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#10b981'])
            else:
                fig_miaa_dia = px.bar(pd.DataFrame({'Aviso': ['Sin datos'], 'Valor': [0]}), x='Aviso', y='Valor', text='Valor')
            
            fig_miaa_dia.update_traces(textposition='outside', textfont_size=10)
            fig_miaa_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_miaa_dia, use_container_width=True)

            st.markdown("<p style='font-size:12px; margin-top:5px; margin-bottom:0; font-weight:bold;'>Distribución por Nivel Tarifario (MIAA)</p>", unsafe_allow_html=True)
            if 'nivel' in df_miaa_pers.columns and not df_miaa_pers.empty:
                df_miaa_nivel = df_miaa_pers['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
                df_miaa_nivel.columns = ['Nivel', 'Cantidad']
                fig_miaa_niv = px.bar(df_miaa_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_miaa_niv.update_traces(textposition='outside', textfont_size=10)
            else:
                fig_miaa_niv = px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad', text='Cantidad')
            
            fig_miaa_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=210, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_miaa_niv, use_container_width=True)

        with col_mi_right:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
            df_miaa_map = df_miaa_pers.dropna(subset=['latitud', 'longitud']) if not df_miaa_pers.empty else pd.DataFrame()
            mm_lat = df_miaa_map['latitud'].mean() if not df_miaa_map.empty else lat_centro
            mm_lon = df_miaa_map['longitud'].mean() if not df_miaa_map.empty else lon_centro
            
            mapa_miaa_pers = folium.Map(location=[mm_lat, mm_lon], zoom_start=12, tiles=None)
            agregar_capas_base(mapa_miaa_pers)

            for _, row in df_miaa_map.iterrows():
                folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#10b981', fill=True, fill_color='#10b981', fill_opacity=0.7).add_to(mapa_miaa_pers)
            
            st_folium(mapa_miaa_pers, width=None, height=460, use_container_width=True, key="mapa_miaa_personal", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal MIAA</p>", unsafe_allow_html=True)
        df_tabla_miaa = df_miaa_pers.copy()
        if not df_tabla_miaa.empty:
            terminos_excluidos = ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio']
            cols_ex = [c for c in df_tabla_miaa.columns if any(term in c.lower() for term in terminos_excluidos)]
            df_tabla_miaa = df_tabla_miaa.drop(columns=cols_ex, errors='ignore')
            if 'fechaInstalacion' in df_tabla_miaa.columns:
                df_tabla_miaa['fechaInstalacion'] = pd.to_datetime(df_tabla_miaa['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
            df_tabla_miaa = df_tabla_miaa.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')
        st.dataframe(df_tabla_miaa, use_container_width=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # SECCION 11: PESTAÑA TABLA BASE DE DATOS COMPLETA
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab_tabla:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📋 Tabla Completa de Registros de la API</p>", unsafe_allow_html=True)
        
        total_registros_tabla = len(df_filtrado)
        total_colonias_tabla = df_filtrado['colonia'].nunique() if 'colonia' in df_filtrado.columns else 0

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #38bdf8;"><i class="fa-solid fa-table-list"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Total de Registros</div>
                        <div class="metric-value">{total_registros_tabla:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with t_col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon-box" style="color: #4ade80;"><i class="fa-solid fa-map-pin"></i></div>
                    <div class="metric-content">
                        <div class="metric-title">Colonias Registradas</div>
                        <div class="metric-value">{total_colonias_tabla:,}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:0;'>Distribución por Nivel (Comercial / Doméstico)</p>", unsafe_allow_html=True)
        if 'nivel' in df_filtrado.columns:
            df_nivel = df_filtrado['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
            df_nivel.columns = ['Nivel', 'Cantidad']
            
            fig_nivel = px.bar(
                df_nivel, 
                x='Nivel', 
                y='Cantidad', 
                text='Cantidad',
                color='Nivel',
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_nivel.update_traces(textposition='outside', textfont_size=11)
            fig_nivel.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='#ffffff', 
                margin=dict(t=30, b=5, l=5, r=5), 
                height=220, 
                xaxis_title=None, 
                yaxis_title=None,
                showlegend=False
            )
            st.plotly_chart(fig_nivel, use_container_width=True)
        else:
            st.info("La columna 'nivel' no se encuentra disponible en los registros.")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        df_tabla_limpia = df_filtrado.copy()
        
        terminos_excluidos = ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio']
        columnas_a_excluir = [c for c in df_tabla_limpia.columns if any(term in c.lower() for term in terminos_excluidos)]
        df_tabla_limpia = df_tabla_limpia.drop(columns=columnas_a_excluir, errors='ignore')
        
        if 'fechaInstalacion' in df_tabla_limpia.columns:
            df_tabla_limpia['fechaInstalacion'] = pd.to_datetime(df_tabla_limpia['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')

        if 'horaInicio' in df_tabla_limpia.columns:
            df_tabla_limpia['horaInicio'] = pd.to_datetime(df_tabla_limpia['horaInicio'], errors='coerce').dt.strftime('%H:%M')

        df_tabla_limpia = df_tabla_limpia.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')

        st.dataframe(df_tabla_limpia, use_container_width=True)
