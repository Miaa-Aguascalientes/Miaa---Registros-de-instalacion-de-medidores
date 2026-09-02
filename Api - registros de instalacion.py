import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(page_title="Gestor de Medidores MIAA", page_icon="💧", layout="wide")

st.title("💧 Consulta de Instalación de Medidores - MIAA")
st.write("Panel visual para el registro de instalaciones de medidores.")

# Campos de entrada en la barra lateral
st.sidebar.header("Credenciales de Acceso")
usuario = st.sidebar.text_input("Usuario", value="pedro.templos@miaa.mx")
password = st.sidebar.text_input("Contraseña", type="password", value="Pedro0208")

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

if st.sidebar.button("Consultar API"):
    with st.spinner("Autenticándose y obteniendo registros..."):
        try:
            # 1. Petición de Login
            res_login = requests.post(
                url_login, 
                json={"username": usuario, "password": password}, 
                headers={"Content-Type": "application/json"}
            )
            
            if res_login.status_code == 200:
                data_login = res_login.json()
                token = data_login.get("token") or data_login.get("access_token")
                
                if token:
                    # 2. Petición al endpoint protegido
                    res_inst = requests.get(
                        url_instalaciones, 
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                    )
                    
                    if res_inst.status_code == 200:
                        resultado = res_inst.json()
                        st.success("¡Datos obtenidos correctamente!")
                        
                        # Guardamos los datos en la sesión para poder interactuar sin perderlos
                        st.session_state['datos_instalaciones'] = resultado
                    else:
                        st.error(f"Error al obtener las instalaciones (Código {res_inst.status_code})")
                else:
                    st.warning("No se encontró el token en la respuesta de autenticación.")
            else:
                st.error(f"Error de autenticación (Código {res_login.status_code})")
        except Exception as e:
            st.error(f"Ocurrió un error de conexión: {e}")

# Si ya tenemos datos en la sesión, los mostramos de forma amigable
if 'datos_instalaciones' in st.session_state:
    data = st.session_state['datos_instalaciones']
    
    # Normalizar la estructura JSON anidada para convertirla en una tabla limpia de Pandas
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

    # Ocultar / Eliminar la columna 'uuid' del DataFrame para que no aparezca
    if 'uuid' in df.columns:
        df_display = df.drop(columns=['uuid'])
    else:
        df_display = df.copy()

    st.divider()
    st.subheader("📊 Resumen General de Instalaciones")
    
    # Filtro de búsqueda rápido
    busqueda = st.text_input("🔍 Buscar por cliente, predio, colonia o serie de medidor:")
    
    if busqueda and not df_display.empty:
        mask = df_display.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        df_filtrado = df_display[mask]
    else:
        df_filtrado = df_display

    # Mostrar tabla interactiva sin uuid
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
                    if url_foto and str(url_foto).lower() != "nan" and str(url_foto).lower() != "none" and str(url_foto).lower() != "null":
                        try:
                            st.image(url_foto, caption=titulo, use_container_width=True)
                            hay_fotos = True
                        except Exception as img_err:
                            st.warning(f"No se pudo cargar la imagen de {titulo}: {img_err}")
                
                if not hay_fotos:
                    st.info("Este registro no cuenta con evidencias fotográficas disponibles.")

    # Botón para descargar respaldo en JSON limpio
    st.download_button(
        label="📥 Descargar todos los registros en JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="instalaciones_medidores_miaa.json",
        mime="application/json"
    )
