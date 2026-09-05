import database
from config import PRECIO_VALORACION, LINK_PAGO_VALORACION
from services.calendar_service import obtener_dias_disponibles, obtener_horas_disponibles

def procesar_mensaje_usuario(telefono, mensaje):
    mensaje_limpio = mensaje.strip().lower()
    
    estado, datos_temp = database.obtener_estado_usuario(telefono)

    # REINICIAR FLUJOS
    if mensaje_limpio in ['cancelar', 'inicio', 'menu', 'reiniciar', '0']:
        database.guardar_estado_usuario(telefono, 'INICIO', {})
        return (
            "🔄 *Proceso cancelado.*\n\n"
            "Bienvenido al sistema de citas. Escribe *agendar* para iniciar."
        )

    if estado == 'INICIO':
        if mensaje_limpio in ['2', 'consultar', 'consultar cita', 'ver cita']:
            cita = database.obtener_cita_activa(telefono)
            if cita:
                texto_meet = f"\n💻 *Enlace a Google Meet:*\n{cita['meet_link']}\n" if cita.get('meet_link') else ""
                return (
                    f"📌 *Tu cita agendada:*\n\n"
                    f"👤 *Paciente:* {cita['paciente']}\n"
                    f"📅 *Fecha:* {cita['fecha_str']}\n"
                    f"⏰ *Hora:* {cita['hora_str']}\n"
                    f"{texto_meet}\n"
                    f"¡Te esperamos!"
                )
            else:
                return "❌ No encontramos ninguna cita activa registrada para este número."

        elif mensaje_limpio in ['3', 'eliminar cita', 'cancelar cita']:
            event_id = database.eliminar_cita_por_telefono(telefono)
            if event_id:
                return "✅ Tu cita ha sido eliminada del sistema."
            else:
                return "❌ No tienes ninguna cita registrada para cancelar."

    elif estado == 'ESPERANDO_NOMBRE':
        nombre_usuario = mensaje.strip().title()
        
        data_cita = {
            'telefono': telefono,
            'paciente': nombre_usuario,
            'tipo_cita': datos_temp.get('tipo_cita', 'Valoración Inicial'),
            'modalidad': datos_temp.get('modalidad', 'VIRTUAL'),
            'fecha_iso': datos_temp.get('fecha_iso', ''),
            'fecha_str': datos_temp.get('fecha_str', ''),
            'hora_iso': datos_temp.get('hora_iso', ''),
            'hora_str': datos_temp.get('hora_str', ''),
            'estado': 'PENDIENTE_PAGO',
            'plan_nombre': datos_temp.get('plan_nombre'),
            'citas_restantes': datos_temp.get('citas_restantes', 1),
            'event_id': None,
            'meet_link': None
        }

        # Pasamos el diccionario data que exige database.py
        database.guardar_cita_pendiente(data_cita)
        database.guardar_estado_usuario(telefono, 'INICIO', {})

        return (
            f"✅ *Pre-reserva registrada con éxito.*\n\n"
            f"👤 *Paciente:* {nombre_usuario}\n"
            f"📅 *Fecha:* {datos_temp.get('fecha_str')}\n"
            f"⏰ *Hora:* {datos_temp.get('hora_str')}\n\n"
            f"💳 *Enlace de pago:*\n{LINK_PAGO_VALORACION}"
        )

    return None