import os
import time
from urllib.parse import quote
import xmlrpc.client

import requests
from dotenv import load_dotenv



database = os.getenv("DATABASE")
user = os.getenv("USER")
password = os.getenv("PASSWORD")
host = os.getenv("HOST")
tenant_id = os.getenv('TENANT_ID')
client_id = os.getenv('CLIENT_ID')
client_secret  = os.getenv('CLIENT_SECRET')
scope = os.getenv('SCOPE')
site_id = os.getenv('SITE_ID')
list_name = os.getenv('LIST_NAME')

"""Este módulo contiene funciones para sincronizar datos de Odoo con SharePoint ."""
def obtener_registros_pendientes():
    """Esta función trae los registros desde Odoo."""
    # Conexión al servicio de autenticación de Odoo
    common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
    uid = common.authenticate(database, user, password, {})
    # Conexión al servicio de objetos de Odoo para password operaciones en los modelos
    models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')
    # Búsqueda de empleados pendientes de sincronización
    registros = models.execute_kw(database, uid, password,
        'hr.employee', 'search_read',
        [[('x_studio_pendiente_sincronizacion', '=', 'Si')]],
        {'fields': ['identification_id','name', 'company_id',
        'job_title', 'x_studio_correo_electrnico_personal',
        'work_email', 'birthday', 'x_studio_estado_empleado']})
    if registros:
        print("Empleados pendientes de sincronización obtenidos con éxito desde Odoo.")
        return registros
    print("No se encontraron empleados pendientes de sincronización en Odoo.")
    return None
def obtener_access_token():
    """Esta función obtiene el token de Sharepoint."""
    url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    data = {
        'client_id': client_id,
        'scope': scope,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post(url, data=data, timeout=10)
    response.raise_for_status()
    token_response = response.json()
    access_token = token_response.get('access_token')
    if access_token:
        print("Token de acceso obtenido exitosamente:", access_token)
        return response.json().get('access_token')
    print("Error al obtener el token de acceso:", token_response)
    return None     # Esto lanzará un error si la solicitud falla
def verificar_si_existe( name, access_token):
    """Esta función valida los registros de Odoo si ya existen el sharepoint."""
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json", 
               "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly" }
    search_url = (
    f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}"
    f"/items?$filter=fields/field_2 eq '{quote(name)}'&$top=100"
    )
    response = requests.get(search_url, headers=headers, timeout=10)
    if response.status_code == 200 and response.json()['value']:
        item = response.json()['value'][0]
        item_id = item['id']
        etag = item.get('@odata.etag')
        print("id", item_id)
        print("etag:",etag)
        return item_id, etag
    return None, None
def marcar_registro_como_sincronizado(name):
    """Esta función Ingresa a la BD de Odoo y actualiza el registro."""
    if not name:
        print("No se proporcionó un nombre de empleado para marcar como sincronizado.")
        return
    # Conexión al servicio de autenticación de Odoo
    common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
    uid = common.authenticate(database, user, password, {})
    # Conexión al servicio de objetos de Odoo para realizar operaciones en los modelos
    models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')
    # Busca el ID del empleado basado en el 'name' (nombre) proporcionado
    employee_id = models.execute_kw(database, uid, password,
                                    'hr.employee', 'search',
                                    [[('name', '=', name)]])
    if not employee_id:
        print(f"No se encontró el empleado con nombre {name} para marcar como sincronizado.")
        return
    # Marca el registro como sincronizado
    response = models.execute_kw(database, uid, password,
        'hr.employee', 'write',
        [employee_id, {'x_studio_pendiente_sincronizacion': 'No'}],
        {'context': {'skip_sync': True}})
    if response:
        print(f"Empleado {name} marcado como sincronizado con éxito.")
    else:
        print("Error al actualizar el registro.")
def sincronizar_con_sharepoint(registros, access_token):
    """Esta función cumple con controlar y ejecutar el metodo eliminar y crear."""
    for registro in registros:
        identification_id = registro['identification_id'] if registro['identification_id'] else None
        name = registro['name'] if registro['name'] else None
        _, company_id = registro['company_id'] if registro['company_id'] else None
        job_title = registro['job_title'] if registro['job_title'] else None
        x_studio_correo_electrnico_personal = registro['x_studio_correo_electrnico_personal'] if registro['x_studio_correo_electrnico_personal'] else None
        work_email =  registro['work_email'] if registro['work_email'] else None
        birthday = registro['birthday']
        x_studio_estado_empleado = registro['x_studio_estado_empleado'] if registro['x_studio_estado_empleado']  else None
        birthday2 = f"{birthday}T00:00:00Z" if birthday else None
        item_id, etag = verificar_si_existe(name, access_token)
        # Lógica para manejar el estado del registro
        if x_studio_estado_empleado == "Activo" and item_id:
            eliminado_exitosamente = eliminar_registro(item_id, etag, access_token, site_id, list_name)
            crear_registro_en_sharepoint(name, identification_id, company_id, job_title,
                                        x_studio_correo_electrnico_personal, work_email,
                                        birthday2, x_studio_estado_empleado, access_token,
                                        site_id, list_name)
            marcar_registro_como_sincronizado(name)
        elif x_studio_estado_empleado == "Activo":
            crear_registro_en_sharepoint(name, identification_id, company_id, job_title,
                                        x_studio_correo_electrnico_personal, work_email,
                                        birthday2, x_studio_estado_empleado, access_token,
                                        site_id, list_name)
            marcar_registro_como_sincronizado(name)
        elif x_studio_estado_empleado == "Retirado" and item_id:
            eliminado_exitosamente = eliminar_registro(item_id, etag, access_token, site_id, list_name)
            if eliminado_exitosamente:
                marcar_registro_como_sincronizado(name)
def eliminar_registro(item_id, etag, access_token, site_id, list_name):
    """Esta función elimina los registros de sharepoint por ID."""
    delete_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{item_id}"
    delete_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "If-Match": etag  # Necesario para la eliminación
    }
    delete_response = requests.delete(delete_url, headers=delete_headers, timeout=10)
    delete_response.raise_for_status()# Esto lanzará una excepción si la solicitud falla
    print(f"Registro eliminado con éxito: {item_id}")
def crear_registro_en_sharepoint(name, identification_id, company_id,
                                job_title, x_studio_correo_electrnico_personal,
                                work_email, birthday2, x_studio_estado_empleado,
                                access_token, site_id, list_name):
    """Esta función crea los registros de sharepoint."""
    create_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items"
    create_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "fields": {
            "Title": x_studio_estado_empleado,
            "field_2": name,
            "field_1": identification_id,
            "field_3": job_title,
            "field_4": x_studio_correo_electrnico_personal,
            "field_5": work_email,
            "field_6": birthday2,
            "field_7": company_id
        }
    }
    create_response = requests.post(create_url, headers=create_headers, json=payload, timeout=10)
    print("Estado del envio", create_response.status_code)
    if create_response.status_code in [200, 201]:
        print(f"Sincronizado con éxito: {name}")
    elif create_response.status_code == 500:
        enviar_solicitud_con_reintento(create_url, create_headers, payload)
        if create_response.status_code in [200, 201]:
            print(f"Sincronizado con éxito después del reintento: {name}")
        else:
            print(f"Error al sincronizar después del reintento: {name}")
def enviar_solicitud_con_reintento(url, headers, payload, max_reintentos=5):
    """Esta función reintenta los registros que fallan."""
    espera = 2
    for reintento in range(max_reintentos):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                print(f"Error 500 detectado, reintento {reintento + 1} de {max_reintentos}. Esperando {espera} segundos.")
                time.sleep(espera)
                espera *= 2# Aumenta el tiempo de espera para el próximo intento
            else:
                print(f"Error {e.response.status_code}: {e.response.text}")
                raise
    raise Exception("Se alcanzó el máximo número de reintentos sin éxito para crear el registro en SharePoint.")
def clear_sharepoint_list(access_token, site_id, list_name):
    """Esta función elimina todos los registros de sharepoint."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    get_url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items'
    response = requests.get(get_url, headers=headers, timeout=10)
    if response.status_code == 200:
        items = response.json().get('value', [])
        if not items:
            print("La lista ya está vacía.")
        batch_size = 20
        for i in range(0, len(items), batch_size):
            batch = {"requests": []}
            for item in items[i:i+batch_size]:
                batch["requests"].append({
                    "id": str(item["id"]),
                    "method": "DELETE",
                    "url": f"/sites/{site_id}/lists/{list_name}/items/{item['id']}"
                })
            batch_url = "https://graph.microsoft.com/v1.0/$batch"
            batch_response = requests.post(batch_url, headers=headers, json=batch, timeout=10)
            if batch_response.status_code == 200:
                print(f"Elementos del lote {i//batch_size + 1} eliminados exitosamente.")
            else:
                print(f"Error al eliminar elementos del lote {i//batch_size + 1}: {batch_response.text}")
    else:
        print("Error al obtener elementos de la lista:", response.text)
