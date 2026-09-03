from calendar_service import obtener_dias_disponibles, obtener_horas_disponibles, agendar_cita
from database import obtener_usuario, guardar_estado_usuario
from config import PRECIO_PRIMERA_CITA, PRECIO_SEGUIMIENTO, LINK_DE_PAGO
import database

def procesar_mensaje_usuario(telefono, mensaje):
    mensaje_limpio = mensaje.strip().lower()
    
    user = obtener_usuario(telefono)
    if not user:
        guardar_estado_usuario(telefono, 'INICIO')
        user = obtener_usuario(telefono)
        
    estado = user['estado']
    datos_temp = user['datos_temp']

    # --- REINICIAR FLUJOS ---
    if mensaje_limpio in ['cancelar', 'inicio', 'menu', 'reiniciar', '0']:
        guardar_estado_usuario(telefono, 'INICIO', {})
        return (
            "🔄 *Proceso cancelado.*\n\n"
            "Bienvenido al sistema de citas. Por favor selecciona una opción:\n"
            "*1.* Agendar cita\n"
            "*2.* Consultar cita\n"
            "*3.* Cancelar cita"
        )

    # --- ESTADO 1: MENÚ PRINCIPAL ---
    if estado == 'INICIO':
        if mensaje_limpio in ['1', 'agendar', 'agendar cita']:
            guardar_estado_usuario(telefono, 'SELECCIONANDO_TIPO', {})
            return (
                "📌 *Por favor selecciona el tipo de consulta:*\n\n"
                f"*1.* Primera Cita (${PRECIO_PRIMERA_CITA:,} COP)\n"
                f"*2.* Cita de Control / Seguimiento (${PRECIO_SEGUIMIENTO:,} COP)\n\n"
                "_Escribe *0* para cancelar._"
            )
        else:
            # Si no es la opción de agendar (1), devolvemos None para que main.py
            # se encargue de procesar los comandos 'consultar', 'cancelar' o saludos.
            return None

    # --- ESTADO 2: SELECCIÓN TIPO DE CITA ---
    elif estado == 'SELECCIONANDO_TIPO':
        if mensaje_limpio in ['1', '2']:
            tipo = "Primera Cita" if mensaje_limpio == '1' else "Cita de Seguimiento"
            precio = PRECIO_PRIMERA_CITA if mensaje_limpio == '1' else PRECIO_SEGUIMIENTO
            
            # Ahora llamamos la función del mes completo sin límite de 7 días
            dias = obtener_dias_disponibles()
            if not dias:
                return "Lo sentimos, no hay días disponibles en lo que resta del mes."

            datos_temp['tipo_cita'] = tipo
            datos_temp['precio'] = precio
            datos_temp['dias_opciones'] = dias
            guardar_estado_usuario(telefono, 'ESPERANDO_DIA', datos_temp)

            respuesta = f"📋 Has seleccionado: *{tipo}* (${precio:,} COP)\n\n"
            respuesta += "📅 *Selecciona el día de tu preferencia enviando el número:*\n\n"
            for idx, dia in enumerate(dias, 1):
                respuesta += f"*{idx}.* {dia['fecha_str']}\n"
            
            respuesta += "\n_Escribe *0* para cancelar._"
            return respuesta
        return "⚠️ Opción no válida. Responde *1* para Primera Cita o *2* para Control."

    # --- ESTADO 3: SELECCIÓN DE DÍA ---
    elif estado == 'ESPERANDO_DIA':
        dias_opciones = datos_temp.get('dias_opciones', [])
        if mensaje_limpio.isdigit():
            opcion = int(mensaje_limpio)
            if 1 <= opcion <= len(dias_opciones):
                dia_elegido = dias_opciones[opcion - 1]
                fecha_iso = dia_elegido['fecha_iso']
                
                horas = obtener_horas_disponibles(fecha_iso)
                if not horas:
                    return f"No hay horas disponibles para {dia_elegido['fecha_str']}. Elige otra fecha."

                datos_temp['fecha_iso'] = fecha_iso
                datos_temp['fecha_str'] = dia_elegido['fecha_str']
                datos_temp['horas_opciones'] = horas
                guardar_estado_usuario(telefono, 'ESPERANDO_HORA', datos_temp)

                respuesta = f"⏰ *Horarios disponibles para {dia_elegido['fecha_str']}:*\n\n"
                for idx, hora in enumerate(horas, 1):
                    respuesta += f"*{idx}.* {hora['hora_str']}\n"
                
                respuesta += "\nEscribe el *número de la hora* que deseas agendar."
                return respuesta
        return f"⚠️ Opción no válida. Por favor, envía un número del *1 al {len(dias_opciones)}*."

    # --- ESTADO 4: SELECCIÓN DE HORA ---
    elif estado == 'ESPERANDO_HORA':
        horas_opciones = datos_temp.get('horas_opciones', [])
        if mensaje_limpio.isdigit():
            opcion = int(mensaje_limpio)
            if 1 <= opcion <= len(horas_opciones):
                hora_elegida = horas_opciones[opcion - 1]
                datos_temp['hora_iso'] = hora_elegida['hora_iso']
                datos_temp['hora_str'] = hora_elegida['hora_str']
                
                guardar_estado_usuario(telefono, 'ESPERANDO_NOMBRE', datos_temp)

                return (
                    f"📝 Resumen de tu selección:\n"
                    f"• *Consulta:* {datos_temp['tipo_cita']}\n"
                    f"• *Fecha:* {datos_temp['fecha_str']}\n"
                    f"• *Hora:* {hora_elegida['hora_str']}\n\n"
                    "Por favor, escribe tu *Nombre Completo* para continuar."
                )
        return f"⚠️ Opción no válida. Envía un número del *1 al {len(horas_opciones)}*."

   # --- ESTADO 5: NOMBRE Y ENVÍO DEL LINK DE PAGO ---
    elif estado == 'ESPERANDO_NOMBRE':
        nombre_usuario = mensaje.strip()
        datos_temp['nombre_paciente'] = nombre_usuario
        
        # Guardar en Google Calendar
        event_id = agendar_cita(
            resumen=f"{datos_temp['tipo_cita']} - {nombre_usuario}",
            fecha=datos_temp['fecha_iso'],
            hora_inicio=datos_temp['hora_iso'],
            descripcion=f"Paciente: {nombre_usuario}\nTeléfono: {telefono}"
        )
        
        if event_id:
            # Guardar registro en la base de datos SQLite para consultas/cancelaciones posteriores
            database.guardar_cita(
                telefono=telefono,
                paciente=nombre_usuario,
                fecha=datos_temp['fecha_str'],
                hora=datos_temp['hora_str'],
                event_id=event_id
            )

            # Reiniciar estado del usuario
            guardar_estado_usuario(telefono, 'INICIO', {}, nombre=nombre_usuario)

            return (
                f"✅ *¡Pre-reserva registrada con éxito!*\n\n"
                f"👤 *Paciente:* {nombre_usuario}\n"
                f"📅 *Fecha:* {datos_temp['fecha_str']}\n"
                f"⏰ *Hora:* {datos_temp['hora_str']}\n"
                f"💰 *Valor:* ${datos_temp['precio']:,} COP\n\n"
                f"💳 *Para confirmar y asegurar tu espacio, realiza el pago en el siguiente enlace:*\n"
                f"{LINK_DE_PAGO}\n\n"
                f"¡Te esperamos!"
            )
        else:
            return "❌ Ocurrió un error al registrar la cita en la agenda. Por favor escribe *1* para intentar agendar nuevamente."