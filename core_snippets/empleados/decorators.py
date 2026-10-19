from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import Administrativo

# 1. GUARDIA ESTÁNDAR: Solo verifica que la sesión exista
def admin_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            return redirect('login_web')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

# 2. GUARDIA EJECUTIVO: Verifica sesión y además busca el rol en la Base de Datos
def ejecutivo_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Primero chequeamos que al menos haya iniciado sesión
        if 'admin_id' not in request.session:
            messages.error(request, "Debes iniciar sesión.")
            return redirect('login_web')
        
        # Si tiene sesión, buscamos su registro en la base de datos
        admin_id = request.session['admin_id']
        try:
            admin_actual = Administrativo.objects.get(id=admin_id)
            
            # Revisamos su nivel de acceso (el campo booleano)
            if not admin_actual.ejecutivo:
                return redirect('home') # Asegurate de que 'home' sea el alias de tu panel principal
                
        except Administrativo.DoesNotExist:
            # Si el usuario fue borrado de la BD mientras tenía la sesión abierta, lo deslogueamos
            request.session.flush()
            return redirect('login_web')
        
        # Si pasó todos los filtros, le abrimos la puerta
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
