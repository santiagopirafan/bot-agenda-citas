from calendar_service import obtener_dias_disponibles, obtener_horas_disponibles
from database import obtener_usuario, guardar_estado_usuario, consultar_citas, eliminar_cita
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
            "*3.* Cancelar cita registrada"
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
        elif mensaje_limpio in ['2', 'consultar', 'consultar cita', 'ver cita']:
            cita = consultar_citas(telefono)
            if cita:
                texto_meet = f"\n💻 *Enlace a Google Meet:*\n{cita['meet_link']}\n" if cita.get('meet_link') else ""
                return (
                    f"📌 *Tu cita agendada:*\n\n"
                    f"👤 *Paciente:* {cita['paciente']}\n"
                    f"📅 *Fecha:* {cita['fecha']}\n"
                    f"⏰ *Hora:* {cita['hora']}\n"
                    f"{texto_meet}\n"
                    f"¡Te esperamos!"
                )
            else:
                return "❌ No encontramos ninguna cita pagada o activa registrada con este número de teléfono."

        elif mensaje_limpio in ['3', 'eliminar cita', 'cancelar cita']:
            cita = consultar_citas(telefono)
            if cita:
                eliminar_cita(telefono)
                return "✅ Tu cita ha sido eliminada del sistema."
            else:
                return "❌ No tienes ninguna cita registrada para cancelar."

        else:
            # Retorna None para que main.py/webhook gestione saludos u otros textos desconocidos
            return None

    # --- ESTADO 2: SELECCIÓN TIPO DE CITA ---
    elif estado == 'SELECCIONANDO_TIPO':
        if mensaje_limpio in ['1', '2']:
            tipo = "Primera Cita" if mensaje_limpio == '1' else "Cita de Seguimiento"
            precio = PRECIO_PRIMERA_CITA if mensaje_limpio == '1' else PRECIO_SEGUIMIENTO
            
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
                respuesta += "Escribe el *número de la hora* que deseas agendar:\n\n"
                for idx, hora in enumerate(horas, 1):
                    respuesta += f"*{idx}.* {hora['hora_str']}\n"
                
                respuesta += "\n_Escribe *0* para cancelar._"
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

    # --- ESTADO 5: NOMBRE Y REGISTRO PENDIENTE ---
    elif estado == 'ESPERANDO_NOMBRE':
        nombre_usuario = mensaje.strip()
        datos_temp['nombre_paciente'] = nombre_usuario
        
        # Guardar registro preliminar en SQLite con estado PENDIENTE
        if hasattr(database, 'guardar_cita_pendiente'):
            database.guardar_cita_pendiente(
                telefono=telefono,
                paciente=nombre_usuario,
                fecha_str=datos_temp['fecha_str'],
                fecha_iso=datos_temp['fecha_iso'],
                hora_str=datos_temp['hora_str'],
                hora_iso=datos_temp['hora_iso'],
                tipo_cita=datos_temp['tipo_cita']
            )
        else:
            database.guardar_cita(
                telefono=telefono,
                paciente=nombre_usuario,
                fecha=datos_temp['fecha_str'],
                hora=datos_temp['hora_str'],
                event_id=None,
                estado='PENDIENTE'
            )

        # Transicionar a ESPERANDO_PAGO
        guardar_estado_usuario(telefono, 'ESPERANDO_PAGO', datos_temp, nombre=nombre_usuario)

        return (
            f"✅ *Pre-reserva registrada con éxito.*\n\n"
            f"👤 *Paciente:* {nombre_usuario}\n"
            f"📅 *Fecha:* {datos_temp['fecha_str']}\n"
            f"⏰ *Hora:* {datos_temp['hora_str']}\n"
            f"💰 *Valor:* ${datos_temp['precio']:,} COP\n\n"
            f"💳 *Para confirmar y agendar tu cita en el calendario, realiza el pago en el siguiente enlace:*\n"
            f"{LINK_DE_PAGO}\n\n"
            f"_Una vez confirmado el pago, tu cita se agendará automáticamente en nuestra agenda._"
        )

    # --- ESTADO 6: ESPERANDO PAGO ---
    elif estado == 'ESPERANDO_PAGO':
        return (
            "⏳ Estamos a la espera de la confirmación de tu pago.\n\n"
            f"Por favor ingresa al enlace para completar el pago:\n{LINK_DE_PAGO}\n\n"
            "Una vez aprobado, tu cita se agendará en el calendario automáticamente.\n"
            "_Escribe *0* o *cancelar* si deseas reiniciar el proceso._"
        )