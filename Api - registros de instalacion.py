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
    if 'latitud' in df.columns:
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
    else:
        df['latitud'] = np.nan

    if 'longitud' in df.columns:
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
    else:
        df['longitud'] = np.nan

    df_metas = cargar_metas_db()
    
    if not df_metas.empty:
        for col_num in ['Usuarios_Reales', 'Usuarios_con_medidor_inteligente', 'Usuarios_nueva_instalacion']:
            if col_num in df_metas.columns:
                df_metas[col_num] = pd.to_numeric(df_metas[col_num].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        df_metas = df_metas[df_metas['Usuarios_con_medidor_inteligente'] > 0].copy()

    # ---------------------------------------------------------
    # BARRA LATERAL
    # ---------------------------------------------------------
    logo_url = "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg"
    st.sidebar.image(logo_url, use_container_width=True)
    st.sidebar.markdown("---")

    st.sidebar.subheader("Periodo de Fechas")
    opcion_periodo = st.sidebar.selectbox(
        "Seleccionar Rango",
        ["Este mes", "El mes pasado", "Últimos tres meses", "Últimos 6 meses", "Este año", "El año pasado"],
        index=4
    )

    hoy = pd.to_datetime("2026-09-10").date()
    
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
    if not df_metas.empty and 'Poligono_de_instalacion' in df_metas.columns:
        lista_poligonos = sorted([str(p) for p in df_metas['Poligono_de_instalacion'].dropna().unique()], key=lambda x: int(x) if x.isdigit() else x)

    # Botones de control rápido para los checkboxes
    col_c1, col_c2 = st.sidebar.columns(2)
    seleccionar_todos = col_c1.button("Marcar todos")
    deseleccionar_todos = col_c2.button("Desmarcar")

    if seleccionar_todos:
        for p in lista_poligonos:
            st.session_state[f"chk_pol_{p}"] = True

    if deseleccionar_todos:
        for p in lista_poligonos:
            st.session_state[f"chk_pol_{p}"] = False

    # Contenedor con scroll para los checkboxes de polígonos
    with st.sidebar.container(height=220):
        poligonos_seleccionados = []
        for pol in lista_poligonos:
            estado = st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}")
            if estado:
                poligonos_seleccionados.append(pol)

    if not df_metas.empty and 'Poligono_de_instalacion' in df_metas.columns:
        df_metas_filtrado = df_metas[df_metas['Poligono_de_instalacion'].astype(str).isin(poligonos_seleccionados)].copy()
    else:
        df_metas_filtrado = df_metas.copy()

    if col_fecha_ref and not df['fecha_dt'].isna().all():
        mask = (df['fecha_dt'].dt.date >= fecha_inicio) & (df['fecha_dt'].dt.date <= fecha_fin)
        df_filtrado = df.loc[mask].copy()
    else:
        df_filtrado = df.copy()

    meta_total = int(df_metas_filtrado['Usuarios_nueva_instalacion'].sum()) if not df_metas_filtrado.empty and 'Usuarios_nueva_instalacion' in df_metas_filtrado.columns else len(df_filtrado)
    total_instalados = len(df_filtrado)
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0

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

    # FILA 1: KPIs Superiores Reales
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1: st.metric("Meta Total", f"{meta_total:,}")
    with k2: st.metric("Instalados", f"{total_instalados:,}")
    with k3: st.metric("Registros API", f"{len(df_filtrado):,}")
    with k4: st.metric("Técnicos Activos", f"{df_filtrado['usuarioNombre'].nunique() if 'usuarioNombre' in df_filtrado.columns else 0:,}")
    with k5: st.metric("Porcentaje Avance", f"{porc_avance}%")
    with k6: st.metric("Sin Coordenadas", f"{df_filtrado['latitud'].isna().sum():,}")

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # FILA 2: Gráficas (Instalaciones por Día y Distribución por Usuario Externo)
    col_g1, col_g2 = st.columns([1.8, 1.2])

    with col_g1:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Día (Real API)</p>", unsafe_allow_html=True)
        if col_fecha_ref and not df_filtrado['fecha_dt'].isna().all():
            df_filtrado['fecha_dia'] = df_filtrado['fecha_dt'].dt.date
            df_dia = df_filtrado.groupby('fecha_dia', as_index=False).size()
            df_dia['fecha_dia'] = pd.to_datetime(df_dia['fecha_dia']).dt.strftime('%d/%m/%Y')
            fig_dia = px.bar(df_dia, x='fecha_dia', y='size', color_discrete_sequence=['#3b82f6'])
        else:
            fig_dia = px.bar(pd.DataFrame({'Aviso': ['Sin fechas'], 'Valor': [0]}), x='Aviso', y='Valor')
        fig_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=160, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_dia, use_container_width=True)

    with col_g2:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Distribución por Usuario Externo</p>", unsafe_allow_html=True)
        if 'usuarioExterno' in df_filtrado.columns:
            df_ext = df_filtrado['usuarioExterno'].value_counts().reset_index()
            df_ext.columns = ['Externo', 'Cantidad']
            fig_pie = go.Figure(go.Pie(labels=df_ext['Externo'], values=df_ext['Cantidad'], hole=0.5))
        else:
            fig_pie = go.Figure(go.Pie(labels=['Total'], values=[len(df_filtrado)], hole=0.5))
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=160, showlegend=True, legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_pie, use_container_width=True)

    # FILA 3: Tabla de Eficiencia Ordenada y Mapa
    col_inf1, col_inf2 = st.columns([1, 1.6])

    with col_inf1:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Eficiencia por Colonia y Polígono</p>", unsafe_allow_html=True)
        if not df_eficiencia.empty:
            st.dataframe(df_eficiencia, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron datos para los polígonos seleccionados.")

    with col_inf2:
        st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones (Coordenadas Reales API)</p>", unsafe_allow_html=True)
        
        df_mapa_valido = df_filtrado.dropna(subset=['latitud', 'longitud'])
        if not df_mapa_valido.empty:
            map_lat = df_mapa_valido['latitud'].mean()
            map_lon = df_mapa_valido['longitud'].mean()
        else:
            map_lat, map_lon = lat_centro, lon_centro

        mapa_miaa = folium.Map(location=[map_lat, map_lon], zoom_start=12, tiles=None)
        
        carto_api_key = st.secrets.get("carto", {}).get("api_key", "")
        tile_url = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png"
        if carto_api_key: tile_url += f"?api_key={carto_api_key}"
            
        folium.TileLayer(tiles=tile_url, attr='CARTO', name='CARTO Dark Matter', subdomains='abcd', max_zoom=20).add_to(mapa_miaa)

        for _, row in df_mapa_valido.iterrows():
            folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#3b82f6', fill=True, fill_color='#3b82f6', fill_opacity=0.7).add_to(mapa_miaa)

        st_folium(mapa_miaa, width=None, height=230, use_container_width=True)

    # FILA 4: Tabla limpia de la API
    st.markdown("<p style='font-size:12px; margin-top:10px; margin-bottom:0; font-weight:bold;'>Registros completos de la API (Tabla filtrada y formateada)</p>", unsafe_allow_html=True)
    
    df_tabla_limpia = df_filtrado.copy()
    
    terminos_excluidos = ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio']
    columnas_a_excluir = [c for c in df_tabla_limpia.columns if any(term in c.lower() for term in terminos_excluidos)]
    df_tabla_limpia = df_tabla_limpia.drop(columns=columnas_a_excluir, errors='ignore')
    
    if 'fechaInstalacion' in df_tabla_limpia.columns:
        df_tabla_limpia['fechaInstalacion'] = pd.to_datetime(df_tabla_limpia['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')

    if 'horaInicio' in df_tabla_limpia.columns:
        df_tabla_limpia['horaInicio'] = pd.to_datetime(df_tabla_limpia['horaInicio'], errors='coerce').dt.strftime('%H:%M')

    df_tabla_limpia = df_tabla_limpia.drop(columns=['fecha_dt', 'Semana', 'fecha_dia'], errors='ignore')

    st.dataframe(df_tabla_limpia, use_container_width=True)
