from . import views
from django.urls import path

urlpatterns = [
    # Rutas WEB
    # La vista web del listado
    path('gestion/', views.gestion_hojas_de_ruta, name='gestion_hojas'),

    # La vista para crear la hoja de ruta
    path('crear/', views.crear_hoja, name='crear_hoja'),

    # La pantalla del Paso 2 (Dibuja las dos listas)
    path('<int:hoja_id>/asignar-pedidos/', views.asignar_pedidos, name='asignar_pedidos'),
    
    # El endpoint invisible para que el JavaScript mueva los pedidos en vivo
    path('<int:hoja_id>/mover-pedido/<int:pedido_id>/', views.mover_pedido, name='mover_pedido'),


    # Rutas API REST
    # Ej de uso: GET /hojas/api/ruta-hoy/5/ (donde 5 es el ID del transportista)
    path('api/ruta-hoy/<int:transportista_id>/', views.consultar_hoja_hoy, name='api_ruta_hoy'),


    
]
