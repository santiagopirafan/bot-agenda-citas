import database 
import procesador
from controllers.agendamiento import (
    iniciar_agendamiento,
    mostrar_planes,
    pedir_ubicacion_bogota,
    pedir_modalidad,
    mostrar_dias_disponibles,
    procesar_seleccion_tipo,
    procesar_seleccion_plan,
    procesar_seleccion_ubicacion,
    procesar_seleccion_modalidad,
    procesar_seleccion_fecha,
    procesar_seleccion_hora,
    procesar_nombre_paciente
)
from services.whatsapp_service import enviar_mensaje_texto, enviar_botones_interactivos
from services.calendar_service import eliminar_evento

def recibir_mensaje(telefono, texto, interactive_id=None):
    """
    Ruteador principal que procesa la petición recibida por WhatsApp,
    manejando el menú de bienvenida, consulta, reagendamiento, cancelación,
    navegación hacia atrás y la máquina de estados.
    """
    estado, datos_temp = database.obtener_estado_usuario(telefono)
    texto_limpio = texto.strip().lower() if texto else ""

    # Comando universal para reiniciar conversación desde cualquier punto
    if texto_limpio in ['0', 'cancelar todo', 'inicio', 'menu', 'reiniciar']:
        mostrar_menu_principal(telefono, "🔄 Proceso reiniciado. ¿En qué puedo ayudarte?")
        return

    # Determinamos el ID interactivo si proviene de botón o lista, de lo contrario usamos texto
    payload_id = interactive_id if interactive_id else texto_limpio

    # --- MANEJO CENTRAL DE RETROCESO (BTN_ATRAS / ATRAS) ---
    if payload_id in ['BTN_ATRAS', 'atras', 'atrás', 'volver', 'regresar', '00']:
        retroceder_estado(telefono, estado, datos_temp)
        return

    # --- 1. MENÚ PRINCIPAL (Estado INICIO) ---
    if estado == 'INICIO':
        # Opcion 1: AGENDAR
        if payload_id in ['BTN_AGENDAR', '1', 'agendar', 'agendar cita']:
            iniciar_agendamiento(telefono)
            return

        # Opcion 2: CONSULTAR CITA
        elif payload_id in ['BTN_CONSULTAR', '2', 'consultar', 'mis citas', 'consultar cita']:
            cita = database.obtener_cita_activa(telefono)
            if cita:
                texto_meet = f"\n💻 *Enlace a la Videollamada:*\n{cita['meet_link']}\n" if cita.get('meet_link') else ""
                msg = (
                    f"📌 *Tu cita activa:*\n\n"
                    f"👤 *Paciente:* {cita['paciente']}\n"
                    f"📋 *Servicio:* {cita['tipo_cita']}\n"
                    f"📍 *Modalidad:* {cita.get('modalidad', 'VIRTUAL')}\n"
                    f"📅 *Fecha:* {cita['fecha_str']}\n"
                    f"⏰ *Hora:* {cita['hora_str']}\n"
                    f"{texto_meet}"
                )
            else:
                msg = "❌ No tienes ninguna cita activa o pagada registrada actualmente."
            enviar_mensaje_texto(telefono, msg)
            return

        # Opcion 3: REAGENDAR CITA
        elif payload_id in ['BTN_REAGENDAR', '3', 'reagendar', 'reagendar cita']:
            cita = database.obtener_cita_activa(telefono)
            if cita:
                if cita.get('event_id'):
                    eliminar_evento(cita['event_id'])
                database.eliminar_cita_por_telefono(telefono)
                enviar_mensaje_texto(telefono, "🔄 Vamos a reagendar tu cita. Por favor selecciona el nuevo horario:")
                iniciar_agendamiento(telefono)
            else:
                enviar_mensaje_texto(telefono, "❌ No tienes citas activas para reagendar. Puedes agendar una cita nueva.")
            return

        # Opcion 4: CANCELAR CITA
        elif payload_id in ['BTN_CANCELAR', '4', 'cancelar', 'cancelar cita']:
            event_id = database.eliminar_cita_por_telefono(telefono)
            if event_id:
                eliminar_evento(event_id)
                enviar_mensaje_texto(telefono, "✅ Tu cita ha sido cancelada exitosamente y el horario fue liberado en el calendario.")
            else:
                enviar_mensaje_texto(telefono, "❌ No encontramos ninguna cita activa registrada para cancelar.")
            return

    # --- 2. MÁQUINA DE ESTADOS (CONTROLLER) ---
    if estado == 'SELECCIONANDO_TIPO':
        procesar_seleccion_tipo(telefono, payload_id)
        return

    elif estado == 'SELECCIONANDO_PLAN':
        procesar_seleccion_plan(telefono, payload_id, datos_temp)
        return

    elif estado == 'SELECCIONANDO_BOGOTA':
        procesar_seleccion_ubicacion(telefono, payload_id, datos_temp)
        return

    elif estado == 'SELECCIONANDO_MODALIDAD':
        procesar_seleccion_modalidad(telefono, payload_id, datos_temp)
        return

    elif estado == 'SELECCIONANDO_FECHA':
        procesar_seleccion_fecha(telefono, payload_id, datos_temp)
        return

    elif estado == 'SELECCIONANDO_HORA':
        procesar_seleccion_hora(telefono, payload_id, datos_temp)
        return

    elif estado == 'ESPERANDO_NOMBRE':
        procesar_nombre_paciente(telefono, texto, datos_temp)
        return

    # --- 3. PROCESADOR SECUNDARIO (Respuestas frecuentes / Legacy) ---
    if hasattr(procesador, 'procesar_mensaje_usuario'):
        respuesta_legacy = procesador.procesar_mensaje_usuario(telefono, texto)
        if respuesta_legacy:
            enviar_mensaje_texto(telefono, respuesta_legacy)
            return

    # --- 4. MENÚ POR DEFECTO (Si no coincide con nada) ---
    mostrar_menu_principal(telefono)


def retroceder_estado(telefono, estado_actual, datos_temp):
    """
    Evalúa el estado actual y devuelve al usuario exactamente al paso anterior,
    conservando la información registrada en datos_temp.
    """
    if estado_actual == 'SELECCIONANDO_TIPO':
        mostrar_menu_principal(telefono, "🔄 Regresamos al menú principal:")

    elif estado_actual == 'SELECCIONANDO_PLAN':
        iniciar_agendamiento(telefono)

    elif estado_actual == 'SELECCIONANDO_BOGOTA':
        # Si venía de Planes, vuelve a Planes; si no, vuelve a Selección de Tipo
        if datos_temp.get('plan_nombre') and datos_temp['plan_nombre'] != 'VALORACION':
            mostrar_planes(telefono, datos_temp)
        else:
            iniciar_agendamiento(telefono)

    elif estado_actual == 'SELECCIONANDO_MODALIDAD':
        pedir_ubicacion_bogota(telefono, datos_temp)

    elif estado_actual == 'SELECCIONANDO_FECHA':
        # Si la modalidad se fijó por estar fuera de Bogotá, vuelve a ubicación
        if datos_temp.get('en_bogota') is False:
            pedir_ubicacion_bogota(telefono, datos_temp)
        # Si la cita es Valoración Inicial (que fuerza virtual de entrada), vuelve a selección de tipo
        elif datos_temp.get('tipo_cita') == 'Valoración Inicial':
            iniciar_agendamiento(telefono)
        else:
            pedir_modalidad(telefono, datos_temp)

    elif estado_actual == 'SELECCIONANDO_HORA':
        mostrar_dias_disponibles(telefono, datos_temp)

    elif estado_actual == 'ESPERANDO_NOMBRE':
        # Reobtiene las horas para la fecha previamente seleccionada
        fecha_iso = datos_temp.get('fecha_iso')
        fecha_str = datos_temp.get('fecha_str', fecha_iso)
        if fecha_iso:
            procesar_seleccion_fecha(telefono, f"FECHA_{fecha_iso}", datos_temp)
        else:
            mostrar_dias_disponibles(telefono, datos_temp)

    else:
        mostrar_menu_principal(telefono)


def mostrar_menu_principal(telefono, encabezado="👋 ¡Bienvenido al asistente de agendamiento médico!"):
    """
    Despliega el menú principal con botones para una interacción rápida.
    """
    database.guardar_estado_usuario(telefono, 'INICIO', {})
    
    botones = [
        ("BTN_AGENDAR", "📅 Agendar Cita"),
        ("BTN_CONSULTAR", "🔍 Consultar Cita"),
        ("BTN_REAGENDAR", "🔄 Reagendar Cita")
    ]
    
    texto = (
        f"{encabezado}\n\n"
        "Selecciona una opción:\n"
        "1️⃣ *Agendar Cita:* Crear nueva reserva.\n"
        "2️⃣ *Consultar Cita:* Ver los datos de tu cita actual.\n"
        "3️⃣ *Reagendar Cita:* Cambiar la fecha de tu cita.\n"
        "4️⃣ *Cancelar Cita:* Responde *cancelar cita*."
    )
    enviar_botones_interactivos(telefono, texto, botones)