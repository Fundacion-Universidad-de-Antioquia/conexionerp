import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CtrlCapacitacionesForm, RegistrationForm
from .models import CtrlCapacitaciones
from django.http import HttpResponseRedirect
from django.urls import reverse
from io import BytesIO
import xmlrpc.client
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import base64
from urllib.parse import quote
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
database = os.getenv("DATABASE")
user = os.getenv("ODOO_USER")
password = os.getenv("PASSWORD")
host = os.getenv("HOST")
apphost = os.getenv('APP_HOST')

# Función para obtener el ID del departamento
def get_department_id(department_name):
    try:
        common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
        uid = common.authenticate(database, user, password, {})
        models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')

        department = models.execute_kw(database, uid, password,
            'hr.department', 'search_read',
            [[['name', '=', department_name]]],
            {'fields': ['id'], 'limit': 1})
        
        if department:
            return department[0]['id']
        else:
            return None
    
    except Exception as e:
        logger.error('Failed to fetch department ID from Odoo', exc_info=True)
        return None

# Función para obtener el ID del empleado por Nombre
def get_employee_id_by_name(employee_name):
    try:
        common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
        uid = common.authenticate(database, user, password, {})
        models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')

        employees = models.execute_kw(database, uid, password,
            'hr.employee', 'search_read',
            [[['name', '=', employee_name]]],
            {'fields': ['id', 'name'], 'limit': 1})
        
        if employees:
            print(f"Employee found: {employees[0]}")
            return employees[0]['id']
        else:
            print(f"No employee found with name: {employee_name}")
            return None
    
    except Exception as e:
        logger.error('Failed to fetch employee ID from Odoo', exc_info=True)
        return None


# Función para enviar datos a Odoo
def send_to_odoo(data):
    logger.debug(f"Intentando enviar datos a Odoo: {data}")
    try:
        common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
        uid = common.authenticate(database, user, password, {})
        models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')

        department_id = get_department_id(data['department'])
        if not department_id:
            raise ValueError(f"Department '{data['department']}' not found in Odoo")

        employee_data = models.execute_kw(database, uid, password,
                                          'hr.employee', 'search_read',
                                          [[['name', '=', data['document_id']]]],
                                          {'fields': ['id', 'name'], 'limit': 1})

        if not employee_data:
            raise ValueError(f"Employee with name '{data['document_id']}' not found in Odoo")

        employee_id = employee_data[0]['id']

        # Convertir fechas a cadenas
        date_str = data['date'].strftime('%Y-%m-%d')
        start_time_str = data['start_time'].strftime('%H:%M:%S')
        end_time_str = data['end_time'].strftime('%H:%M:%S')
        # Preparar los datos para el registro en Odoo
        odoo_data = {
            'x_studio_tema': data['topic'],
            'x_studio_many2one_field_iphhw': employee_id,
            'x_studio_fecha_sesin': date_str,
            'x_studio_hora_inicial': start_time_str,
            'x_studio_hora_final': end_time_str,
            'x_studio_many2one_field_ftouu': department_id,
            'x_studio_estado': 'ACTIVA',
            'x_studio_modalidad': data.get('mode', ''),  # Usar .get() para evitar KeyError
            'x_studio_ubicacin': data.get('location', ''),  # Usar .get() para evitar KeyError
            'x_studio_url': data.get('url_reunion', ''),  # Usar .get() para evitar KeyError
            'x_studio_asisti': 'Si',
            'x_studio_fecha_y_hora_de_registro': data.get('registro_datetime'),  # Campo nuevo para la fecha/hora
            'x_studio_ip_del_registro': data.get('ip_address'),  # Campo nuevo para la IP
            'x_studio_user_agent': data.get('user_agent') #Campo nuevo para el user-agent
        }

        record_id = models.execute_kw(database, uid, password,
                                      'x_capacitacion_emplead', 'create', [odoo_data])

        # Obtener el nombre del empleado desde el campo `identification_id`
        employee_name = models.execute_kw(database, uid, password,
                                          'hr.employee', 'search_read',
                                          [[['id', '=', employee_id]]],
                                          {'fields': ['identification_id'], 'limit': 1})[0]['identification_id']

        logger.debug(f'Record created in Odoo with ID: {record_id}, employee_name: {employee_name}')
        return record_id, employee_name, data.get('url_reunion', '')

    except Exception as e:
        logger.error('Failed to send data to Odoo', exc_info=True)
        return None, None, None



# Función para crear QR de Capacitación
def create_capacitacion(request):
    if request.method == 'POST':
        form = CtrlCapacitacionesForm(request.POST)
        if form.is_valid():
            capacitacion = form.save()
            capacitacion = form.save(commit=False)
            
            qr_url = f"{apphost}/learn/register/?id={capacitacion.id}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            capacitacion.qr_base64 = img_base64
            capacitacion.save()

            return HttpResponseRedirect(reverse('details_view', args=[capacitacion.id]))
    else:
        form = CtrlCapacitacionesForm()
    return render(request, 'crear_capacitacion.html', {'form': form})

# Función para mostrar lista de Capacitaciones
def list_capacitaciones(request):
    capacitaciones = CtrlCapacitaciones.objects.all()
    return render(request, 'list_capacitaciones.html', {'capacitaciones': capacitaciones})


# Función para registrar asistencia y actualizar registro en Odoo
def registration_view(request):
    capacitacion_id = request.GET.get('id')
    capacitacion = get_object_or_404(CtrlCapacitaciones, id=capacitacion_id)

    # Formatea la fecha correctamente
    date_str = capacitacion.fecha.strftime('%Y-%m-%d')

    initial_data = {
        'topic': capacitacion.tema,
        'objective': capacitacion.objetivo,
        'department': capacitacion.area_encargada,
        'moderator': capacitacion.moderador,
        'date': date_str,
        'start_time': capacitacion.hora_inicial,
        'end_time': capacitacion.hora_final,
        'mode': capacitacion.modalidad,
        'location': capacitacion.ubicacion,
        'url_reunion': capacitacion.url_reunion,
        'document_id': ''  # Este campo se llenará por el usuario
    }

    form = RegistrationForm(request.POST or None, initial=initial_data)
    is_active = capacitacion.estado == 'ACTIVA'

    error_message = None  # Inicializa la variable error_message

    if request.method == 'POST' and is_active:
        if form.is_valid():
            logger.debug("El formulario es válido")
            document_id = form.cleaned_data['document_id']

            try:
                # Verifica si el documento existe en Odoo
                employee_id = get_employee_id_by_name(document_id)
                
                if not employee_id:
                    error_message = f"No se encontró un empleado con el documento {document_id}. Por favor, verifique los datos."
                else:
                    common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
                    uid = common.authenticate(database, user, password, {})
                    models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')

                    # Buscar registros en Odoo para evitar duplicados
                    existing_records = models.execute_kw(database, uid, password,
                        'x_capacitacion_emplead', 'search_read',
                        [[
                            ['x_studio_tema', '=', capacitacion.tema],
                            ['x_studio_fecha_sesin', '=', capacitacion.fecha.strftime('%Y-%m-%d')],
                            ['x_studio_many2one_field_iphhw', '=', employee_id]
                        ]],
                        {'fields': ['id']})

                    if existing_records:
                        error_message = f"El usuario con documento {document_id} ya está registrado en esta capacitación."
                    else:
                        #Obtener fecha y hora actual
                        registro_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        user_agent = request.META.get('HTTP_USER_AGENT', '')
                        
                        # Obtener la dirección IP del cliente
                        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
                        if ip_address:
                            ip_address = ip_address.split(',')[0]
                        else:
                            ip_address = request.META.get('REMOTE_ADDR')
                            
                        url_reunion = form.cleaned_data.get('url_reunion', '')
                        
                        if not url_reunion or url_reunion.lower() == 'none':
                            url_reunion = 'without-url'  # Establece un valor por defecto
                            
                        # Si no existe duplicado, procede a crear el registro en Odoo
                        data = form.cleaned_data
                        data['registro_datetime'] = registro_datetime
                        data['ip_address'] = ip_address
                        data['user_agent'] = user_agent
                        record_id, employee_name, url_reunion = send_to_odoo(data)
                        if record_id:
                            # Redirigir a la vista de éxito con el nombre del empleado
                            encoded_url = quote(url_reunion, safe='')
                            return redirect(reverse('success', kwargs={'employee_name': employee_name, 'url_reunion': encoded_url}))
                        else:
                            error_message = "Hubo un problema al enviar los datos a Odoo. Por favor, intente nuevamente."

            except Exception as e:
                logger.error('Failed to verify or register assistant in Odoo', exc_info=True)
                error_message = "Hubo un problema al verificar los datos en el sistema. Por favor, intente nuevamente."
        
        else:
            logger.debug("El formulario no es válido")
            logger.debug(form.errors)

    context = {
        'form': form,
        'is_active': is_active,
        'capacitacion': capacitacion,
        'error_message': error_message  # Incluye error_message en el contexto
    }

    return render(request, 'registration_form.html', context)


# Vista de Éxito Al Enviar Datos
def success_view(request, employee_name, url_reunion=None):
    print(f"Valor de url_reunion antes de la validación: {url_reunion}")
    decoded_url = unquote(url_reunion) if url_reunion and url_reunion != 'without-url' else None
    context = {
        'employee_name': employee_name,
        'url_reunion': decoded_url  # Usa la URL decodificada o None si no se proporciona
    }
    return render(request, 'success.html', context)

#Vista Detalles de la Capacitación
def details_view(request, id):
    capacitacion = get_object_or_404(CtrlCapacitaciones, id=id)
    
     # Determinar si mostrar ubicación y/o URL de la reunión según la modalidad
    show_url = capacitacion.modalidad == 'VIRTUAL' or capacitacion.modalidad == 'MIXTA'
    show_ubicacion = capacitacion.modalidad == 'PRESENCIAL' or capacitacion.modalidad == 'MIXTA'
    
    context = {
        'topic': capacitacion.tema,
        'department': capacitacion.area_encargada,
        'objective': capacitacion.objetivo,
        'moderator': capacitacion.moderador,
        'date': capacitacion.fecha.strftime('%Y-%m-%d'),
        'start_time': capacitacion.hora_inicial.strftime('%H:%M'),
        'end_time': capacitacion.hora_final.strftime('%H:%M'),
        'modalidad': capacitacion.modalidad, 
        'ubicacion': capacitacion.ubicacion if show_ubicacion else None,  # Condicionalmente según la modalidad
        'url_reunion': capacitacion.url_reunion if show_url else None,  # Condicionalmente según la modalidad
        'qr_url': f"{apphost}/learn/register/?id={capacitacion.id}",
        'qr_base64': capacitacion.qr_base64
    }
    
    return render(request, 'details_view.html', context)

# Vista Home que muestra todas las capacitaciones
def home(request):
    capacitaciones = CtrlCapacitaciones.objects.all()
    for capacitacion in capacitaciones:
        capacitacion.fecha_formateada = capacitacion.fecha.strftime('%Y-%m-%d')
        
    return render(request, 'home.html', {'capacitaciones': capacitaciones})

# Vista para editar una capacitación existente
def edit_capacitacion(request, id):
    capacitacion = get_object_or_404(CtrlCapacitaciones, id=id)
    if request.method == 'POST':
        form = CtrlCapacitacionesForm(request.POST, instance=capacitacion)
        if form.is_valid():
            capacitacion = form.save(commit=False)
            form.save()
            return redirect('home')
    else:
        form = CtrlCapacitacionesForm(instance=capacitacion)
    return render(request, 'crear_capacitacion.html', {'form': form})

# Vista para ver los usuarios que asistieron a una capacitación
def view_assistants(request, id):
    capacitacion = get_object_or_404(CtrlCapacitaciones, id=id)
    try:
        common = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/common')
        uid = common.authenticate(database, user, password, {})
        models = xmlrpc.client.ServerProxy(f'{host}/xmlrpc/2/object')

        assistants = models.execute_kw(database, uid, password,
            'x_capacitacion_emplead', 'search_read',
            [[
                ['x_studio_tema', '=', capacitacion.tema],
                ['x_studio_fecha_sesin', '=', capacitacion.fecha.strftime('%Y-%m-%d')],
                ['x_studio_hora_inicial', '=', capacitacion.hora_inicial.strftime('%H:%M:%S')]
            ]],
            {'fields': ['x_studio_many2one_field_iphhw', 'x_studio_cargo', 'x_studio_nombre_empleado', 'x_studio_departamento_empleado']})

        assistant_data = []
        for assistant in assistants:
            userId = assistant['x_studio_many2one_field_iphhw'][1] if assistant['x_studio_many2one_field_iphhw'] else ''
            jobTitle = assistant.get('x_studio_cargo', '')
            username = assistant.get('x_studio_nombre_empleado','')
            employeeDepartment = assistant.get('x_studio_departamento_empleado','')
            
            assistant_data.append({'userId': userId, 'jobTitle': jobTitle, 'username':username, 'employeeDepartment': employeeDepartment})

    except Exception as e:
        logger.error('Failed to fetch assistants from Odoo', exc_info=True)
        assistant_data = []

    return render(request, 'view_assistants.html', {
        'capacitacion': capacitacion,
        'assistants': assistant_data
    })