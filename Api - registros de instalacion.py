import requests
import json

# 1. Configuración de URLs y credenciales
url_login = "https://prelec.miaa.mx/auth/v2/login"
url_instalaciones = "https://prelec.miaa.mx/msvc-tecnica/medidores/instalaciones"

payload_login = {
    "username": "pedro.templos@miaa.mx",
    "password": "Pedro0208"
}

headers = {
    "Content-Type": "application/json"
}

print("Autenticándose en la API...")

# 2. Solicitud para obtener el token
response_login = requests.post(url_login, json=payload_login, headers=headers)

if response_login.status_code == 200:
    data_login = response_login.json()
    
    # Nota: Dependiendo de cómo devuelva el token la API, 
    # comúnmente viene en una llave como "token", "access_token" o similar.
    # Imprimiremos la respuesta completa por seguridad si la estructura varía.
    print("¡Autenticación exitosa!")
    
    # Intentamos extraer el token (ajusta la clave si el JSON usa otra, ej: data_login['access_token'])
    token = data_login.get("token") or data_login.get("access_token")
    
    if not token:
        # Si no tiene una clave estándar, mostramos el JSON para identificarla
        print("Estructura de respuesta de login:", json.dumps(data_login, indent=2))
        token = input("Pega aquí el token o la llave de acceso que aparece arriba: ").strip()

    # 3. Consulta al endpoint protegido con el token obtenido
    headers_auth = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print("Obteniendo el listado de instalaciones de medidores...")
    response_inst = requests.get(url_instalaciones, headers=headers_auth)

    if response_inst.status_code == 200:
        print("¡Datos obtenidos correctamente!")
        resultado = response_inst.json()
        print(json.dumps(resultado, indent=2))
        
        # Opcional: Guardar el resultado en un archivo JSON local
        with open("instalaciones_medidores.json", "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print("Los datos se han guardado en 'instalaciones_medidores.json'")
    else:
        print(f"Error al obtener las instalaciones: {response_inst.status_code}")
        print(response_inst.text)

else:
    print(f"Error de autenticación: {response_login.status_code}")
    print(response_login.text)