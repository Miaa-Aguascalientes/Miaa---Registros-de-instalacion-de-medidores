import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(page_title="Gestor de Medidores MIAA", page_icon="💧", layout="wide")

st.title("💧 Consulta de Instalación de Medidores - MIAA")

# Campos de entrada en la barra lateral
st.sidebar.header("Credenciales de Acceso")
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

    # Tarjetas de indicadores
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Total Instalados", value=total_instalaciones)
    with m2:
        st.metric(label="Promedio por Día", value=promedio_dia)
    with m3:
        colonias_unicas = df['colonia'].nunique() if 'colonia' in df.columns else 0
        st.metric(label="Colonias Atendidas", value=colonias_unicas)
    with m4:
        niveles_unicos = df['nivel'].nunique() if 'nivel' in df.columns else 0
        st.metric(label="Niveles Tarifarios", value=niveles_unicos)

    # Resumen agrupado por Colonia (Preparado para cruzar con la base de datos de metas totales)
    if 'colonia' in df.columns:
        st.markdown("##### 📌 Avance de Instalación por Colonia")
        
        # Agrupamos lo instalado actual desde la API
        df_resumen_colonia = df.groupby('colonia').agg(
            Med_Inst=('predio', 'count'),
            Nivel_Tarifario=('nivel', lambda x: ', '.join(x.dropna().unique()[:2]))
        ).reset_index()
        
        # Columna temporal vacía para los medidores totales (pendiente de BD)
        df_resumen_colonia['Med_Tot'] = "Pendiente (BD)"
        df_resumen_colonia['%_Avance'] = "Pendiente (BD)"
        
        # Reordenar columnas para que coincida con tu esquema deseado
        df_resumen_colonia = df_resumen_colonia[['colonia', 'Med_Tot', 'Med_Inst', '%_Avance', 'Nivel_Tarifario']]
        df_resumen_colonia.columns = ['Colonia', 'Med. Tot.', 'Med. Inst.', '% Avance', 'Nivel Tarifario']
        
        st.dataframe(df_resumen_colonia, use_container_width=True)

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
