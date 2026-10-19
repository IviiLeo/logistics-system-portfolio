from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Transportista, Administrativo
from django.contrib.auth.hashers import check_password # La herramienta para comparar claves encriptadas
from .decorators import admin_requerido, ejecutivo_requerido

# Herramientas API REST
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import *

# =========================================================
# --- VISTAS WEB (Devuelven HTML para el navegador) ---
# =========================================================

# Devuelve al Front WEB una lista con la información de todos los transportistas
def lista_transportistas_web(request): 

    # 1. Vamos a la base de datos y traemos todos los registros
    transportistas_db = Transportista.objects.all()
    
    # 2. Armamos el "contexto" (un diccionario con los datos que le mandamos al HTML)
    contexto = {
        'lista_de_transportistas': transportistas_db
    }
    
    # 3. Renderizamos la página combinando el HTML con nuestros datos
    return render(request, 'empleados/lista_transportistas.html', contexto)


def iniciar_sesion_web(request):
    # PASO 1: Control de barrera. 
    # Si el navegador ya tiene nuestra cookie admin_id, lo mandamos directo al panel.
    if 'admin_id' in request.session:
        return redirect('home') # Reemplazá 'home' por el nombre de la URL de tu panel principal

    # PASO 2: Procesamiento de datos (Cuando el Front-End hace el POST)
    if request.method == 'POST':
        # Capturamos lo que el usuario escribió en el HTML
        correo_ingresado = request.POST.get('mail') 
        clave_ingresada = request.POST.get('clave')

        try:
            # 2.A: Vamos a TU base de datos y buscamos si existe un Administrativo con ese mail
            admin = Administrativo.objects.get(mail=correo_ingresado)

            # 2.B: Si el mail existe, agarramos la clave que escribió recién, y usamos
            # check_password para que la compare matemáticamente con el hash que guardaste en SQLite
            if check_password(clave_ingresada, admin.contraseña):
                
                # 2.C: Regla de negocio -> Verificamos el booleano de estado
                if admin.estado: 
                    # ¡ÉXITO! Creamos la sesión manualmente guardando el ID del administrativo
                    request.session['admin_id'] = admin.id
                    return redirect('home')
                else:
                    messages.error(request, "Esta cuenta administrativa está desactivada.")
            else:
                # La matemática del hash no coincidió
                messages.error(request, "Contraseña incorrecta.")
                
        except Administrativo.DoesNotExist:
            # El ORM no encontró ningún registro con ese mail en SQLite
            messages.error(request, "El correo ingresado no pertenece a ningún administrador.")

    # PASO 3: Si entra por primera vez (Método GET), le mostramos el formulario HTML vacío
    return render(request, 'empleados/login.html')


def cerrar_sesion_web(request):
    # Para cerrar sesión, simplemente destruimos nuestra variable manual en la memoria del servidor
    if 'admin_id' in request.session:
        del request.session['admin_id']
    
    # Destruimos la sesión completa por seguridad y lo mandamos a la pantalla de login
    request.session.flush()
    return redirect('login_web')






# =========================================================
# VISTAS API (Devuelven JSON para la app móvil en Expo)
# =========================================================

@api_view(['GET'])
def lista_transportistas_api(request):
    
    # 1. Buscamos la información cruda en la base de datos (Igual que en la web)
    transportistas_db = Transportista.objects.all()
    
    # 2. ¡Acá entra a trabajar el traductor! 
    # Le pasamos los registros crudos y le aclaramos many=True porque es una lista de varios.
    traductor = TransportistaParcialSerializer(transportistas_db, many=True)
    
    # 3. Devolvemos la respuesta empaquetada en el formato universal JSON
    return Response(traductor.data)

@api_view(['POST'])
def iniciar_sesion_movil(request):
    # 1. Ahora el celular manda DNI y PIN
    dni = request.data.get('dni')
    pin = request.data.get('pin')
    
    # 2. Validación de campos vacíos
    if not dni or not pin:
        return Response({'error': 'Por favor, ingresa tu DNI y PIN.'}, status=400)
        
    try:
        # 3. Buscamos al TRANSPORTISTA en SQLite por su DNI
        transportista = Transportista.objects.get(dni=dni)
    
        # 4. Comparamos el PIN. 
        if check_password(pin, transportista.pin):
            
            # 5. Validamos que el chofer no esté suspendido o dado de baja
            if not transportista.estado:
                return Response({'error': 'Tu cuenta se encuentra inactiva.'}, status=403)
                
            # ÉXITO: Le mandamos los datos al celular
            return Response({
                'exito': True,
                'mensaje': 'Inicio de sesión correcto',
                'usuario': {
                    'id': transportista.id,
                    'dni': transportista.dni,
                    'nombre': transportista.nombre,
                    'apellido': transportista.apellido,
                    'cbu': transportista.cbu,
                    'alias': transportista.alias
                }
            })
            
        else:
            return Response({'error': 'DNI o PIN incorrectos.'}, status=401)
            
    except Transportista.DoesNotExist:
        return Response({'error': 'DNI o PIN incorrectos.'}, status=401)
