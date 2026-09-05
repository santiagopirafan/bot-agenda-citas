import database
from services.whatsapp_service import (
    enviar_mensaje_texto, 
    enviar_botones_interactivos, 
    enviar_lista_interactiva
)
from services.calendar_service import obtener_dias_disponibles, obtener_horas_disponibles, agendar_cita
from services.wompi_service import obtener_link_pago
from config import PRECIO_VALORACION, PRECIO_PLAN_1, PRECIO_PLAN_2, PRECIO_PLAN_3


def iniciar_agendamiento(telefono):
    """
    Punto de entrada: Cambia el estado en la base de datos a SELECCIONANDO_TIPO
    y despliega las opciones iniciales de consulta con 3 botones.
    """
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_TIPO", {})
    
    texto = (
        "🏥 *Elige el tipo de atención que deseas agendar:*\n\n"
        f"1️⃣ *Valoración Inicial (Solo Virtual):* ${PRECIO_VALORACION:,.0f} COP\n"
        f"2️⃣ *Segunda Valoración:* ${PRECIO_VALORACION:,.0f} COP\n"
        f"3️⃣ *Planes de Control:* Opciones de paquetes con descuento."
    )
    
    botones = [
        ("TIPO_VAL_INICIAL", "1. Val. Inicial"),
        ("TIPO_SEGUNDA_VAL", "2. Segunda Val."),
        ("TIPO_PLANES", "3. Planes")
    ]
    
    enviar_botones_interactivos(telefono, texto, botones)


def procesar_seleccion_tipo(telefono, respuesta_id):
    """
    Procesa la elección. La Valoración Inicial va directo a calendario (Virtual),
    mientras que la Segunda Valoración y los Planes consultan ubicación.
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
        database.guardar_estado_usuario(telefono, "SELECCIONANDO_BOGOTA", datos_temp)
        
        texto = "¿Te encuentras en la ciudad de Bogotá para una atención presencial o prefieres consulta virtual?"
        botones = [
            ("UBICACION_BOGOTA", "Estoy en Bogotá"),
            ("UBICACION_FUERA", "Fuera de Bogotá")
        ]
        enviar_botones_interactivos(telefono, texto, botones)

    elif respuesta_id == "TIPO_PLANES":
        database.guardar_estado_usuario(telefono, "SELECCIONANDO_PLAN", {})
        
        texto = "📦 *Planes de Control Disponibles:*\n\nSelecciona el paquete que mejor se adapte a tus necesidades:"
        opciones = [
            {"id": "PLAN_1", "title": "Plan 1 Cita", "description": f"${PRECIO_PLAN_1:,.0f} COP"},
            {"id": "PLAN_2", "title": "Plan 3 Citas", "description": f"${PRECIO_PLAN_2:,.0f} COP"},
            {"id": "PLAN_3", "title": "Plan 5 Citas", "description": f"${PRECIO_PLAN_3:,.0f} COP"}
        ]
        enviar_lista_interactiva(telefono, texto, "Ver Planes", "Planes Disponibles", opciones)
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona una opción válida de los botones.")


def procesar_seleccion_plan(telefono, respuesta_id, datos_temp):
    """
    Procesa el plan de control seleccionado y consulta la ubicación/modalidad.
    """
    mapa_planes = {
        "PLAN_1": {"nombre": "Plan 1 Cita", "citas": 1},
        "PLAN_2": {"nombre": "Plan 3 Citas", "citas": 3},
        "PLAN_3": {"nombre": "Plan 5 Citas", "citas": 5}
    }
    
    if respuesta_id in mapa_planes:
        plan_info = mapa_planes[respuesta_id]
        datos_temp["tipo_cita"] = f"Plan de Control ({plan_info['nombre']})"
        datos_temp["plan_nombre"] = respuesta_id
        datos_temp["citas_restantes"] = plan_info["citas"]
        
        database.guardar_estado_usuario(telefono, "SELECCIONANDO_BOGOTA", datos_temp)
        
        texto = "¿Te encuentras en Bogotá para tomar la atención de tu plan presencialmente o de forma virtual?"
        botones = [
            ("UBICACION_BOGOTA", "Estoy en Bogotá"),
            ("UBICACION_FUERA", "Fuera de Bogotá")
        ]
        enviar_botones_interactivos(telefono, texto, botones)
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona un plan válido de la lista.")


def procesar_seleccion_ubicacion(telefono, respuesta_id, datos_temp):
    """
    Determina si la cita permite Presencial/Virtual o fuerza Virtual según la ubicación.
    """
    if respuesta_id == "UBICACION_BOGOTA":
        database.guardar_estado_usuario(telefono, "SELECCIONANDO_MODALIDAD", datos_temp)
        texto = "📍 *Elige la modalidad de tu atención:*\n\n• *Presencial:* Atención en consultorio (días pares).\n• *Virtual:* Consulta por videollamada (días impares)."
        botones = [
            ("MOD_PRESENCIAL", "🏢 Presencial"),
            ("MOD_VIRTUAL", "💻 Virtual")
        ]
        enviar_botones_interactivos(telefono, texto, botones)
    elif respuesta_id == "UBICACION_FUERA":
        datos_temp["modalidad"] = "VIRTUAL"
        mostrar_dias_disponibles(telefono, datos_temp)
    else:
        enviar_mensaje_texto(telefono, "⚠️ Por favor, selecciona tu ubicación con los botones.")


def procesar_seleccion_modalidad(telefono, respuesta_id, datos_temp):
    """
    Guarda la modalidad (PRESENCIAL o VIRTUAL) y despliega el calendario respetando pares/impares.
    """
    if respuesta_id not in ["MOD_PRESENCIAL", "MOD_VIRTUAL"]:
        enviar_mensaje_texto(telefono, "⚠️ Selecciona una modalidad válida.")
        return

    datos_temp["modalidad"] = "PRESENCIAL" if respuesta_id == "MOD_PRESENCIAL" else "VIRTUAL"
    mostrar_dias_disponibles(telefono, datos_temp)


def mostrar_dias_disponibles(telefono, datos_temp):
    """
    Consulta días disponibles en Google Calendar según reglas de agenda y guarda el estado.
    """
    modalidad = datos_temp.get("modalidad", "VIRTUAL")
    dias = obtener_dias_disponibles(modalidad=modalidad)
    
    if not dias:
        enviar_mensaje_texto(telefono, "❌ No hay días disponibles en las próximas semanas para esta modalidad.")
        return

    datos_temp["dias_opciones"] = dias
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_FECHA", datos_temp)
    
    opciones = []
    for d in dias:
        opciones.append({
            "id": f"FECHA_{d['fecha_iso']}",
            "title": d['fecha_str'][:24],
            "description": f"Atención {modalidad.capitalize()}"
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
        enviar_mensaje_texto(telefono, f"❌ No quedan horarios disponibles para el {fecha_str}. Selecciona otra fecha.")
        mostrar_dias_disponibles(telefono, datos_temp)
        return

    datos_temp["horas_opciones"] = horas
    database.guardar_estado_usuario(telefono, "SELECCIONANDO_HORA", datos_temp)
    
    opciones = []
    for h in horas:
        opciones.append({
            "id": f"HORA_{h['hora_iso']}--{h['hora_str']}",
            "title": h['hora_str'][:24]
        })
        
    texto = f"⏰ *Horarios disponibles para el {fecha_str}:*"
    enviar_lista_interactiva(telefono, texto, "Ver Horas", "Horarios", opciones)


def procesar_seleccion_hora(telefono, respuesta_id, datos_temp):
    """
    Desempaqueta el ID de la hora y solicita el nombre completo del paciente.
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
    
    database.guardar_estado_usuario(telefono, "ESPERANDO_NOMBRE", datos_temp)
    enviar_mensaje_texto(telefono, "✍️ Por favor, escribe el *Nombre Completo* del paciente que tomará la consulta:")


def procesar_nombre_paciente(telefono, nombre, datos_temp):
    """
    Registra la cita. Si es virtual, envía link de pago y queda pendiente. 
    Si es presencial, agenda directamente en Calendar, verifica la creación 
    y avisa del pago en efectivo en recepción.
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
            
            # Desempaquetado seguro idéntico a app.py
            if isinstance(res_cal, tuple):
                event_id, meet_link = res_cal
            else:
                event_id = res_cal
                
        except Exception as e:
            print(f"[ERROR CALENDAR PRESENCIAL] {e}")
            enviar_mensaje_texto(telefono, "❌ Lo siento, ocurrió un error al intentar registrar tu cita en el calendario. Por favor, intenta agendar nuevamente en unos minutos.")
            database.guardar_estado_usuario(telefono, "INICIO", {})
            return # Cortamos la ejecución si Calendar falla

        # Solo si Calendar nos devuelve un event_id válido, guardamos en base de datos
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
                'estado': "PENDIENTE_PAGO", # Obligatorio para que confirmar_cita_pagada la detecte
                'plan_nombre': plan_nombre,
                'citas_restantes': citas_restantes,
                'event_id': None,
                'meet_link': None
            }
            
            # 1. Guardamos como pendiente para resetear cualquier cita anterior
            database.guardar_cita_pendiente(data_cita)
            
            # 2. Inyectamos el event_id y la pasamos a CONFIRMADA
            database.confirmar_cita_pagada(telefono, event_id, meet_link)

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