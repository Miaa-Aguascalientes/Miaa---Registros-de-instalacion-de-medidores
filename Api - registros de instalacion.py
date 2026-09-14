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
        <span style='color: #94a3b8; font-size: 0.9rem;'>Actualizado al: 14/09/2026</span>
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
        df = pd.read_sql(query, con=engine)
        
        if not df.empty and 'coord' in df.columns:
            coords_split = df['coord'].astype(str).str.split(',', expand=True)
            if coords_split.shape[1] >= 2:
                df['Latitud'] = pd.to_numeric(coords_split[0].str.strip(), errors='coerce')
                df['Longitud'] = pd.to_numeric(coords_split[1].str.strip(), errors='coerce')
            else:
                df['Latitud'] = np.nan
                df['Longitud'] = np.nan
                
        return df
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

    # BARRA LATERAL
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
        for p in lista_poligonos: st.session_state[f"chk_pol_{p}"] = True
    if deseleccionar_todos:
        for p in lista_poligonos: st.session_state[f"chk_pol_{p}"] = False

    with st.sidebar.container(height=220):
        poligonos_seleccionados = []
        for pol in lista_poligonos:
            if st.checkbox(f"Polígono {pol}", key=f"chk_pol_{pol}"):
                poligonos_seleccionados.append(pol)

    df_metas_filtrado = df_metas_valido[df_metas_valido['Poligono_de_instalacion'].astype(str).isin(poligonos_seleccionados)].copy() if not df_metas_valido.empty else pd.DataFrame()

    if col_fecha_ref and not df['fecha_dt'].isna().all():
        mask = (df['fecha_dt'].dt.date >= fecha_inicio) & (df['fecha_dt'].dt.date <= fecha_fin)
        df_filtrado = df.loc[mask].copy()
    else:
        df_filtrado = df.copy()

    meta_total = int(df_metas['Usuarios_nueva_instalacion'].sum()) if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else len(df_filtrado)
    total_instalados = len(df_filtrado)
    porc_avance = round((total_instalados / meta_total) * 100, 2) if meta_total > 0 else 0.0

    total_externo = int(df_filtrado['usuarioExterno'].fillna(False).astype(bool).sum()) if 'usuarioExterno' in df_filtrado.columns else 0
    total_miaa = int((~df_filtrado['usuarioExterno'].fillna(False).astype(bool)).sum()) if 'usuarioExterno' in df_filtrado.columns else len(df_filtrado)
    df_externo = df_filtrado[df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy() if 'usuarioExterno' in df_filtrado.columns else pd.DataFrame()
    df_miaa_pers = df_filtrado[~df_filtrado['usuarioExterno'].fillna(False).astype(bool)].copy() if 'usuarioExterno' in df_filtrado.columns else df_filtrado.copy()

    if not df_metas_filtrado.empty:
        df_eficiencia = df_metas_filtrado.groupby(['Colonia_ATL', 'Poligono_de_instalacion'], as_index=False).agg({
            'Usuarios_Reales': 'sum',
            'Usuarios_con_medidor_inteligente': 'sum'
        })
        df_eficiencia['pct_sort'] = np.where(df_eficiencia['Usuarios_Reales'] > 0, (df_eficiencia['Usuarios_con_medidor_inteligente'] / df_eficiencia['Usuarios_Reales']) * 100, 0.0)
        df_eficiencia = df_eficiencia.sort_values(by='pct_sort', ascending=False).reset_index(drop=True)
        df_eficiencia['%'] = df_eficiencia['pct_sort'].round(2).astype(str) + '%'
        df_eficiencia = df_eficiencia.rename(columns={'Colonia_ATL': 'Colonia', 'Usuarios_Reales': 'Med. tot', 'Usuarios_con_medidor_inteligente': 'Med. inst', 'Poligono_de_instalacion': 'Polígono'})[['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono']]
    else:
        df_eficiencia = pd.DataFrame(columns=['Colonia', 'Med. tot', 'Med. inst', '%', 'Polígono'])

    # PESTAÑAS PRINCIPALES
    tab_principal, tab_externo, tab_miaa, tab_tabla, tab_poligonos = st.tabs([
        "📊 Dashboard Principal", "👷 Personal Externo", "🏢 Personal MIAA", "📋 Tabla Base de Datos Completa", "🗺️ Polígonos"
    ])

    api_key_carto = "cb1_26ji_1_864817f3cb73c0bdbe0daccd"

    with tab_principal:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: st.metric("Meta Total", f"{meta_total:,}")
        with k2: st.metric("Instalados", f"{total_instalados:,}")
        with k3: st.metric("Instalados por Externo", f"{total_externo:,}")
        with k4: st.metric("Instalados por MIAA", f"{total_miaa:,}")
        with k5: st.metric("Porcentaje Avance", f"{porc_avance}%")
        with k6: st.metric("Sin Coordenadas", f"{df_filtrado['latitud'].isna().sum():,}")

        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns([1.8, 1.2])

        with col_g1:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Día (Real API)</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df_filtrado['fecha_dt'].isna().all():
                df_filtrado['fecha_dia'] = df_filtrado['fecha_dt'].dt.date
                df_dia = df_filtrado.groupby('fecha_dia', as_index=False).size()
                df_dia['fecha_dia'] = pd.to_datetime(df_dia['fecha_dia']).dt.strftime('%d/%m/%Y')
                fig_dia = px.bar(df_dia, x='fecha_dia', y='size', text='size', color_discrete_sequence=['#3b82f6'])
            else:
                fig_dia = px.bar(pd.DataFrame({'Aviso': ['Sin fechas'], 'Valor': [0]}), x='Aviso', y='Valor', text='Valor')
            fig_dia.update_traces(textposition='outside', textfont_size=10)
            fig_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=40, b=5, l=5, r=5), height=230, xaxis_title=None, yaxis_title=None, yaxis=dict(range=[0, 500]))
            st.plotly_chart(fig_dia, use_container_width=True)

        with col_g2:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Distribución por Usuario Externo</p>", unsafe_allow_html=True)
            if 'usuarioExterno' in df_filtrado.columns:
                df_ext = df_filtrado['usuarioExterno'].value_counts().reset_index()
                df_ext.columns = ['Externo', 'Cantidad']
                fig_pie = go.Figure(go.Pie(labels=df_ext['Externo'], values=df_ext['Cantidad'], hole=0.5))
            else:
                fig_pie = go.Figure(go.Pie(labels=['Total'], values=[len(df_filtrado)], hole=0.5))
            fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=5), height=230, showlegend=True, legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_pie, use_container_width=True)

        col_inf1, col_inf2 = st.columns([1, 1.6])
        with col_inf1:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Eficiencia por Colonia y Polígono</p>", unsafe_allow_html=True)
            if not df_eficiencia.empty: st.dataframe(df_eficiencia, use_container_width=True, hide_index=True)
            else: st.info("No se encontraron datos.")

        with col_inf2:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Instalaciones por Mes</p>", unsafe_allow_html=True)
            if col_fecha_ref and not df['fecha_dt'].isna().all():
                df_mes_total = df.copy()
                df_mes_total['periodo_mes'] = df_mes_total['fecha_dt'].dt.to_period('M')
                df_mes = df_mes_total.groupby('periodo_mes', as_index=False).size()
                df_mes.columns = ['Periodo', 'Cantidad']
                meses_es = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
                df_mes['Mes'] = df_mes['Periodo'].apply(lambda x: f"{meses_es[x.month]} {x.year}")
                df_mes = df_mes.sort_values(by='Periodo', ascending=True)
            else:
                df_mes = pd.DataFrame({'Mes': ['Sin datos'], 'Cantidad': [0]})

            colores_barras = ['#1e3a8a', '#3b82f6'] * ((len(df_mes) // 2) + 1)
            fig_mes_h = px.bar(df_mes, x='Cantidad', y='Mes', orientation='h', text='Cantidad', color='Mes', color_discrete_sequence=colores_barras)
            fig_mes_h.update_traces(textposition='outside', textfont_size=11)
            fig_mes_h.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=5, b=5, l=5, r=30), height=130, xaxis=dict(showgrid=False, showticklabels=False, title=None), yaxis=dict(showgrid=False, title=None, tickfont=dict(size=11), categoryorder='array', categoryarray=df_mes['Mes'].tolist()), showlegend=False)
            st.plotly_chart(fig_mes_h, use_container_width=True)

            st.markdown("<p style='font-size:12px; margin-top:5px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones</p>", unsafe_allow_html=True)
            df_mapa_valido = df_filtrado.dropna(subset=['latitud', 'longitud'])
            map_lat = df_mapa_valido['latitud'].mean() if not df_mapa_valido.empty else lat_centro
            map_lon = df_mapa_valido['longitud'].mean() if not df_mapa_valido.empty else lon_centro
            
            mapa_miaa = folium.Map(location=[map_lat, map_lon], zoom_start=12)
            folium.TileLayer(
                tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key_carto}",
                name="Vista Nocturna",
                attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains="abcd",
                max_zoom=20,
                overlay=False,
                control=True
            ).add_to(mapa_miaa)

            for _, row in df_mapa_valido.iterrows():
                folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#3b82f6', fill=True, fill_color='#3b82f6', fill_opacity=0.7).add_to(mapa_miaa)
            st_folium(mapa_miaa, width=None, height=190, use_container_width=True, key="mapa_estatico_instalaciones", returned_objects=[])

    # PESTAÑA: PERSONAL EXTERNO
    with tab_externo:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>👷 Resumen de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
        e_k1, e_k2, e_k3 = st.columns(3)
        with e_k1: st.metric("Total Instalados (Externo)", f"{len(df_externo):,}")
        with e_k2: st.metric("Colonias Atendidas", f"{df_externo['colonia'].nunique() if 'colonia' in df_externo.columns and not df_externo.empty else 0:,}")
        with e_k3: st.metric("Sin Coordenadas", f"{df_externo['latitud'].isna().sum() if not df_externo.empty else 0:,}")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
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
            fig_ext_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_ext_dia, use_container_width=True)

        with col_ex2:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Distribución por Nivel (Externo)</p>", unsafe_allow_html=True)
            if 'nivel' in df_externo.columns and not df_externo.empty:
                df_ext_nivel = df_externo['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
                df_ext_nivel.columns = ['Nivel', 'Cantidad']
                fig_ext_niv = px.bar(df_ext_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_ext_niv.update_traces(textposition='outside', textfont_size=10)
            else:
                fig_ext_niv = px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad', text='Cantidad')
            fig_ext_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_ext_niv, use_container_width=True)

        st.markdown("<p style='font-size:12px; margin-top:5px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones - Personal Externo</p>", unsafe_allow_html=True)
        df_ext_map = df_externo.dropna(subset=['latitud', 'longitud']) if not df_externo.empty else pd.DataFrame()
        mapa_ext = folium.Map(location=[df_ext_map['latitud'].mean() if not df_ext_map.empty else lat_centro, df_ext_map['longitud'].mean() if not df_ext_map.empty else lon_centro], zoom_start=12)
        folium.TileLayer(
            tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key_carto}",
            name="Vista Nocturna",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains="abcd",
            max_zoom=20,
            overlay=False,
            control=True
        ).add_to(mapa_ext)

        for _, row in df_ext_map.iterrows():
            folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#f59e0b', fill=True, fill_color='#f59e0b', fill_opacity=0.7).add_to(mapa_ext)
        st_folium(mapa_ext, width=None, height=220, use_container_width=True, key="mapa_externo", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal Externo</p>", unsafe_allow_html=True)
        df_tabla_ext = df_externo.copy()
        if not df_tabla_ext.empty:
            df_tabla_ext = df_tabla_ext.drop(columns=[c for c in df_tabla_ext.columns if any(t in c.lower() for t in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore')
            if 'fechaInstalacion' in df_tabla_ext.columns: df_tabla_ext['fechaInstalacion'] = pd.to_datetime(df_tabla_ext['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
            df_tabla_ext = df_tabla_ext.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')
        st.dataframe(df_tabla_ext, use_container_width=True)

    # PESTAÑA: PERSONAL MIAA
    with tab_miaa:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🏢 Resumen de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
        m_k1, m_k2, m_k3 = st.columns(3)
        with m_k1: st.metric("Total Instalados (MIAA)", f"{len(df_miaa_pers):,}")
        with m_k2: st.metric("Colonias Atendidas", f"{df_miaa_pers['colonia'].nunique() if 'colonia' in df_miaa_pers.columns and not df_miaa_pers.empty else 0:,}")
        with m_k3: st.metric("Sin Coordenadas", f"{df_miaa_pers['latitud'].isna().sum() if not df_miaa_pers.empty else 0:,}")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        col_mi1, col_mi2 = st.columns(2)
        with col_mi1:
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
            fig_miaa_dia.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_miaa_dia, use_container_width=True)

        with col_mi2:
            st.markdown("<p style='font-size:12px; margin-bottom:0; font-weight:bold;'>Distribución por Nivel (MIAA)</p>", unsafe_allow_html=True)
            if 'nivel' in df_miaa_pers.columns and not df_miaa_pers.empty:
                df_miaa_nivel = df_miaa_pers['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
                df_miaa_nivel.columns = ['Nivel', 'Cantidad']
                fig_miaa_niv = px.bar(df_miaa_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_miaa_niv.update_traces(textposition='outside', textfont_size=10)
            else:
                fig_miaa_niv = px.bar(pd.DataFrame({'Nivel': ['Sin datos'], 'Cantidad': [0]}), x='Nivel', y='Cantidad', text='Cantidad')
            fig_miaa_niv.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_miaa_niv, use_container_width=True)

        st.markdown("<p style='font-size:12px; margin-top:5px; margin-bottom:0; font-weight:bold;'>Mapa de Instalaciones - Personal MIAA</p>", unsafe_allow_html=True)
        df_miaa_map = df_miaa_pers.dropna(subset=['latitud', 'longitud']) if not df_miaa_pers.empty else pd.DataFrame()
        mapa_miaa_pers = folium.Map(location=[df_miaa_map['latitud'].mean() if not df_miaa_map.empty else lat_centro, df_miaa_map['longitud'].mean() if not df_miaa_map.empty else lon_centro], zoom_start=12)
        folium.TileLayer(
            tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key_carto}",
            name="Vista Nocturna",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains="abcd",
            max_zoom=20,
            overlay=False,
            control=True
        ).add_to(mapa_miaa_pers)

        for _, row in df_miaa_map.iterrows():
            folium.CircleMarker(location=[float(row['latitud']), float(row['longitud'])], radius=2.5, color='#10b981', fill=True, fill_color='#10b981', fill_opacity=0.7).add_to(mapa_miaa_pers)
        st_folium(mapa_miaa_pers, width=None, height=220, use_container_width=True, key="mapa_miaa_personal", returned_objects=[])

        st.markdown("<p style='font-size:14px; font-weight:bold; margin-top:15px; margin-bottom:5px;'>Tabla de Registros - Personal MIAA</p>", unsafe_allow_html=True)
        df_tabla_miaa = df_miaa_pers.copy()
        if not df_tabla_miaa.empty:
            df_tabla_miaa = df_tabla_miaa.drop(columns=[c for c in df_tabla_miaa.columns if any(t in c.lower() for t in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore')
            if 'fechaInstalacion' in df_tabla_miaa.columns: df_tabla_miaa['fechaInstalacion'] = pd.to_datetime(df_tabla_miaa['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
            df_tabla_miaa = df_tabla_miaa.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')
        st.dataframe(df_tabla_miaa, use_container_width=True)

    # PESTAÑA: TABLA BASE DE DATOS COMPLETA
    with tab_tabla:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>📋 Tabla Completa de Registros de la API</p>", unsafe_allow_html=True)
        t_col1, t_col2 = st.columns(2)
        with t_col1: st.metric("Total de Registros", f"{len(df_filtrado):,}")
        with t_col2: st.metric("Colonias Registradas", f"{df_filtrado['colonia'].nunique() if 'colonia' in df_filtrado.columns else 0:,}")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:13px; font-weight:bold; margin-bottom:0;'>Distribución por Nivel</p>", unsafe_allow_html=True)
        if 'nivel' in df_filtrado.columns:
            df_nivel = df_filtrado['nivel'].fillna("SIN NIVEL").value_counts().reset_index()
            df_nivel.columns = ['Nivel', 'Cantidad']
            fig_nivel = px.bar(df_nivel, x='Nivel', y='Cantidad', text='Cantidad', color='Nivel', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_nivel.update_traces(textposition='outside', textfont_size=11)
            fig_nivel.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', margin=dict(t=30, b=5, l=5, r=5), height=220, xaxis_title=None, yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_nivel, use_container_width=True)
        else:
            st.info("La columna 'nivel' no se encuentra disponible.")

        df_tabla_limpia = df_filtrado.copy()
        df_tabla_limpia = df_tabla_limpia.drop(columns=[c for c in df_tabla_limpia.columns if any(t in c.lower() for t in ['foto', 'fecharegistro', 'fechamodificacion', 'uuid', 'horafin', 'lecturaanterior', 'lecturaactual', 'folio'])], errors='ignore')
        if 'fechaInstalacion' in df_tabla_limpia.columns: df_tabla_limpia['fechaInstalacion'] = pd.to_datetime(df_tabla_limpia['fechaInstalacion'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
        if 'horaInicio' in df_tabla_limpia.columns: df_tabla_limpia['horaInicio'] = pd.to_datetime(df_tabla_limpia['horaInicio'], errors='coerce').dt.strftime('%H:%M')
        df_tabla_limpia = df_tabla_limpia.drop(columns=['fecha_dt', 'Semana', 'fecha_dia', 'anio_mes', 'periodo_mes'], errors='ignore')
        st.dataframe(df_tabla_limpia, use_container_width=True)

    # PESTAÑA: POLÍGONOS (Diccionario_poligonos_instalacion)
    with tab_poligonos:
        st.markdown("<p style='font-size:16px; font-weight:bold; margin-bottom:10px;'>🗺️ Visualización de Polígonos de Instalación</p>", unsafe_allow_html=True)
        
        if not df_poligonos.empty:
            total_pols = df_poligonos['FID'].nunique() if 'FID' in df_poligonos.columns else 0
            total_verts = len(df_poligonos)

            p_col1, p_col2 = st.columns(2)
            with p_col1: st.metric("Total de Polígonos (FID)", f"{total_pols:,}")
            with p_col2: st.metric("Vértices Totales", f"{total_verts:,}")

            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            map_lat_p, map_lon_p = lat_centro, lon_centro
            if 'Latitud' in df_poligonos.columns and 'Longitud' in df_poligonos.columns:
                valid_coords = df_poligonos.dropna(subset=['Latitud', 'Longitud'])
                if not valid_coords.empty:
                    map_lat_p = valid_coords['Latitud'].mean()
                    map_lon_p = valid_coords['Longitud'].mean()

            mapa_poligonos = folium.Map(location=[map_lat_p, map_lon_p], zoom_start=12)
            folium.TileLayer(
                tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={api_key_carto}",
                name="Vista Nocturna",
                attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains="abcd",
                max_zoom=20,
                overlay=False,
                control=True
            ).add_to(mapa_poligonos)

            if {'FID', 'Latitud', 'Longitud', 'Vertice'}.issubset(df_poligonos.columns):
                for fid_id, grupo_pol in df_poligonos.groupby('FID'):
                    puntos_df = grupo_pol.dropna(subset=['Latitud', 'Longitud']).sort_values('Vertice')
                    
                    if len(puntos_df) >= 3:
                        puntos = puntos_df[['Latitud', 'Longitud']].values.tolist()
                        centro_lat = puntos_df['Latitud'].mean()
                        centro_lon = puntos_df['Longitud'].mean()

                        folium.Polygon(
                            locations=puntos,
                            color='#2563eb',
                            weight=2.5,
                            fill=True,
                            fill_color='#3b82f6',
                            fill_opacity=0.4,
                            tooltip=f"Polígono FID: {fid_id}"
                        ).add_to(mapa_poligonos)

                        folium.Marker(
                            location=[centro_lat, centro_lon],
                            icon=folium.DivIcon(
                                html=f"""<div style="font-size: 10px; color: #1e293b; background: rgba(255, 255, 255, 0.85); padding: 2px 5px; border-radius: 4px; text-align: center; border: 1px solid #2563eb;"><b>FID-{fid_id}</b></div>"""
                            )
                        ).add_to(mapa_poligonos)

            st_folium(mapa_poligonos, width=None, height=500, use_container_width=True, key="mapa_diccionario_poligonos", returned_objects=[])
            
            with st.expander("Ver tabla de datos de polígonos"):
                st.dataframe(df_poligonos, use_container_width=True)
        else:
            st.warning("No se encontraron registros en la tabla `Diccionario_poligonos_instalacion` o faltan las columnas requeridas.")
