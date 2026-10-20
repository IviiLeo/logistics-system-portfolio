from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import date, datetime
from .models import HojaDeRuta
from .serializers import HojaDeRutaSerializer
from django.shortcuts import get_object_or_404, render, redirect
from empleados.decorators import sesion_requerida
from django.core.paginator import Paginator
from django.contrib import messages
from empleados.models import Transportista
from django.db import transaction
from pedidos.models import Pedido

# =========================================================
# --- VISTAS WEB (Devuelven HTML para el navegador) ---
# =========================================================

@sesion_requerida
def gestion_hojas_de_ruta(request):
    # 1. Leemos qué botón apretó el usuario en la URL (ej: /hojas/gestion/?filtro=pasadas)
    # Si no mandó nada, por defecto mostramos las de 'hoy'
    filtro_seleccionado = request.GET.get('filtro', 'hoy')
    hoy = date.today()

    # 2. Vamos a la base de datos y filtramos según el botón elegido.
    # Usamos select_related para el chofer y prefetch_related para los pedidos.
    consulta_base = HojaDeRuta.objects.all().select_related('transportista').prefetch_related('pedidos')

    if filtro_seleccionado == 'pasadas':
        hojas_db = consulta_base.filter(fecha__lt=hoy).order_by('-fecha')
    elif filtro_seleccionado == 'futuras':
        hojas_db = consulta_base.filter(fecha__gt=hoy).order_by('fecha')
    else: 
        # Cae acá si el filtro es 'hoy'
        hojas_db = consulta_base.filter(fecha=hoy)

    # 3. Dividimos la lista resultante en páginas de 30 hojas cada una
    paginador = Paginator(hojas_db, 30)

    # 4. Leemos qué número de página pidió el usuario en la URL (ej: /hojas/gestion/?pagina=2)
    numero_pagina = request.GET.get('pagina')
    pagina_de_hojas = paginador.get_page(numero_pagina)

    # 5. Armamos el "contexto" enviando las 30 hojas y el filtro para pintar el botón
    contexto = {
        'lista_de_hojas': pagina_de_hojas,
        'filtro_actual': filtro_seleccionado
    }

    # 6. Renderizamos la página combinando el HTML con nuestros datos paginados
    return render(request, 'hojas/gestion_hojas.html', contexto)



@sesion_requerida
def crear_hoja(request):
    """
    Vista web (Paso 1): Pantalla para elegir fecha y transportista.
    """
    # --- SI EL ADMIN APRETÓ "CONFIRMAR" (POST) ---
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        transportista_id = request.POST.get('transportista')
        
        # 1. Validamos que no vengan campos vacíos
        if not fecha_str:
            messages.error(request, 'Debe seleccionar una fecha.')
            return redirect('hojas:crear_hoja')
            
        if not transportista_id:
            messages.error(request, 'Debe seleccionar un transportista obligatoriamente.')
            return redirect('hojas:crear_hoja')
            
        # 2. Traducimos el texto a una fecha real de Python
        fecha_ingresada = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        # 3. Validación de la regla de negocio: Debe ser POSTERIOR a hoy
        if fecha_ingresada <= date.today():
            messages.error(request, 'Error: La fecha de la hoja debe ser posterior al día de hoy.')
            return redirect('hojas:crear_hoja')
            
        # 4. Creamos la hoja de ruta en la base de datos
        nueva_hoja = HojaDeRuta.objects.create(
            fecha=fecha_ingresada,
            transportista_id=transportista_id # Ya sabemos que viene sí o sí
        )

        messages.success(request, f'Hoja de ruta #{nueva_hoja.id} creada correctamente. Ahora asigne los pedidos.')
        
        # Redirigimos al PASO 2 pasándole el ID de la hoja que acabamos de crear
        return redirect('hojas:asignar_pedidos', hoja_id=nueva_hoja.id)


    # --- SI EL ADMIN RECIÉN ENTRÓ O ESTÁ BUSCANDO (GET) ---
    
    buscar_dni = request.GET.get('dni', '')
    fecha_filtro_str = request.GET.get('fecha_calendario')
    
    transportistas_disponibles = None
    
    # Solo buscamos transportistas si el administrador ya seleccionó una fecha
    if fecha_filtro_str:
        fecha_filtro = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
        
        transportistas_db = Transportista.objects.all()
        
        if buscar_dni:
            transportistas_db = transportistas_db.filter(dni__icontains=buscar_dni)
            
        # Excluimos a los que ya tienen viaje ese día y traemos la lista completa sin paginar
        transportistas_disponibles = transportistas_db.exclude(
            hojas_asignadas__fecha=fecha_filtro
        ).order_by('nombre')

    # Si transportistas_disponibles es None, el equipo de Front puede usar un 
    # {% if lista_de_transportistas is None %} en su HTML para mostrar el cartel:
    # "Seleccione una fecha para ver los transportistas disponibles."
    contexto = {
        'lista_de_transportistas': transportistas_disponibles,
        'busqueda_dni': buscar_dni,
        'fecha_seleccionada': fecha_filtro_str if fecha_filtro_str else ''
    }

    return render(request, 'hojas/crear_hoja.html', contexto)


@sesion_requerida
def asignar_pedidos(request, hoja_id):
    """
    Vista web (Paso 2): Dibuja la pantalla con las dos listas completas.
    """
    hoja_actual = get_object_or_404(HojaDeRuta, id=hoja_id)

    # --- LISTA IZQUIERDA: Todos los Pedidos Disponibles del día ---
    pedidos_disponibles = Pedido.objects.filter(
        fecha_entrega=hoja_actual.fecha,
        hoja_de_ruta__isnull=True,
        estado='pendiente'
    )

    # --- LISTA DERECHA: Todos los Pedidos Ya Asignados a esta hoja ---
    pedidos_asignados = hoja_actual.pedidos.all()
    
    # 2. Empaquetamos todo y lo mandamos al Front
    contexto = {
        'hoja': hoja_actual,
        'disponibles': pedidos_disponibles,
        'asignados': pedidos_asignados,
    }

    return render(request, 'hojas/asignar_pedidos.html', contexto)


@sesion_requerida
def mover_pedido(request, hoja_id, pedido_id):
    """
    Función de acción rápida (AJAX/Fetch).
    Alterna el pedido entre la hoja actual y el depósito (estado pendiente).
    Devuelve un JSON para que el Front-End actualice la vista sin recargar.
    """
    # 1. Aseguramos que la petición sea POST por seguridad
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    # 2. Buscamos los objetos (si no existen, get_object_or_404 devuelve error 404)
    hoja_actual = get_object_or_404(HojaDeRuta, id=hoja_id)
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # 3. Lógica de palanca (Toggle): 
    accion_realizada = "" # Variable para avisarle al front qué hicimos
    
    if pedido.hoja_de_ruta == hoja_actual:
        # Si ya estaba asignado a esta hoja (Lista Derecha) -> Lo sacamos
        pedido.hoja_de_ruta = None
        pedido.estado = 'pendiente'
        accion_realizada = "desasignado"
        
    elif pedido.hoja_de_ruta is None and pedido.estado == 'pendiente':
        # Si estaba libre en el depósito (Lista Izquierda) -> Lo asignamos
        pedido.hoja_de_ruta = hoja_actual
        pedido.estado = 'asignado'
        accion_realizada = "asignado"
        
    else:
        # Si el pedido está asignado a OTRA hoja distinta o ya fue entregado,
        # frenamos la operación para evitar inconsistencias.
        return JsonResponse({'error': 'El pedido no está disponible para esta acción'}, status=400)

    # 4. Guardamos el cambio en la base de datos
    pedido.save()

    # 5. Respondemos con un JSON confirmando el éxito y qué acción se hizo
    return JsonResponse({
        'status': 'ok',
        'accion': accion_realizada,
        'pedido_id': pedido.id
    })




# =========================================================
# VISTAS API (Devuelven JSON para la app móvil en Expo)
# =========================================================

@api_view(['GET'])
def consultar_hoja_hoy(request, transportista_id):
    """
    Endpoint para la App Móvil:
    Devuelve la hoja de ruta del día actual para un transportista específico,
    incluyendo la lista de todos sus pedidos.
    """
    try:
        # Buscamos la hoja de ruta de HOY para el chofer que lo solicita
        hoja = HojaDeRuta.objects.get(
            transportista_id=transportista_id, 
            fecha=date.today()
        )
        
        # Traducimos el objeto de Python a JSON
        serializer = HojaDeRutaSerializer(hoja)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except HojaDeRuta.DoesNotExist:
        # Si el chofer abre la app y no tiene viajes hoy, le avisamos
        return Response(
            {"mensaje": "No tenés una hoja de ruta asignada para hoy."}, 
            status=status.HTTP_404_NOT_FOUND
        )
