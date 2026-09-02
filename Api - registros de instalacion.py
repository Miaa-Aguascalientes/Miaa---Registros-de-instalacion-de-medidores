import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Gestor de Medidores MIAA", page_icon="💧", layout="wide")

# Ocultar la barra superior (Header), el menú desplegable y el pie de página de Streamlit
hide_streamlit_style = """
    <style>
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("💧 Consulta de Instalación de Medidores - MIAA")

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
            st.error("No se pudieron cargar los datos de la API. Verifica tus credenciales en los secretos.")

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

    # Formatear columnas de fecha
    for col in df.columns:
        if 'fecha' in col.lower():
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
    st.sidebar.header("Filtros Operativos")
    filtro_personal = st.sidebar.selectbox("Tipo de Personal", ["Todos", "Personal MIAA", "Personal Externo"])

    if filtro_personal == "Personal MIAA":
        df_filtrado_personal = df[df['Tipo_Personal'] == "Personal MIAA"]
    elif filtro_personal == "Personal Externo":
        df_filtrado_personal = df[df['Tipo_Personal'] == "Personal Externo"]
    else:
        df_filtrado_personal = df.copy()

    columnas_to_hide = ['uuid', 'Tipo_Personal'] + [col for col in df.columns if 'foto' in col.lower()]
    df_display = df_filtrado_personal.drop(columns=[c for c in columnas_to_hide if c in df_filtrado_personal.columns], errors='ignore')

    # ==========================================
    # DASHBOARD SUPERIOR
    # ==========================================
    st.markdown("---")
    st.subheader("📊 Dashboard Principal - Resumen Operativo")
    
    total_instalaciones = len(df_filtrado_personal)
    total_miaa = len(df[df['Tipo_Personal'] == "Personal MIAA"])
    total_externo = len(df[df['Tipo_Personal'] == "Personal Externo"])
    
    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    promedio_dia = 0
    if col_fecha_ref and not df_filtrado_personal.empty:
        fechas_unicas = pd.to_datetime(df_filtrado_personal[col_fecha_ref].str[:10], errors='coerce').dropna().unique()
        if len(fechas_unicas) > 0:
            promedio_dia = round(total_instalaciones / len(fechas_unicas), 1)

    df_metas = cargar_metas_db()
    total_meta_global = df_metas['Usuarios_nueva_instalacion'].sum() if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Total Registros", value=total_instalaciones)
    with m2:
        st.metric(label="👨‍💼 Personal MIAA", value=total_miaa)
    with m3:
        st.metric(label="👷 Personal Externo", value=total_externo)
    with m4:
        st.metric(label="Promedio / Día", value=promedio_dia)
    with m5:
        st.metric(label="Meta Total (BD)", value=total_meta_global)

    if 'colonia' in df.columns and not df_metas.empty:
        st.markdown("##### 📌 Avance de Instalación por Colonia (Cruce con Base de Datos)")
        
        df_filtrado_personal['colonia_norm'] = df_filtrado_personal['colonia'].astype(str).str.strip().str.upper()
        df_metas['colonia_norm'] = df_metas['Colonia_ATL'].astype(str).str.strip().str.upper()
        
        df_resumen_api = df_filtrado_personal.groupby('colonia_norm').agg(
            Colonia_Real=('colonia', 'first'),
            Med_Inst=('predio', 'count'),
            Nivel_Tarifario=('nivel', lambda x: ', '.join(x.dropna().unique()[:2]))
        ).reset_index()
        
        df_merged = pd.merge(
            df_metas,
            df_resumen_api,
            on='colonia_norm',
            how='left'
        )
        
        df_merged['Med_Inst'] = df_merged['Med_Inst'].fillna(0).astype(int)
        df_merged['Med_Tot'] = df_merged['Usuarios_nueva_instalacion'].fillna(0).astype(int)
        df_merged['Poligono'] = df_merged['Poligono_de_instalacion'].fillna(0).astype(int)
        df_merged['Colonia'] = df_merged['Colonia_ATL'].fillna(df_merged['Colonia_Real'])
        df_merged['Nivel_Tarifario'] = df_merged['Nivel_Tarifario'].fillna("N/D")
        
        df_merged['%_Avance'] = df_merged.apply(
            lambda row: f"{round((row['Med_Inst'] / row['Med_Tot']) * 100, 1)}%" if row['Med_Tot'] > 0 else "0%", 
            axis=1
        )
        
        df_tabla_final = df_merged[['Colonia', 'Med_Tot', 'Med_Inst', '%_Avance', 'Poligono', 'Nivel_Tarifario']]
        df_tabla_final.columns = ['Colonia', 'Med. Tot.', 'Med. Inst.', '% Avance', 'Polígono', 'Nivel Tarifario']
        
        st.dataframe(df_tabla_final, use_container_width=True)
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
