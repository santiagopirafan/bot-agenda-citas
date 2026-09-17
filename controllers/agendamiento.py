import database
from services.whatsapp_service import (
    enviar_mensaje_texto, 
    enviar_botones_interactivos, 
    enviar_lista_interactiva
)
from services.calendar_service import obtener_dias_disponibles, obtener_horas_disponibles, agendar_cita, eliminar_evento
from services.wompi_service import obtener_link_pago
from config import PRECIO_VALORACION, PRECIO_PLAN_1, PRECIO_PLAN_2, PRECIO_PLAN_3


def iniciar_agendamiento(telefono):
    """
    Punto de entrada: Cambia el estado a SELECCIONANDO_TIPO
    y despliega las opciones mediante lista interactiva.
    """
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_TIPO", {})
    
    texto = (
        "🏥 *Elige el tipo de atención que deseas agendar:*\n\n"
        f"1️⃣ *Valoración Inicial (Solo Virtual):* ${PRECIO_VALORACION:,.0f} COP\n"
        f"2️⃣ *Segunda Valoración:* ${PRECIO_VALORACION:,.0f} COP\n"
        f"3️⃣ *Controles:* Opciones de paquetes con descuento."
    )
    
    opciones = [
        {"id": "TIPO_VAL_INICIAL", "title": "1. Valoración Inicial", "description": f"${PRECIO_VALORACION:,.0f} COP (Virtual)"},
        {"id": "TIPO_SEGUNDA_VAL", "title": "2. Segunda Valoración", "description": f"${PRECIO_VALORACION:,.0f} COP"},
        {"id": "TIPO_PLANES", "title": "3. Controles", "description": ""},
        {"id": "BTN_ATRAS", "title": "↩️ Menú Principal", "description": "Regresar al menú principal"}
    ]
    
    enviar_lista_interactiva(telefono, texto, "Ver Servicios", "Tipos de Atención", opciones)


def procesar_seleccion_tipo(telefono, respuesta_id):
    """
    Procesa la elección del tipo de servicio.
    """
    if respuesta_id == "TIPO_VAL_INICIAL":
        datos_temp = {
            "tipo_cita": "Valoración Inicial",
            "plan_nombre": "VALORACION",
            "citas_restantes": 1,
            "modalidad": "VIRTUAL"  # Se fuerza virtual directamente
        }
        mostrar_dias_disponibles(telefono, datos_temp)

    elif respuesta_id == "TIPO_SEGUNDA_VAL":
        datos_temp = {
            "tipo_cita": "Segunda Valoración",
            "plan_nombre": "VALORACION",
            "citas_restantes": 1
        }
        pedir_ubicacion_bogota(telefono, datos_temp)

    elif respuesta_id == "TIPO_PLANES":
        datos_temp = {
            "tipo_cita": "Control",
            "plan_nombre": "PLAN_1",
            "citas_restantes": 1
        }
        pedir_modalidad(telefono, datos_temp)

    elif respuesta_id == "BTN_ATRAS":
        pass

    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona una opción válida de la lista.")


def pedir_modalidad(telefono, datos_temp):
    """Solicita la modalidad guardando el estado."""
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_MODALIDAD", datos_temp)
    texto = "📍 *Elige la modalidad de tu atención:*\n\n• *Presencial:* Atención en consultorio (días pares).\n• *Virtual:* Consulta por videollamada (días impares)."
    botones = [
        ("MOD_PRESENCIAL", "🏢 Presencial"),
        ("MOD_VIRTUAL", "💻 Virtual"),
        ("BTN_ATRAS", "↩️ Volver Atrás")
    ]
    enviar_botones_interactivos(telefono, texto, botones)


def procesar_seleccion_modalidad(telefono, respuesta_id, datos_temp):
    """
    Guarda la modalidad (PRESENCIAL o VIRTUAL).
    - Presencial en Controles: Pasa directo a ver días disponibles.
    - Virtual en Controles: Muestra la lista de paquetes de controles.
    """
    if respuesta_id not in ["MOD_PRESENCIAL", "MOD_VIRTUAL"]:
        enviar_mensaje_texto(telefono, "⚠️ Selecciona una modalidad válida.")
        return

    modalidad_elegida = "PRESENCIAL" if respuesta_id == "MOD_PRESENCIAL" else "VIRTUAL"
    datos_temp["modalidad"] = modalidad_elegida

    if datos_temp.get("tipo_cita") == "Control":
        if modalidad_elegida == "PRESENCIAL":
            mostrar_dias_disponibles(telefono, datos_temp)
        else:
            mostrar_planes(telefono, datos_temp)
    else:
        mostrar_dias_disponibles(telefono, datos_temp)


def mostrar_planes(telefono, datos_temp):
    """Muestra la lista de paquetes de controles."""
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_PLAN", datos_temp)
    
    texto = "📦 *Controles Disponibles:*\n\nSelecciona la opción que mejor se adapte a tus necesidades:"
    opciones = [
        {"id": "PLAN_1", "title": "1 Control", "description": f"${PRECIO_PLAN_1:,.0f} COP (1 Control)"},
        {"id": "PLAN_2", "title": "3 Controles", "description": f"${PRECIO_PLAN_2:,.0f} COP (Paquete)"},
        {"id": "PLAN_3", "title": "5 Controles", "description": f"${PRECIO_PLAN_3:,.0f} COP (Paquete)"},
        {"id": "BTN_ATRAS", "title": "↩️ Volver Atrás", "description": "Regresar a Modalidad"}
    ]
    enviar_lista_interactiva(telefono, texto, "Ver Controles", "Opciones de Controles", opciones)


def procesar_seleccion_plan(telefono, respuesta_id, datos_temp):
    """
    Procesa la opción de control seleccionada y solicita la ubicación.
    """
    mapa_planes = {
        "PLAN_1": {"nombre": "1 Control", "citas": 1},
        "PLAN_2": {"nombre": "3 Controles", "citas": 3},
        "PLAN_3": {"nombre": "5 Controles", "citas": 5}
    }
    
    if respuesta_id in mapa_planes:
        plan_info = mapa_planes[respuesta_id]
        datos_temp["tipo_cita"] = f"Control ({plan_info['nombre']})"
        datos_temp["plan_nombre"] = respuesta_id
        datos_temp["citas_restantes"] = plan_info["citas"]
        
        pedir_ubicacion_bogota(telefono, datos_temp)
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona una opción válida de controles.")


def pedir_ubicacion_bogota(telefono, datos_temp):
    """Solicita la ubicación guardando el estado."""
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_BOGOTA", datos_temp)
    
    texto = "¿Te encuentras en la ciudad de Bogotá para tu atención o en otra ubicación?"
    botones = [
        ("UBICACION_BOGOTA", "Estoy en Bogotá"),
        ("UBICACION_FUERA", "Fuera de Bogotá"),
        ("BTN_ATRAS", "↩️ Volver Atrás")
    ]
    enviar_botones_interactivos(telefono, texto, botones)


def procesar_seleccion_ubicacion(telefono, respuesta_id, datos_temp):
    """
    Determina la continuidad hacia el calendario tras responder ubicación.
    """
    if respuesta_id in ["UBICACION_BOGOTA", "UBICACION_FUERA"]:
        mostrar_dias_disponibles(telefono, datos_temp)
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona tu ubicación con los botones.")


def mostrar_dias_disponibles(telefono, datos_temp):
    """
    Consulta días disponibles e incluye la opción de retroceso en la lista.
    """
    modalidad = datos_temp.get("modalidad", "VIRTUAL")
    dias = obtener_dias_disponibles(modalidad=modalidad)
    
    if not dias:
        botones = [("BTN_ATRAS", "↩️ Volver Atrás")]
        enviar_botones_interactivos(
            telefono, 
            "❌ No hay días disponibles en las próximas semanas para esta modalidad.", 
            botones
        )
        return

    datos_temp["dias_opciones"] = dias
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_FECHA", datos_temp)
    
    opciones = []
    for d in dias[:9]:
        opciones.append({
            "id": f"FECHA_{d['fecha_iso']}",
            "title": d['fecha_str'][:24],
            "description": f"Atención {modalidad.capitalize()}"
        })
        
    opciones.append({
        "id": "BTN_ATRAS",
        "title": "↩️ Volver Atrás",
        "description": "Regresar al paso anterior"
    })
    
    texto = f"📅 *Días disponibles ({modalidad.lower()}):*\n\nSelecciona la fecha que prefieras:"
    enviar_lista_interactiva(telefono, texto, "Ver Días", "Fechas Disponibles", opciones)


def procesar_seleccion_fecha(telefono, respuesta_id, datos_temp):
    """
    Guarda la fecha seleccionada y solicita los horarios libres.
    """
    if not respuesta_id.startswith("FECHA_"):
        enviar_mensaje_texto(telefono, "⚠️ Selecciona una fecha válida de la lista.")
        return

    fecha_iso = respuesta_id.replace("FECHA_", "")
    dias_opciones = datos_temp.get("dias_opciones", [])
    
    dia_enc = next((d for d in dias_opciones if d["fecha_iso"] == fecha_iso), None)
    fecha_str = dia_enc["fecha_str"] if dia_enc else fecha_iso
    
    datos_temp["fecha_iso"] = fecha_iso
    datos_temp["fecha_str"] = fecha_str
    
    modalidad = datos_temp.get("modalidad", "VIRTUAL")
    horas = obtener_horas_disponibles(fecha_iso, modalidad=modalidad)
    
    if not horas:
        botones = [("BTN_ATRAS", "↩️ Elegir otra fecha")]
        enviar_botones_interactivos(
            telefono, 
            f"❌ No quedan horarios disponibles para el {fecha_str}.", 
            botones
        )
        return

    datos_temp["horas_opciones"] = horas
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_HORA", datos_temp)
    
    opciones = []
    for h in horas[:9]:
        opciones.append({
            "id": f"HORA_{h['hora_iso']}--{h['hora_str']}",
            "title": h['hora_str'][:24]
        })
        
    opciones.append({
        "id": "BTN_ATRAS",
        "title": "↩️ Volver Atrás",
        "description": "Regresar a selección de fecha"
    })
    
    texto = f"⏰ *Horarios disponibles para el {fecha_str}:*"
    enviar_lista_interactiva(telefono, texto, "Ver Horas", "Horarios", opciones)


def procesar_seleccion_hora(telefono, respuesta_id, datos_temp):
    """
    Desempaqueta el ID de la hora. Si es reagendamiento, solicita confirmación final.
    """
    if not respuesta_id.startswith("HORA_"):
        enviar_mensaje_texto(telefono, "⚠️ Selecciona un horario válido.")
        return

    contenido_hora = respuesta_id.replace("HORA_", "")
    
    if "--" in contenido_hora:
        hora_iso, hora_str = contenido_hora.split("--")
    else:
        hora_iso = contenido_hora
        hora_str = contenido_hora

    datos_temp["hora_iso"] = hora_iso
    datos_temp["hora_str"] = hora_str
    
    # 👈 FLUJO DE REAGENDAMIENTO: Pedir confirmación final antes de borrar la cita anterior
    if datos_temp.get("reagendando"):
        database.guardar_estado_usuario(telefono, "CONFIRMANDO_REAGENDAMIENTO", datos_temp)
        
        texto = (
            f"❓ *¿Deseas reconfirmar el reagendamiento de tu cita?*\n\n"
            f"👤 *Paciente:* {datos_temp.get('paciente')}\n"
            f"📋 *Servicio:* {datos_temp.get('tipo_cita')}\n"
            f"📍 *Modalidad:* {datos_temp.get('modalidad')}\n"
            f"📅 *Nueva Fecha:* {datos_temp.get('fecha_str')}\n"
            f"⏰ *Nueva Hora:* {datos_temp.get('hora_str')}\n\n"
            f"_Al reconfirmar, tu cita anterior quedará cancelada y se actualizará el nuevo horario._"
        )
        botones = [
            ("CONFIRMAR_REAGENDO_SI", "✅ Sí, Confirmar"),
            ("CONFIRMAR_REAGENDO_NO", "❌ No, Cancelar"),
            ("BTN_ATRAS", "↩️ Cambiar Hora")
        ]
        enviar_botones_interactivos(telefono, texto, botones)
        return

    # Flujo estándar de agendamiento nuevo
    database.guardar_estado_usuario(telefono, "ESPERANDO_NOMBRE", datos_temp)
    
    botones = [("BTN_ATRAS", "↩️ Cambiar Hora")]
    texto = "✍️ Por favor, escribe el *Nombre Completo* del paciente que tomará la consulta:"
    enviar_botones_interactivos(telefono, texto, botones)


def procesar_confirmacion_reagendamiento(telefono, respuesta_id, datos_temp):
    """
    Procesa la respuesta al reagendamiento:
    - SI: Elimina evento anterior y registra la cita nueva con los mismos datos del paciente.
    - NO: Cancela el reagendamiento y mantiene la cita original activa.
    """
    if respuesta_id == "CONFIRMAR_REAGENDO_SI":
        event_id_previo = datos_temp.get("event_id_previo")
        
        # 1. Eliminar evento antiguo en Google Calendar si existía
        if event_id_previo:
            try:
                eliminar_evento(event_id_previo)
            except Exception as e:
                print(f"[ERROR ELIMINAR EVENTO PREVIO] {e}")

        # 2. Remover el registro antiguo de la base de datos
        database.eliminar_cita_por_telefono(telefono)

        # 3. Guardar el nuevo agendamiento manteniendo el nombre del paciente
        paciente_nombre = datos_temp.get("paciente", "Paciente")
        procesar_nombre_paciente(telefono, paciente_nombre, datos_temp)

    elif respuesta_id in ["CONFIRMAR_REAGENDO_NO", "BTN_CANCELAR"]:
        enviar_mensaje_texto(telefono, "🚫 *Reagendamiento cancelado.* Tu cita original se mantiene activa sin cambios.")
        database.guardar_estado_usuario(telefono, "INICIO", {})
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona una opción válida usando los botones.")


def procesar_nombre_paciente(telefono, nombre, datos_temp):
    """
    Registra la cita respetando la lógica original de presencial y virtual.
    """
    paciente_nombre = nombre.strip().title()
    modalidad = datos_temp.get("modalidad", "VIRTUAL")
    tipo_cita = datos_temp.get("tipo_cita", "Valoración Inicial")
    plan_nombre = datos_temp.get("plan_nombre", "VALORACION")
    citas_restantes = datos_temp.get("citas_restantes", 1)

    link_pago, precio = obtener_link_pago(plan_nombre)

    if modalidad == "VIRTUAL":
        # Flujo Virtual: Pendiente de pago
        data_cita = {
            'telefono': telefono,
            'paciente': paciente_nombre,
            'tipo_cita': tipo_cita,
            'modalidad': modalidad,
            'fecha_iso': datos_temp.get("fecha_iso"),
            'fecha_str': datos_temp.get("fecha_str"),
            'hora_iso': datos_temp.get("hora_iso"),
            'hora_str': datos_temp.get("hora_str"),
            'estado': "PENDIENTE_PAGO",
            'plan_nombre': plan_nombre,
            'citas_restantes': citas_restantes,
            'event_id': None,
            'meet_link': None
        }
        database.guardar_cita_pendiente(data_cita)

        # Si viene de un reagendamiento exitoso
        if datos_temp.get("reagendando"):
            mensaje = (
                f"✅ *Cita Virtual Reagendada Exitosamente*\n\n"
                f"👤 *Paciente:* {paciente_nombre}\n"
                f"📋 *Servicio:* {tipo_cita}\n"
                f"📅 *Nueva Fecha:* {datos_temp.get('fecha_str')}\n"
                f"⏰ *Nueva Hora:* {datos_temp.get('hora_str')}\n\n"
                f"_Se ha actualizado tu información. Si ya habías pagado, tu pago cubrirá esta nueva fecha._"
            )
        else:
            mensaje = (
                f"✅ *Pre-reserva Virtual Registrada*\n\n"
                f"👤 *Paciente:* {paciente_nombre}\n"
                f"📋 *Servicio:* {tipo_cita}\n"
                f"📅 *Fecha:* {datos_temp.get('fecha_str')}\n"
                f"⏰ *Hora:* {datos_temp.get('hora_str')}\n"
                f"💰 *Valor:* ${precio:,.0f} COP\n\n"
                f"💳 *Para confirmar tu cita, realiza el pago aquí:*\n{link_pago}\n\n"
                f"_Una vez confirmado el pago, se agendará automáticamente tu espacio en el calendario y recibirás el enlace de Google Meet._"
            )
        
        enviar_mensaje_texto(telefono, mensaje)
        database.guardar_estado_usuario(telefono, "INICIO", {})

    else:
        # Flujo Presencial: Se agenda de inmediato
        event_id, meet_link = None, None
        try:
            res_cal = agendar_cita(
                resumen=f"{tipo_cita} - {paciente_nombre}",
                fecha=datos_temp.get("fecha_iso"),
                hora_inicio=datos_temp.get("hora_iso"),
                descripcion=f"Paciente: {paciente_nombre}\nTeléfono: {telefono}\nModalidad: {modalidad}",
                modalidad=modalidad
            )
            
            if isinstance(res_cal, tuple):
                event_id, meet_link = res_cal
            else:
                event_id = res_cal
                
        except Exception as e:
            print(f"[ERROR CALENDAR PRESENCIAL] {e}")
            enviar_mensaje_texto(telefono, "❌ Lo siento, ocurrió un error al intentar registrar tu cita en el calendario. Por favor, intenta agendar nuevamente en unos minutos.")
            database.guardar_estado_usuario(telefono, "INICIO", {})
            return

        if event_id:
            data_cita = {
                'telefono': telefono,
                'paciente': paciente_nombre,
                'tipo_cita': tipo_cita,
                'modalidad': modalidad,
                'fecha_iso': datos_temp.get("fecha_iso"),
                'fecha_str': datos_temp.get("fecha_str"),
                'hora_iso': datos_temp.get("hora_iso"),
                'hora_str': datos_temp.get("hora_str"),
                'estado': "PENDIENTE_PAGO",
                'plan_nombre': plan_nombre,
                'citas_restantes': citas_restantes,
                'event_id': None,
                'meet_link': None
            }
            
            database.guardar_cita_pendiente(data_cita)
            database.confirmar_cita_pagada(telefono, event_id, meet_link)

            if datos_temp.get("reagendando"):
                mensaje = (
                    f"✅ *Cita Presencial Reagendada Exitosamente*\n\n"
                    f"👤 *Paciente:* {paciente_nombre}\n"
                    f"📋 *Servicio:* {tipo_cita}\n"
                    f"📅 *Nueva Fecha:* {datos_temp.get('fecha_str')}\n"
                    f"⏰ *Nueva Hora:* {datos_temp.get('hora_str')}\n"
                    f"📍 *Lugar:* Consultorio Médico Bogotá"
                )
            else:
                mensaje = (
                    f"✅ *Cita Presencial Agendada Exitosamente*\n\n"
                    f"👤 *Paciente:* {paciente_nombre}\n"
                    f"📋 *Servicio:* {tipo_cita}\n"
                    f"📅 *Fecha:* {datos_temp.get('fecha_str')}\n"
                    f"⏰ *Hora:* {datos_temp.get('hora_str')}\n"
                    f"📍 *Lugar:* Consultorio Médico Bogotá\n\n"
                    f"⚠️ *Importante:* Recuerda cancelar el valor de ${precio:,.0f} COP en efectivo directamente en la recepción antes de ingresar a tu consulta."
                )
            
            enviar_mensaje_texto(telefono, mensaje)
            database.guardar_estado_usuario(telefono, "INICIO", {})