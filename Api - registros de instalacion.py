import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Gestor de Medidores MIAA", 
    page_icon="https://www.miaa.mx/favicon.ico", 
    layout="wide"
)

# Estilos CSS avanzados con animaciones, efectos hover y centrado completo de métricas (títulos y números)
custom_style = """
    <style>
    /* Ocultar barra superior, menú y footer de Streamlit */
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Forzar que la barra lateral permanezca siempre abierta, visible y con animación sutil de entrada */
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

    /* Subir el contenido del área principal eliminando el espacio superior */
    .block-container {
        padding-top: 0.8rem !important;
        margin-top: 0px !important;
        animation: fadeIn 0.8s ease-in-out;
    }

    /* Subir el logotipo de la barra lateral al borde superior */
    [data-testid="stSidebar"] div[data-testid="stImage"] {
        margin-top: -35px !important;
        padding-top: 0px !important;
        transition: transform 0.3s ease;
    }
    
    [data-testid="stSidebar"] div[data-testid="stImage"]:hover {
        transform: scale(1.02);
    }

    /* ==========================================
       ANIMACIONES Y MOVIMIENTO ("VIDA" UI)
       ========================================== */
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

    /* Tarjetas de Métricas con altura reducida y padding menor */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 6px 10px !important;
        border-radius: 12px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: pulseGlow 4s infinite;
        text-align: center;
    }

    [data-testid="stMetric"] > div {
        align-items: center !important;
        gap: 2px !important;
    }

    /* Centrar tanto los títulos (labels) como los valores (values) de las métricas y reducir el tamaño de los números */
    [data-testid="stMetricLabel"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        text-align: center !important;
        font-size: 13px !important;
    }

    [data-testid="stMetricLabel"] > div {
        text-align: center !important;
        justify-content: center !important;
    }

    [data-testid="stMetricValue"] {
        justify-content: center !important;
        display: flex !important;
        width: 100% !important;
        font-size: 26px !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #00a8cc;
        box-shadow: 0 8px 25px rgba(0, 168, 204, 0.3);
    }

    /* Efecto dinámico en tablas */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    [data-testid="stDataFrame"]:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    /* Botones con transición fluida */
    .stButton>button, .stDownloadButton>button {
        transition: all 0.3s ease !important;
        border-radius: 8px !important;
    }

    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 168, 204, 0.4);
    }

    /* Indicador de estado en vivo (Punto Pulsante) */
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #2ecc71;
        border-radius: 50%;
        margin-right: 8px;
        box-shadow: 0 0 0 rgba(46, 204, 113, 0.4);
        animation: livePulse 2s infinite;
    }

    @keyframes livePulse {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 8px rgba(46, 204, 113, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0);
        }
    }
    </style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# Título principal en la parte superior
st.title("📊 Registro de instalacion medidores Miaa")

# Logo en la barra lateral
st.sidebar.image(
    "https://raw.githubusercontent.com/Miaa-Aguascalientes/Logos/38504978c8f77a4dac38ad476f74dbdee6af2cad/LogoMIAA.svg", 
    use_container_width=True
)

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

# Función para autenticar y obtener datos de la API automáticamente usando st.secrets
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
            data_login = res_login.json()
            token = data_login.get("token") or data_login.get("access_token")
            
            if token:
                res_inst = requests.get(
                    url_instalaciones, 
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                )
                
                if res_inst.status_code == 200:
                    return res_inst.json()
        return None
    except Exception as e:
        st.error(f"Error de conexión con la API: {e}")
        return None

# Función para cargar las metas de medidores desde la base de datos MySQL usando st.secrets
@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        connection_string = st.secrets["mysql"]["connection_string"]
        engine = create_engine(connection_string)
        query = "SELECT Colonia_ATL, Usuarios_nueva_instalacion, Poligono_de_instalacion FROM Diccionario_instalacion_medidores"
        df_metas = pd.read_sql(query, con=engine)
        return df_metas
    except Exception as e:
        st.error(f"Error al conectar con la base de datos MySQL: {e}")
        return pd.DataFrame()

# Cargar automáticamente al abrir la aplicación
if 'datos_instalaciones' not in st.session_state:
    with st.spinner("Conectando y cargando registros desde la API y Base de Datos..."):
        resultado_api = cargar_datos_api()
        if resultado_api:
            st.session_state['datos_instalaciones'] = resultado_api
        else:
            st.error("No se pudieron cargar los datos de la API. Verifica tus secretos.")

# Si ya tenemos datos en la sesión, procesamos y mostramos el dashboard superior y las tablas
if 'datos_instalaciones' in st.session_state:
    data = st.session_state['datos_instalaciones']
    
    if isinstance(data, dict):
        lista_registros = []
        for key, value in data.items():
            if isinstance(value, list):
                lista_registros.extend(value)
            elif isinstance(value, dict):
                for sub_k, sub_v in value.items():
                    if isinstance(sub_v, dict):
                        lista_registros.append(sub_v)
                    else:
                        lista_registros.append(value)
                        break
        df = pd.DataFrame(lista_registros) if lista_registros else pd.DataFrame([data])
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame([data])

    # Formatear columnas de fecha y asegurar tipo datetime para ordenamiento
    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    
    if col_fecha_ref:
        df['fecha_dt'] = pd.to_datetime(df[col_fecha_ref], errors='coerce')
    else:
        df['fecha_dt'] = pd.NaT

    for col in df.columns:
        if 'fecha' in col.lower() and col != 'fecha_dt':
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M').fillna(df[col])

    # Detectar columna de personal externo
    col_externo_candidatos = [c for c in df.columns if any(k in c.lower() for k in ['extern', 'tercero', 'contratista'])]
    col_externo = col_externo_candidatos[0] if col_externo_candidatos else None

    if col_externo:
        df['Tipo_Personal'] = df[col_externo].apply(lambda x: "Personal Externo" if str(x).lower() in ['true', '1', 'yes', 'si', 't'] else "Personal MIAA")
    else:
        df['Tipo_Personal'] = "Personal MIAA"

    # ==========================================
    # FILTRO EN BARRA LATERAL (Personal Externo / MIAA)
    # ==========================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("<p style='font-size: 14px; color: #2ecc71; margin-bottom: 5px;'><span class='live-indicator'></span>Sistema en Línea (MIAA)</p>", unsafe_allow_html=True)
    st.sidebar.header("Filtros Operativos")
    filtro_personal = st.sidebar.selectbox("Tipo de Personal", ["Todos", "Personal MIAA", "Personal Externo"])

    if filtro_personal == "Personal MIAA":
        df_filtrado_personal = df[df['Tipo_Personal'] == "Personal MIAA"]
    elif filtro_personal == "Personal Externo":
        df_filtrado_personal = df[df['Tipo_Personal'] == "Personal Externo"]
    else:
        df_filtrado_personal = df.copy()

    columnas_to_hide = ['uuid', 'Tipo_Personal', 'fecha_dt'] + [col for col in df.columns if 'foto' in col.lower()]
    df_display = df_filtrado_personal.drop(columns=[c for c in columnas_to_hide if c in df_filtrado_personal.columns], errors='ignore')

    # ==========================================
    # DASHBOARD SUPERIOR (Métricas)
    # ==========================================
    total_instalaciones = len(df_filtrado_personal)
    df_miaa_all = df[df['Tipo_Personal'] == "Personal MIAA"]
    df_externo_all = df[df['Tipo_Personal'] == "Personal Externo"]
    
    total_miaa = len(df_miaa_all)
    total_externo = len(df_externo_all)
    
    # Promedio General del filtro actual
    promedio_dia = 0
    if col_fecha_ref and not df_filtrado_personal.empty:
        fechas_unicas = df_filtrado_personal['fecha_dt'].dt.date.dropna().unique()
        if len(fechas_unicas) > 0:
            promedio_dia = round(total_instalaciones / len(fechas_unicas), 1)

    # Promedio Específico para MIAA
    promedio_miaa = 0
    if col_fecha_ref and not df_miaa_all.empty:
        fechas_miaa = df_miaa_all['fecha_dt'].dt.date.dropna().unique()
        if len(fechas_miaa) > 0:
            promedio_miaa = round(total_miaa / len(fechas_miaa), 1)

    # Promedio Específico para Personal Externo
    promedio_externo = 0
    if col_fecha_ref and not df_externo_all.empty:
        fechas_externo = df_externo_all['fecha_dt'].dt.date.dropna().unique()
        if len(fechas_externo) > 0:
            promedio_externo = round(total_externo / len(fechas_externo), 1)

    df_metas = cargar_metas_db()
    total_meta_global = df_metas['Usuarios_nueva_instalacion'].sum() if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else 0

    # 7 Columnas con títulos y números perfectamente centrados y altura compacta
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    with m1:
        st.metric(label="Total Registros", value=total_instalaciones)
    with m2:
        st.metric(label="Promedio / Día", value=promedio_dia)
    with m3:
        st.metric(label="👨‍💼 Inst. MIAA", value=total_miaa)
    with m4:
        st.metric(label="Prom. MIAA / Día", value=promedio_miaa)
    with m5:
        st.metric(label="👷 Inst. Externo", value=total_externo)
    with m6:
        st.metric(label="Prom. Ext. / Día", value=promedio_externo)
    with m7:
        st.metric(label="Meta Total (BD)", value=total_meta_global)

    if 'colonia' in df.columns and not df_metas.empty:
        df_filtrado_personal['colonia_norm'] = df_filtrado_personal['colonia'].astype(str).str.strip().str.upper()
        df_metas['colonia_norm'] = df_metas['Colonia_ATL'].astype(str).str.strip().str.upper()
        
        # Fecha actual para filtrar medidores instalados hoy
        hoy_date = pd.Timestamp.today().normalize()
        
        # Agregación incluyendo el conteo de instalaciones de hoy y la última fecha para ordenar de mayor a menor instalación hoy
        df_resumen_api = df_filtrado_personal.groupby('colonia_norm').agg(
            Colonia_Real=('colonia', 'first'),
            Med_Inst=('predio', 'count'),
            Inst_Hoy=('fecha_dt', lambda x: (pd.to_datetime(x).dt.normalize() == hoy_date).sum()),
            Ultima_Fecha=('fecha_dt', 'max'),
            Nivel_Tarifario=('nivel', lambda x: ', '.join(x.dropna().unique()[:2]))
        ).reset_index()
        
        df_merged = pd.merge(
            df_metas,
            df_resumen_api,
            on='colonia_norm',
            how='left'
        )
        
        df_merged['Med_Inst'] = df_merged['Med_Inst'].fillna(0).astype(int)
        df_merged['Inst_Hoy'] = df_merged['Inst_Hoy'].fillna(0).astype(int)
        df_merged['Med_Tot'] = df_merged['Usuarios_nueva_instalacion'].fillna(0).astype(int)
        df_merged['Poligono'] = df_merged['Poligono_de_instalacion'].fillna(0).astype(int)
        df_merged['Colonia'] = df_merged['Colonia_ATL'].fillna(df_merged['Colonia_Real'])
        df_merged['Nivel_Tarifario'] = df_merged['Nivel_Tarifario'].fillna("N/D")
        
        # Ordenar principal por Inst_Hoy descendente (más instalados hoy arriba) y secundario por Med_Inst descendente
        df_merged = df_merged.sort_values(by=['Inst_Hoy', 'Med_Inst', 'Ultima_Fecha'], ascending=[False, False, False], na_position='last')
        
        df_merged['Porcentaje_Avance_Num'] = df_merged.apply(
            lambda row: round((row['Med_Inst'] / row['Med_Tot']) * 100, 1) if row['Med_Tot'] > 0 else 0.0, 
            axis=1
        )
        
        df_merged['%_Avance'] = df_merged['Porcentaje_Avance_Num'].astype(str) + "%"

        # ==========================================
        # SECCIÓN DE GRÁFICAS ANALÍTICAS AVANZADAS (ARRIBA DE LA TABLA)
        # ==========================================
        st.markdown("---")
        st.subheader("📈 Análisis Gráfico de Operaciones y Avances")

        # Top 10 colonias para visualizaciones limpias
        df_top10 = df_merged.sort_values(by='Med_Inst', ascending=False).head(10)
        df_top10_hoy = df_merged[df_merged['Inst_Hoy'] > 0].sort_values(by='Inst_Hoy', ascending=False).head(10)

        gcol1, gcol2 = st.columns(2)

        with gcol1:
            st.markdown("##### 🏢 Instalados vs Meta Total (Top 10)")
            fig_bar_comp = px.bar(
                df_top10,
                x='Colonia',
                y=['Med_Tot', 'Med_Inst'],
                barmode='group',
                labels={'value': 'Número de Medidores', 'variable': 'Métrica'},
                color_discrete_map={'Med_Tot': '#3498db', 'Med_Inst': '#2ecc71'}
            )
            fig_bar_comp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff',
                xaxis_tickangle=-35,
                margin=dict(t=20, b=40, l=20, r=20)
            )
            st.plotly_chart(fig_bar_comp, use_container_width=True)

        with gcol2:
            st.markdown("##### ⚡ Productividad Diaria (Instalaciones Hoy)")
            if not df_top10_hoy.empty:
                fig_hoy = px.bar(
                    df_top10_hoy,
                    x='Inst_Hoy',
                    y='Colonia',
                    orientation='h',
                    labels={'Inst_Hoy': 'Instalaciones Realizadas Hoy', 'Colonia': 'Colonia'},
                    color='Inst_Hoy',
                    color_continuous_scale='Tealgrn'
                )
                fig_hoy.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#ffffff',
                    yaxis={'categoryorder': 'total ascending'},
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_hoy, use_container_width=True)
            else:
                st.info("No hay instalaciones registradas el día de hoy.")

        gcol3, gcol4 = st.columns(2)

        with gcol3:
            st.markdown("##### 🎯 Porcentaje de Avance por Colonia (Top 10)")
            df_avance_top = df_merged.sort_values(by='Porcentaje_Avance_Num', ascending=False).head(10)
            fig_avance = px.bar(
                df_avance_top,
                x='Porcentaje_Avance_Num',
                y='Colonia',
                orientation='h',
                labels={'Porcentaje_Avance_Num': 'Avance (%)', 'Colonia': 'Colonia'},
                text='%_Avance',
                color='Porcentaje_Avance_Num',
                color_continuous_scale='Viridis'
            )
            fig_avance.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff',
                yaxis={'categoryorder': 'total ascending'},
                margin=dict(t=20, b=20, l=20, r=20)
            )
            fig_avance.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig_avance, use_container_width=True)

        with gcol4:
            st.markdown("##### 🗺️ Distribución de Medidores Instalados por Polígono")
            df_poligono = df_merged.groupby('Poligono')[['Med_Inst', 'Med_Tot']].sum().reset_index()
            fig_poly = px.pie(
                df_poligono,
                names='Poligono',
                values='Med_Inst',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig_poly.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_poly, use_container_width=True)

        # ==========================================
        # TABLA PRINCIPAL DE AVANCE POR COLONIA
        # ==========================================
        df_tabla_final = df_merged[['Colonia', 'Med_Tot', 'Med_Inst', 'Inst_Hoy', '%_Avance', 'Poligono', 'Nivel_Tarifario']]
        df_tabla_final.columns = ['Colonia', 'Med. Tot.', 'Med. Inst.', 'Inst. Hoy', '% Avance', 'Polígono', 'Nivel Tarifario']
        
        st.dataframe(df_tabla_final, use_container_width=True, hide_index=True)

    elif 'colonia' in df.columns:
        st.info("Conectando con la base de datos para mostrar el desglose de metas por colonia...")

    st.markdown("---")
    st.subheader("📋 Detalle General de Registros")
    
    busqueda = st.text_input("🔍 Buscar por cliente, predio, colonia o serie de medidor:")
    
    if busqueda and not df_display.empty:
        mask = df_display.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        df_filtrado = df_display[mask]
    else:
        df_filtrado = df_display

    st.dataframe(df_filtrado, use_container_width=True)

    st.divider()
    st.subheader("👁️ Vista Detallada por Registro y Fotografías")
    
    if not df_filtrado.empty:
        opciones_select = []
        for idx, row in df_filtrado.iterrows():
            cliente = row.get('nombreClienteVia', row.get('nombreCliente', 'Sin Nombre'))
            predio = row.get('predio', 'S/N')
            serie = row.get('serie', 'S/N')
            opciones_select.append(f"Índice {idx} | Predio: {predio} | Cliente: {cliente} | Serie: {serie}")
            
        seleccion = st.selectbox("Selecciona un registro para ver sus detalles y evidencias fotográficas:", opciones_select)
        
        if seleccion:
            idx_seleccionado = int(seleccion.split(" | ")[0].replace("Índice ", ""))
            registro = df.loc[idx_seleccionado]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📋 Información del Servicio")
                st.write(f"**Predio:** {registro.get('predio')}")
                st.write(f"**Cliente:** {registro.get('nombreCliente')}")
                st.write(f"**Colonia:** {registro.get('colonia')}")
                st.write(f"**Domicilio:** {registro.get('domicilio')}")
                st.write(f"**Giro:** {registro.get('giro')} ({registro.get('nivel')})")
                st.write(f"**Serie Medidor:** {registro.get('serie')}")
                st.write(f"**Fecha de Instalación:** {registro.get('fechaInstalacion')}")
                st.write(f"**Técnico Responsable:** {registro.get('usuarioNombre')} (ID: {registro.get('usuarioId')})")
                st.write(f"**Tipo de Personal:** {registro.get('Tipo_Personal')}")
                st.write(f"**Lectura Anterior:** {registro.get('lecturaAnterior')} | **Actual:** {registro.get('lecturaActual')}")

            with col2:
                st.markdown("### 📸 Evidencias Fotográficas")
                fotos = {
                    "Foto Medidor Anterior": registro.get('fotoMedidorAnterior'),
                    "Foto Fachada": registro.get('fotoFachada'),
                    "Foto Columpio / Registro": registro.get('fotoColumpioRegistro'),
                    "Foto Medidor ID Visible": registro.get('fotoMedidorIdVisible')
                }
                
                hay_fotos = False
                for titulo, url_foto in fotos.items():
                    if url_foto and str(url_foto).lower() not in ["nan", "none", "null", ""]:
                        try:
                            st.image(url_foto, caption=titulo, use_container_width=True)
                            hay_fotos = True
                        except Exception as img_err:
                            st.warning(f"No se pudo cargar la imagen de {titulo}: {img_err}")
                
                if not hay_fotos:
                    st.info("Este registro no cuenta con evidencias fotográficas disponibles.")

    st.download_button(
        label="📥 Descargar todos los registros en JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="instalaciones_medidores_miaa.json",
        mime="application/json"
    )
