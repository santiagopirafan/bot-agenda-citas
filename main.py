# ==========================================
# IMPORTACIÓN DE MÓDULOS Y LIBRERÍAS
# ==========================================

import procesador 
import database 
import calendar_service 
from datetime import datetime, timedelta
import zoneinfo  # Librería nativa de Python 3.9+ para zonas horarias

# Definimos la zona horaria local
ZONA_HORARIA = zoneinfo.ZoneInfo("America/Bogota")


# ==========================================
# FUNCIONES AUXILIARES LOCALES
# ==========================================

def es_fecha_valida(texto):
    """
    Función que intenta convertir un texto al formato estándar de fecha 'YYYY-MM-DD'.
    """
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def obtener_proximos_dias(dias=5):
    """
    Genera la lista de próximos días hábiles usando la zona horaria correcta.
    """
    lista_dias = []
    hoy = datetime.now(ZONA_HORARIA)
    
    i = 1
    while len(lista_dias) < dias:
        dia_futuro = hoy + timedelta(days=i)
        
        # Excluimos domingos (weekday() == 6)
        if dia_futuro.weekday() != 6:
            nombre_dia = dia_futuro.strftime("%Y-%m-%d")
            lista_dias.append({
                'fecha_iso': nombre_dia,
                'fecha_formateada': nombre_dia
            })
        i += 1
        
    return lista_dias


# ==========================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ==========================================

def recibir_mensaje(telefono, texto):
    """
    Función principal que procesa la petición recibida por WhatsApp.
    """
    datos_procesados = procesador.procesar_mensaje_usuario(texto)
    accion = datos_procesados.get("accion") if datos_procesados else None

    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "opciones", "ayuda"]
    texto_limpio = texto.strip().lower()


    # ------------------------------------------
    # EVALUACIÓN 1: MENÚ PRINCIPAL
    # ------------------------------------------
    if any(saludo in texto_limpio for saludo in saludos) or accion == "menu":
        hoy_str = datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")
        return (
            "👋 ¡Hola! Bienvenido al sistema de agendamiento de citas médicas.\n\n"
            "¿En qué te puedo ayudar hoy? Escribe la opción que desees:\n\n"
            "1️⃣ *Consultar disponibilidad:* Escribe `disponibilidad`\n\n"
            f"2️⃣ *Agendar cita:* Escribe `agendar YYYY-MM-DD HH:MM Nombre` (Ej: `agendar {hoy_str} 10:00 Carlos Gomez`)\n\n"
            "3️⃣ *Consultar mis citas:* Escribe `mis citas` o `consultar`\n\n"
            "4️⃣ *Cancelar cita:* Escribe `cancelar`\n\n"
            "Escribe una de las opciones para comenzar."
        )


    # ------------------------------------------
    # EVALUACIÓN 2: PASO 1 - DÍAS DISPONIBLES
    # ------------------------------------------
    elif texto_limpio in ["1", "disponibilidad", "consultar disponibilidad", "ver disponibilidad"] or accion == "disponibilidad":
        dias_disponibles = obtener_proximos_dias(dias=5) 
        
        if not dias_disponibles:
            return "⚠️ En este momento no hay días con disponibilidad próxima."

        mensaje_dias = "📅 *Días disponibles para agendar:*\n\n"
        for idx, dia in enumerate(dias_disponibles, 1):
            mensaje_dias += f"{idx}️⃣ *{dia['fecha_formateada']}* (Escribe: `{dia['fecha_iso']}`)\n"
            
        mensaje_dias += f"\n👉 *Escribe la fecha del día que prefieres* para ver sus horarios (Ej: `{dias_disponibles[0]['fecha_iso']}`)."
        return mensaje_dias


    # ------------------------------------------
    # EVALUACIÓN 3: PASO 2 - HORAS DEL DÍA
    # ------------------------------------------
    elif es_fecha_valida(texto_limpio):
        fecha_seleccionada = texto_limpio
        
        try:
            libres = calendar_service.obtener_horarios_disponibles(fecha_seleccionada)
            if libres:
                horas_texto = "\n".join([f"• *{hora}*" for hora in libres])
                return (
                    f"⏰ *Horarios disponibles para el día {fecha_seleccionada}:*\n\n"
                    f"{horas_texto}\n\n"
                    f"📌 Para agendar una de estas horas, responde:\n"
                    f"`agendar {fecha_seleccionada} HH:MM Tu Nombre`\n"
                    f"*(Ejemplo: agendar {fecha_seleccionada} {libres[0]} Carlos Gomez)*"
                )
            else:
                return f"⚠️ El día *{fecha_seleccionada}* no tiene horarios disponibles. Intenta consultando otra fecha."
        except Exception as e:
            print(f"[ERROR CALENDAR DISPONIBILIDAD] {e}")
            return "⚠️ Ocurrió un inconveniente al consultar Google Calendar. Inténtalo de nuevo en unos momentos."


    # ------------------------------------------
    # EVALUACIÓN 4: ACCIÓN AGENDAR CITA
    # ------------------------------------------
    elif accion == "agendar":
        datos_cita = procesador.extraer_datos_cita(texto)

        if not datos_cita.get("valido"):
            return datos_cita.get("error")

        try:
            if not calendar_service.esta_disponible(datos_cita['fecha'], datos_cita['hora']):
                libres = calendar_service.obtener_horarios_disponibles(datos_cita['fecha'])
                if libres:
                    horas_texto = ", ".join(libres)
                    return (
                        f"⚠️ El horario de las *{datos_cita['hora']}* para el día *{datos_cita['fecha']}* ya está ocupado.\n\n"
                        f"📅 *Horarios disponibles para ese día:*\n{horas_texto}\n\n"
                        f"Por favor, intenta agendar escribiendo una de estas horas disponibles."
                    )
                else:
                    return f"⚠️ El día *{datos_cita['fecha']}* ya no tiene horarios disponibles."

            id_event = calendar_service.crear_evento_calendar(
                paciente=datos_cita['paciente'],
                fecha_str=datos_cita['fecha'],
                hora_str=datos_cita['hora']
            )

            database.guardar_cita(
                telefono,
                datos_cita['paciente'],
                datos_cita['fecha'],
                datos_cita['hora'],
                id_event
            )

            return f"¡Cita agendada con éxito para {datos_cita['paciente']} el {datos_cita['fecha']} a las {datos_cita['hora']}! 🎉"
        except Exception as e:
            print(f"[ERROR CREAR CITA] {e}")
            return "⚠️ Ocurrió un error al agendar la cita. Por favor intenta de nuevo."


    # ------------------------------------------
    # EVALUACIÓN 5: ACCIÓN CONSULTAR CITAS
    # ------------------------------------------
    elif accion == "consultar":
        consultar_datos = database.consultar_citas(telefono)

        if not consultar_datos:
            return "No encontré ninguna cita registrada para este número de teléfono. 🧐"

        return (
            f"¡Cita registrada, {consultar_datos['paciente']}! 🎉\n\n"
            f"📅 *Fecha:* {consultar_datos['fecha']}\n"
            f"⏰ *Hora:* {consultar_datos['hora']}\n\n"
            f"Te esperamos a la hora agendada."
        )


    # ------------------------------------------
    # EVALUACIÓN 6: ACCIÓN ELIMINAR / CANCELAR CITA
    # ------------------------------------------
    elif accion == "eliminar" or accion == "cancelar":
        datos = database.consultar_citas(telefono)

        if not datos:
            return "No encontré ninguna cita registrada para este número de teléfono. 🧐"

        event_id = datos.get('event_id') or datos.get('id_event')
        if event_id:
            try:
                calendar_service.eliminar_evento(event_id)
            except Exception as e:
                print(f"[ERROR ELIMINAR CALENDAR] {e}")

        database.eliminar_cita(telefono)

        return (
            "Tu cita ha sido cancelada exitosamente. ❌\n\n"
            "El espacio en la agenda ha sido liberado. Cuando desees volver a agendar, solo escríbeme."
        )


    # ------------------------------------------
    # EVALUACIÓN 7: RESPUESTA POR DEFECTO (FALLBACK)
    # ------------------------------------------
    else:
        return "⚠️ No entendí esa opción. Escribe *Hola* o *Menu* para ver las opciones disponibles."