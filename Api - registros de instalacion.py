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
    # Dependiendo de si la API devuelve una lista o un diccionario con índices numéricos:
    if isinstance(data, dict):
        # Extraer los elementos si vienen anidados por número (ej. {"800": {...}, "801": {...}})
        lista_registros = []
        for key, value in data.items():
            if isinstance(value, list):
                lista_registros.extend(value)
            elif isinstance(value, dict):
                # Si el diccionario tiene sub-niveles numéricos como en tu captura
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

    st.divider()
    st.subheader("📊 Resumen General de Instalaciones")
    
    # Filtro de búsqueda rápido
    busqueda = st.text_input("🔍 Buscar por cliente, predio, colonia o serie de medidor:")
    
    if busqueda and not df.empty:
        # Filtrar el DataFrame de manera global en columnas de texto
        mask = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        df_filtrado = df[mask]
    else:
        df_filtrado = df

    # Mostrar tabla interactiva (puedes ordenar columnas, hacer zoom, etc.)
    st.dataframe(df_filtrado, use_container_width=True)

    st.divider()
    st.subheader("👁️ Vista Detallada por Registro y Fotografías")
    
    # Selector para ver a detalle un registro específico si la tabla es grande
    if not df_filtrado.empty:
        # Crear etiquetas legibles para el selector
        opciones_select = []
        for idx, row in df_filtrado.iterrows():
            cliente = row.get('nombreClienteVia', row.get('nombreCliente', 'Sin Nombre'))
            predio = row.get('predio', 'S/N')
            serie = row.get('serie', 'S/N')
            opciones_select.append(f"Índice {idx} | Predio: {predio} | Cliente: {cliente} | Serie: {serie}")
            
        seleccion = st.selectbox("Selecciona un registro para ver sus detalles y evidencias fotográficas:", opciones_select)
        
        if seleccion:
            # Extraer el índice seleccionado
            idx_seleccionado = int(seleccion.split(" | ")[0].replace("Índice ", ""))
            registro = df.loc[idx_seleccionado]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📋 Información del Servicio")
                st.write(f"**UUID:** {registro.get('uuid')}")
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
                foto_anterior = registro.get('fotoMedidorAnterior')
                foto_fachada = registro.get('fotoFachada')
                foto_columpio = registro.get('fotoColumpioRegistro')
                foto_id_visible = registro.get('fotoMedidorIdVisible')
                
                if foto_anterior:
                    st.image(foto_anterior, caption="Foto Medidor Anterior", use_column_width=True)
                if foto_fachada:
                    st.image(foto_fachada, caption="Foto Fachada", use_column_width=True)
                if foto_columpio:
                    st.image(foto_columpio, caption="Foto Columpio / Registro", use_column_width=True)
                if foto_id_visible:
                    st.image(foto_id_visible, caption="Foto Medidor ID Visible", use_column_width=True)

    # Botón para descargar respaldo en JSON limpio
    st.download_button(
        label="📥 Descargar todos los registros en JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="instalaciones_medidores_miaa.json",
        mime="application/json"
    )
