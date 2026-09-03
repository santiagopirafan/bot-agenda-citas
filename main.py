# ==========================================
# IMPORTACIÓN DE MÓDULOS Y LIBRERÍAS
# ==========================================

import procesador 
import database 
import calendar_service 
from config import LINK_DE_PAGO, PRECIO_PRIMERA_CITA
from datetime import datetime, timedelta
import zoneinfo

# Definimos la zona horaria local
ZONA_HORARIA = zoneinfo.ZoneInfo("America/Bogota")


# ==========================================
# FUNCIONES AUXILIARES LOCALES
# ==========================================

def es_fecha_valida(texto):
    """
    Intenta convertir un texto al formato estándar de fecha 'YYYY-MM-DD'.
    """
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def obtener_proximos_dias():
    """
    Genera la lista de todos los días del mes actual a partir de la fecha de hoy,
    excluyendo únicamente los domingos.
    """
    lista_dias = []
    hoy = datetime.now(ZONA_HORARIA)
    mes_actual = hoy.month
    
    dia_iteracion = hoy
    while dia_iteracion.month == mes_actual:
        # Excluir domingos (weekday() == 6)
        if dia_iteracion.weekday() != 6:
            fecha_str = dia_iteracion.strftime("%Y-%m-%d")
            lista_dias.append({
                'fecha_iso': fecha_str,
                'fecha_formateada': fecha_str
            })
        
        # Avanzar 1 día
        dia_iteracion += timedelta(days=1)
            
    return lista_dias


# ==========================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ==========================================

def recibir_mensaje(telefono, texto):
    """
    Función principal que procesa la petición recibida por WhatsApp.
    """
    # 1. Obtenemos el procesamiento del módulo procesador (Manejador de Estados Activos)
    respuesta_procesador = procesador.procesar_mensaje_usuario(telefono, texto)

    # Si el procesador atendió con éxito un estado activo (ej. seleccionando hora o confirmando cita),
    # retornamos de inmediato esa respuesta.
    if respuesta_procesador:
        return respuesta_procesador

    # --- FLUJO SECUNDARIO / EVALUACIONES GENERALES ---
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "opciones", "ayuda"]
    texto_limpio = texto.strip().lower()

    # ------------------------------------------
    # EVALUACIÓN 1: MENÚ PRINCIPAL Y BIENVENIDA
    # ------------------------------------------
    if any(saludo in texto_limpio for saludo in saludos) or texto_limpio == "0":
        hoy_str = datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")
        return (
            "👋 ¡Hola! Bienvenido al sistema de agendamiento de citas médicas.\n\n"
            "¿En qué te puedo ayudar hoy? Escribe el número o palabra de la opción:\n\n"
            "1️⃣ *Agendar o ver disponibilidad:* Responde `1` o `agendar`\n"
            "2️⃣ *Consultar mis citas:* Responde `2` o `mis citas`\n"
            "3️⃣ *Cancelar cita:* Responde `3` o `cancelar`\n\n"
            f"📌 *Para pre-reservar directamente:* Escribe `agendar YYYY-MM-DD HH:MM Nombre`\n"
            f"*(Ejemplo: agendar {hoy_str} 10:00 Carlos Gomez)*"
        )

    # ------------------------------------------
    # EVALUACIÓN 2: AGENDAMIENTO DIRECTO VÍA COMANDO (agendar YYYY-MM-DD HH:MM Nombre)
    # ------------------------------------------
    elif texto_limpio.startswith("agendar "):
        partes = texto.strip().split(" ", 3)
        if len(partes) >= 4:
            _, fecha_input, hora_input, nombre_input = partes
            if es_fecha_valida(fecha_input):
                # Guardar pre-reserva pendiente en SQLite
                if hasattr(database, 'guardar_cita_pendiente'):
                    database.guardar_cita_pendiente(
                        telefono=telefono,
                        paciente=nombre_input,
                        fecha_str=fecha_input,
                        fecha_iso=fecha_input,
                        hora_str=hora_input,
                        hora_iso=hora_input,
                        tipo_cita="Consulta General"
                    )
                else:
                    database.guardar_cita(
                        telefono=telefono,
                        paciente=nombre_input,
                        fecha=fecha_input,
                        hora=hora_input,
                        event_id=None,
                        estado='PENDIENTE'
                    )

                database.guardar_estado_usuario(
                    telefono, 'ESPERANDO_PAGO',
                    {'fecha_str': fecha_input, 'hora_str': hora_input, 'nombre_paciente': nombre_input},
                    nombre=nombre_input
                )

                return (
                    f"✅ *Pre-reserva registrada con éxito.*\n\n"
                    f"👤 *Paciente:* {nombre_input}\n"
                    f"📅 *Fecha:* {fecha_input}\n"
                    f"⏰ *Hora:* {hora_input}\n\n"
                    f"💳 *Para confirmar y agendar tu cita en la agenda, realiza el pago en el siguiente enlace:*\n"
                    f"{LINK_DE_PAGO}\n\n"
                    f"_Una vez confirmado el pago, tu cita se creará automáticamente en la agenda._"
                )

        return "⚠️ Formato de agendamiento directo incorrecto. Usa: `agendar YYYY-MM-DD HH:MM Tu Nombre`"

    # ------------------------------------------
    # EVALUACIÓN 3: PASO 1 - DÍAS DISPONIBLES DEL MES
    # ------------------------------------------
    elif texto_limpio in ["1", "disponibilidad", "consultar disponibilidad", "ver disponibilidad"]:
        dias_disponibles = obtener_proximos_dias() 
        
        if not dias_disponibles:
            return "⚠️ En este momento no hay días con disponibilidad para este mes."

        mensaje_dias = "📅 *Días disponibles para agendar este mes:*\n\n"
        for idx, dia in enumerate(dias_disponibles, 1):
            mensaje_dias += f"• *{dia['fecha_formateada']}*\n"
            
        mensaje_dias += (
            f"\n👉 *Escribe la fecha que prefieres* en formato `YYYY-MM-DD` para ver los horarios libres."
            f"\n*(Ejemplo: `{dias_disponibles[0]['fecha_iso']}`)*"
        )
        return mensaje_dias

    # ------------------------------------------
    # EVALUACIÓN 4: PASO 2 - HORAS DEL DÍA SELECCIONADO
    # ------------------------------------------
    elif es_fecha_valida(texto_limpio):
        fecha_seleccionada = texto_limpio
        
        try:
            libres = calendar_service.obtener_horas_disponibles(fecha_seleccionada)
            if libres:
                horas_texto = "\n".join([f"• *{hora.get('hora_str', hora)}*" for hora in libres])
                hora_ejemplo = libres[0].get('hora_str', '10:00') if isinstance(libres[0], dict) else libres[0]
                return (
                    f"⏰ *Horarios disponibles para el día {fecha_seleccionada}:*\n\n"
                    f"{horas_texto}\n\n"
                    f"📌 Para pre-reservar una de estas horas, responde:\n"
                    f"`agendar {fecha_seleccionada} {hora_ejemplo} Tu Nombre`"
                )
            else:
                return f"⚠️ El día *{fecha_seleccionada}* no tiene horarios disponibles. Intenta consultando otra fecha."
        except Exception as e:
            print(f"[ERROR CALENDAR DISPONIBILIDAD] {e}")
            return "⚠️ Ocurrió un inconveniente al consultar la disponibilidad. Inténtalo de nuevo en unos momentos."

    # ------------------------------------------
    # EVALUACIÓN 5: CONSULTAR CITAS
    # ------------------------------------------
    elif texto_limpio in ["2", "consultar", "mis citas", "consultar cita"]:
        consultar_datos = database.consultar_citas(telefono)

        if not consultar_datos:
            return "No encontré ninguna cita registrada o pagada para este número de teléfono. 🧐"

        estado_cita = consultar_datos.get('estado', 'CONFIRMADA')
        return (
            f"👤 *Paciente:* {consultar_datos.get('paciente')}\n"
            f"📅 *Fecha:* {consultar_datos.get('fecha')}\n"
            f"⏰ *Hora:* {consultar_datos.get('hora')}\n"
            f"📌 *Estado:* {estado_cita}\n\n"
            f"¡Te esperamos!"
        )

    # ------------------------------------------
    # EVALUACIÓN 6: ACCIÓN ELIMINAR / CANCELAR CITA
    # ------------------------------------------
    elif texto_limpio in ["3", "eliminar", "cancelar", "cancelar cita"]:
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