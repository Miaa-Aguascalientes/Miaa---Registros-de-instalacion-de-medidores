import streamlit as st
import requests
import json

st.set_page_config(page_title="Gestor de Medidores MIAA", page_icon="💧", layout="wide")

st.title("💧 Consulta de Instalación de Medidores - MIAA")
st.write("Interfaz para autenticarse y consultar el registro de instalaciones de medidores.")

# Campos de entrada en la interfaz
st.sidebar.header("Credenciales de Acceso")
usuario = st.sidebar.text_input("Usuario", value="pedro.templos@miaa.mx")
password = st.sidebar.text_input("Contraseña", type="password", value="Pedro0208")

url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

if st.sidebar.button("Consultar API"):
    with st.spinner("Autenticándose en la API..."):
        payload_login = {
            "username": usuario,
            "password": password
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response_login = requests.post(url_login, json=payload_login, headers=headers)
            
            if response_login.status_code == 200:
                data_login = response_login.json()
                st.success("¡Autenticación exitosa!")
                
                # Extraemos el token (ajusta la clave según la respuesta exacta de la API si es necesario)
                token = data_login.get("token") or data_login.get("access_token")
                
                if not token:
                    st.warning("No se encontró el token automáticamente. Estructura recibida:")
                    st.json(data_login)
                else:
                    headers_auth = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                    
                    with st.spinner("Obteniendo el listado de instalaciones..."):
                        response_inst = requests.get(url_instalaciones, headers=headers_auth)
                        
                        if response_inst.status_code == 200:
                            resultado = response_inst.json()
                            st.success("¡Datos obtenidos correctamente!")
                            
                            # Mostrar los datos en pantalla de forma interactiva
                            st.subheader("Listado de Instalaciones")
                            st.json(resultado)
                            
                            # Botón de descarga para el archivo JSON
                            json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
                            st.download_button(
                                label="Descargar JSON de Instalaciones",
                                data=json_str,
                                file_name="instalaciones_medidores.json",
                                mime="application/json"
                            )
                        else:
                            st.error(f"Error al obtener las instalaciones (Código {response_inst.status_code})")
                            st.text(response_inst.text)
            else:
                st.error(f"Error de autenticación (Código {response_login.status_code})")
                st.text(response_login.text)
                
        except Exception as e:
            st.error(f"Ocurrió un error de conexión: {e}")
