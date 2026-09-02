import streamlit as st
import requests
import json
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Gestor de Medidores MIAA", page_icon="💧", layout="wide")

st.title("💧 Consulta de Instalación de Medidores - MIAA")

# Campos de entrada en la barra lateral
st.sidebar.header("Credenciales de Acceso API")
usuario = st.sidebar.text_input("Usuario", value="pedro.templos@miaa.mx")
password = st.sidebar.text_input("Contraseña", type="password", value="Pedro0208")

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

if st.sidebar.button("Consultar API"):
    with st.spinner("Autenticándose y obteniendo registros..."):
        try:
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
                        resultado = res_inst.json()
                        st.success("¡Datos obtenidos correctamente!")
                        st.session_state['datos_instalaciones'] = resultado
                    else:
                        st.error(f"Error al obtener las instalaciones (Código {res_inst.status_code})")
                else:
                    st.warning("No se encontró el token en la respuesta de autenticación.")
            else:
                st.error(f"Error de autenticación (Código {res_login.status_code})")
        except Exception as e:
            st.error(f"Ocurrió un error de conexión: {e}")

# Función para cargar las metas de medidores desde la base de datos MySQL
@st.cache_data(ttl=600)
def cargar_metas_db():
    try:
        # Codificamos el caracter '&' de la contraseña como '%26' para la cadena de conexión
        connection_string = "mysql+pymysql://miaamx_telemetria2:bWkrw1Uum1O%26@miaa.mx/miaamx_telemetria2"
        engine = create_engine(connection_string)
        query = "SELECT Colonia_ATL, Usuarios_nueva_instalacion, Poligono_de_instalacion FROM Diccionario_instalacion_medidores"
        df_metas = pd.read_sql(query, con=engine)
        return df_metas
    except Exception as e:
        st.error(f"Error al conectar con la base de datos MySQL: {e}")
        return pd.DataFrame()

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

    # Ocultar uuid y fotos de la tabla principal
    columnas_a_ocultar = ['uuid'] + [col for col in df.columns if 'foto' in col.lower()]
    df_display = df.drop(columns=columnas_a_ocultar, errors='ignore')

    # ==========================================
    # DASHBOARD SUPERIOR
    # ==========================================
    st.markdown("---")
    st.subheader("📊 Dashboard Principal - Resumen Operativo")
    
    total_instalaciones = len(df)
    
    col_fecha_ref = 'fechaInstalacion' if 'fechaInstalacion' in df.columns else ('fechaRegistro' if 'fechaRegistro' in df.columns else None)
    promedio_dia = 0
    if col_fecha_ref:
        fechas_unicas = pd.to_datetime(df[col_fecha_ref].str[:10], errors='coerce').dropna().unique()
        if len(fechas_unicas) > 0:
            promedio_dia = round(total_instalaciones / len(fechas_unicas), 1)

    # Cargar metas desde la base de datos
    df_metas = cargar_metas_db()
    total_meta_global = df_metas['Usuarios_nueva_instalacion'].sum() if not df_metas.empty and 'Usuarios_nueva_instalacion' in df_metas.columns else 0

    # Tarjetas de indicadores
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Total Instalados (API)", value=total_instalaciones)
    with m2:
        st.metric(label="Meta Total (BD)", value=total_meta_global)
    with m3:
        st.metric(label="Promedio por Día", value=promedio_dia)
    with m4:
        colonias_unicas = df['colonia'].nunique() if 'colonia' in df.columns else 0
        st.metric(label="Colonias Atendidas", value=colonias_unicas)

    # Resumen cruzado por Colonia con la base de datos
    if 'colonia' in df.columns and not df_metas.empty:
        st.markdown("##### 📌 Avance de Instalación por Colonia (Cruce con Base de Datos)")
        
        # Normalizar nombres para hacer el cruce correcto
        df['colonia_norm'] = df['colonia'].astype(str).str.strip().str.upper()
        df_metas['colonia_norm'] = df_metas['Colonia_ATL'].astype(str).str.strip().str.upper()
        
        # Agrupar instalaciones reales de la API
        df_resumen_api = df.groupby('colonia_norm').agg(
            Colonia_Real=('colonia', 'first'),
            Med_Inst=('predio', 'count'),
            Nivel_Tarifario=('nivel', lambda x: ', '.join(x.dropna().unique()[:2]))
        ).reset_index()
        
        # Unir con la tabla del diccionario en la BD
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
        
        # Calcular porcentaje de avance
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
    
    # Filtro de búsqueda rápido
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
