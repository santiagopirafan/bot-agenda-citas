# ==========================================
# IMPORTACIÓN DE MÓDULOS Y LIBRERÍAS
# ==========================================

# Importamos 'procesador' para interpretar el texto del usuario y extraer intenciones o datos de citas
import procesador 

# Importamos 'database' para interactuar con la base de datos local SQLite (guardar, consultar o eliminar)
import database 

# Importamos 'calendar_service' para conectar con Google Calendar y consultar/crear/eliminar eventos reales
import calendar_service 

# Importamos 'datetime' y 'timedelta' de la librería nativa de Python para manejar fechas, horas y cálculos de días
from datetime import datetime, timedelta


# ==========================================
# FUNCIONES AUXILIARES LOCALES
# ==========================================

def es_fecha_valida(texto):
    """
    Función que intenta convertir un texto al formato estándar de fecha 'YYYY-MM-DD'.
    Sirve para saber si el usuario escribió una fecha para consultar sus horas.
    """
    try:
        # Se intenta parsear el texto con la máscara Año-Mes-Día
        datetime.strptime(texto, "%Y-%m-%d")
        # Si no genera error, la fecha es totalmente válida
        return True
    except ValueError:
        # Si el texto no cumple el formato (ej: 'hola' o '10/09'), retorna False
        return False


def obtener_proximos_dias(dias=5):
    """
    Función que genera una lista con los próximos días a partir de la fecha actual.
    Construye la lista de días disponibles para mostrarle al paciente.
    """
    # Lista vacía donde guardaremos las fechas encontradas
    lista_dias = []
    
    # 'hoy' guarda la fecha y hora exacta del momento de la consulta
    hoy = datetime.now()
    
    # Contador de días que sumaremos a la fecha actual
    i = 1
    
    # Bucle que continúa hasta recolectar la cantidad de días solicitados (por defecto 5)
    while len(lista_dias) < dias:
        # 'dia_futuro' calcula la fecha sumando 'i' días a la fecha actual
        dia_futuro = hoy + timedelta(days=i)
        
        # 'weekday() == 6' representa el Domingo. Si no es domingo, agregamos el día (puedes ajustar esta regla)
        if dia_futuro.weekday() != 6:
            # Formateamos la fecha en texto con estándar ISO 'YYYY-MM-DD'
            nombre_dia = dia_futuro.strftime("%Y-%m-%d")
            
            # Guardamos el diccionario con la fecha para enviarlo al flujo de respuesta
            lista_dias.append({
                'fecha_iso': nombre_dia,
                'fecha_formateada': nombre_dia
            })
            
        # Incrementamos el contador para evaluar el siguiente día del calendario
        i += 1
        
    # Retornamos la lista final con los días calculados
    return lista_dias


# ==========================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ==========================================

def recibir_mensaje(telefono, texto):
    """
    Función principal que procesa la petición recibida por WhatsApp,
    evalúa las condicionales de negocio y retorna la respuesta para el usuario.
    """

    # 'datos_procesados' llama al procesador de texto para identificar la intención principal
    datos_procesados = procesador.procesar_opcion_menu(texto)

    # 'accion' extrae la clave (ej: "agendar", "consultar", "eliminar", "menu") devuelta por el procesador
    accion = datos_procesados.get("accion") if datos_procesados else None

    # Lista de palabras de saludo para activar automáticamente el menú principal si el paciente saluda
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "opciones", "ayuda"]

    # 'texto_limpio' remueve espacios adicionales a los lados y convierte a minúsculas para comparaciones uniformes
    texto_limpio = texto.strip().lower()


    # ------------------------------------------
    # EVALUACIÓN 1: MENÚ PRINCIPAL
    # ------------------------------------------
    # Se evalúa si el texto contiene un saludo conocido O si el procesador clasificó el mensaje como "menu"
    if any(saludo in texto_limpio for saludo in saludos) or accion == "menu":
        # Retorna el texto con las instrucciones y formato con viñetas para que el usuario elija
        return (
            "👋 ¡Hola! Bienvenido al sistema de agendamiento de citas médicas.\n\n"
            "¿En qué te puedo ayudar hoy? Escribe la opción que desees:\n\n"
            "1️⃣ *Consultar disponibilidad:* Escribe `disponibilidad`\n\n"
            "2️⃣ *Agendar cita:* Escribe `agendar YYYY-MM-DD HH:MM Nombre` (Ej: `agendar 2026-09-10 10:00 Carlos Gomez`)\n\n"
            "3️⃣ *Consultar mis citas:* Escribe `mis citas` o `consultar`\n\n"
            "4️⃣ *Cancelar cita:* Escribe `cancelar YYYY-MM-DD HH:MM` (Ej: `cancelar 2026-09-10 10:00`)\n\n"
            "Escribe una de las opciones para comenzar."
        )


    # ------------------------------------------
    # EVALUACIÓN 2: PASO 1 - DÍAS DISPONIBLES
    # ------------------------------------------
    # Se evalúa si el usuario seleccionó la opción 1 o escribió solicitudes de disponibilidad
    elif texto_limpio in ["1", "disponibilidad", "consultar disponibilidad", "ver disponibilidad"] or accion == "disponibilidad":
        
        # 'dias_disponibles' invoca la función auxiliar local para obtener los próximos 5 días hábiles
        dias_disponibles = obtener_proximos_dias(dias=5) 
        
        # Si por alguna razón la lista regresa vacía, se notifica al usuario
        if not dias_disponibles:
            return "⚠️ En este momento no hay días con disponibilidad próxima."

        # Cadena inicial para estructurar el mensaje formateado de la lista de días
        mensaje_dias = "📅 *Días disponibles para agendar:*\n\n"
        
        # Iteramos los días obtenidos asignándole un número de lista a cada uno
        for idx, dia in enumerate(dias_disponibles, 1):
            mensaje_dias += f"{idx}️⃣ *{dia['fecha_formateada']}* (Escribe: `{dia['fecha_iso']}`)\n"
            
        # Agregamos el llamado a la acción para indicarle al paciente el siguiente paso
        mensaje_dias += "\n👉 *Escribe la fecha del día que prefieres* para ver sus horarios (Ej: `2026-09-10`)."
        
        # Retornamos el listado de días generado
        return mensaje_dias


    # ------------------------------------------
    # EVALUACIÓN 3: PASO 2 - HORAS DEL DÍA
    # ------------------------------------------
    # Se evalúa si el texto ingresado por el usuario corresponde a una fecha válida (YYYY-MM-DD)
    elif es_fecha_valida(texto_limpio):
        
        # Guardamos la fecha reconocida en 'fecha_seleccionada'
        fecha_seleccionada = texto_limpio
        
        # 'libres' consulta en Google Calendar los huecos/horarios disponibles para esa fecha en específico
        libres = calendar_service.obtener_horarios_disponibles(fecha_seleccionada)
        
        # Si existen horas libres devueltas por Google Calendar
        if libres:
            # Formateamos cada hora disponible en una viñeta con salto de línea
            horas_texto = "\n".join([f"• *{hora}*" for hora in libres])
            
            # Retornamos las horas disponibles y el comando exacto para que el paciente proceda a agendar
            return (
                f"⏰ *Horarios disponibles para el día {fecha_seleccionada}:*\n\n"
                f"{horas_texto}\n\n"
                f"📌 Para agendar una de estas horas, responde:\n"
                f"`agendar {fecha_seleccionada} HH:MM Tu Nombre`\n"
                f"*(Ejemplo: agendar {fecha_seleccionada} {libres[0]} Carlos Gomez)*"
            )
        else:
            # Si no hay horas disponibles para esa fecha, se le informa al paciente
            return f"⚠️ El día *{fecha_seleccionada}* no tiene horarios disponibles. Intenta consultando otra fecha."


    # ------------------------------------------
    # EVALUACIÓN 4: ACCIÓN AGENDAR CITA
    # ------------------------------------------
    # Se evalúa si la intención clasificada por el procesador es la de agendar una cita
    elif accion == "agendar":
        
        # 'datos_cita' extrae paciente, fecha y hora mediante las expresiones regulares del módulo procesador
        datos_cita = procesador.extraer_datos_cita(texto)

        # Si no viene con la estructura correcta (ej: falta la hora o el nombre), devuelve el mensaje de error del procesador
        if not datos_cita.get("valido"):
            return datos_cita.get("error")

        # PASO A: Se valida directamente en Google Calendar si la hora puntual solicitada está libre
        if not calendar_service.esta_disponible(datos_cita['fecha'], datos_cita['hora']):
            
            # Si el horario ya está ocupado, traemos los otros horarios libres del mismo día
            libres = calendar_service.obtener_horarios_disponibles(datos_cita['fecha'])
            
            if libres:
                # Unimos los horarios libres con comas
                horas_texto = ", ".join(libres)
                # Informamos la ocupación y mostramos las alternativas disponibles
                return (
                    f"⚠️ El horario de las *{datos_cita['hora']}* para el día *{datos_cita['fecha']}* ya está ocupado.\n\n"
                    f"📅 *Horarios disponibles para ese día:*\n{horas_texto}\n\n"
                    f"Por favor, intenta agendar escribiendo una de estas horas disponibles."
                )
            else:
                return f"⚠️ El día *{datos_cita['fecha']}* ya no tiene horarios disponibles."

        # PASO B: Si la hora está libre, se crea el evento en el calendario de Google
        id_event = calendar_service.crear_evento_calendar(
            paciente=datos_cita['paciente'],
            fecha_str=datos_cita['fecha'],
            hora_str=datos_cita['hora']
        )

        # PASO C: Se guarda la cita en la base de datos local SQLite asignada al número de teléfono
        database.guardar_cita(
            telefono,
            datos_cita['paciente'],
            datos_cita['fecha'],
            datos_cita['hora'],
            id_event
        )

        # Se retorna el mensaje de confirmación exitosa del agendamiento
        return f"¡Cita agendada con éxito para {datos_cita['paciente']} el {datos_cita['fecha']} a las {datos_cita['hora']}! 🎉"


    # ------------------------------------------
    # EVALUACIÓN 5: ACCIÓN CONSULTAR CITAS
    # ------------------------------------------
    # Se evalúa si la intención clasificada por el procesador es consultar citas existentes
    elif accion == "consultar":
        
        # 'consultar_datos' busca en la base de datos SQLite el registro de cita ligado a este número
        consultar_datos = database.consultar_citas(telefono)

        # Si no existe ninguna cita agendada en la base de datos para este teléfono
        if not consultar_datos:
            return "No encontré ninguna cita registrada para este número de teléfono. 🧐"

        # Si se encuentra la cita, se retorna la información con fecha, hora y paciente
        return (
            f"¡Cita agendada con éxito, {consultar_datos['paciente']}! 🎉\n\n"
            f"📅 *Fecha:* {consultar_datos['fecha']}\n"
            f"⏰ *Hora:* {consultar_datos['hora']}\n\n"
            f"Te hemos enviado la confirmación a tu agenda. ¡Te esperamos!"
        )


    # ------------------------------------------
    # EVALUACIÓN 6: ACCIÓN ELIMINAR / CANCELAR CITA
    # ------------------------------------------
    # Se evalúa si la intención clasificada por el procesador es cancelar o eliminar la cita
    elif accion == "eliminar" or accion == "cancelar":
        
        # Consultamos primero la cita en SQLite para obtener el 'event_id' guardado de Google Calendar
        datos = database.consultar_citas(telefono)

        # Si no existe cita previa para cancelar, notificamos al usuario
        if not datos:
            return "No encontré ninguna cita registrada para este número de teléfono. 🧐"

        # Eliminamos la cita de Google Calendar mediante su ID único de evento
        calendar_service.eliminar_evento(datos['event_id'])

        # Eliminamos la cita de la base de datos local SQLite
        database.eliminar_cita(telefono)

        # Confirmamos la cancelación y liberación del espacio en la agenda
        return (
            "Tu cita ha sido cancelada exitosamente. ❌\n\n"
            "El espacio en la agenda ha sido liberado. Cuando desees volver a agendar, solo escríbeme. ¡Que tengas un excelente día! ✨"
        )


    # ------------------------------------------
    # EVALUACIÓN 7: RESPUESTA POR DEFECTO (FALLBACK)
    # ------------------------------------------
    # Si la petición del usuario no coincidió con ninguna condicional previa, evita que el bot se quede en silencio
    else:
        return "⚠️ No entendí esa opción. Escribe *Hola* o *Menu* para ver las opciones disponibles."

