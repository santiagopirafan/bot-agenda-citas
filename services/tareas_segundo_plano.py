import time
import re
from datetime import datetime
import database
from services.calendar_service import buscar_citas_manuales_nuevas
from services.whatsapp_service import enviar_mensaje_texto

INTERVALO_ESCANEO_SEGUNDOS = 30

def extraer_telefono_descripcion(descripcion):
    """
    Busca un número telefónico celular colombiano dentro de la descripción del evento.
    Soporta formatos: 3147867948, 573147867948, +57 314 786 7948, etc.
    """
    if not descripcion:
        return None

    # Elimina caracteres que no sean dígitos
    solo_numeros = re.sub(r'[^\d]', '', descripcion)

    # Busca número celular de 10 dígitos (3XX...) o con prefijo 57 (573XX...)
    coincidencia = re.search(r'(573\d{9}|3\d{9})', solo_numeros)
    
    if coincidencia:
        numero = coincidencia.group(1)
        if not numero.startswith('57'):
            numero = f"57{numero}"
        return numero
    
    return None

def formatear_fecha_legible(fecha_iso):
    """Convierte fecha YYYY-MM-DD a DD/MM/YYYY"""
    if not fecha_iso:
        return ""
    try:
        fecha_dt = datetime.strptime(fecha_iso[:10], '%Y-%m-%d')
        return fecha_dt.strftime('%d/%m/%Y')
    except Exception:
        return fecha_iso[:10]

def escanear_eventos_y_notificar():
    """
    Lee Google Calendar en búsqueda de eventos asignados manualmente y
    notifica vía WhatsApp utilizando Meta Cloud API.
    """
    try:
        eventos = buscar_citas_manuales_nuevas()
        
        for evento in eventos:
            event_id = evento.get('id')
            titulo = evento.get('summary', 'Cita Médica')
            descripcion = evento.get('description', '')
            
            # Si la cita ya fue notificada previamente, se ignora
            if database.evento_ya_notificado(event_id):
                continue

            # Extraer teléfono del paciente desde la descripción/notas
            telefono = extraer_telefono_descripcion(descripcion)
            if not telefono:
                continue

            # Formatear Fecha y Hora
            inicio_info = evento.get('start', {})
            fecha_raw = inicio_info.get('dateTime', inicio_info.get('date', ''))
            
            fecha_corta = formatear_fecha_legible(fecha_raw)
            hora_corta = ""
            if 'T' in fecha_raw:
                hora_corta = fecha_raw.split('T')[1][:5]

            # Construir mensaje oficial para el paciente
            mensaje = (
                f"👋 ¡Hola! Te confirmamos tu cita médica.\n\n"
                f"📌 *Paciente / Detalle:* {titulo}\n"
                f"📅 *Fecha:* {fecha_corta}\n"
                f"⏰ *Hora:* {hora_corta}\n\n"
                f"Por favor estar atento(a) unos minutos antes de tu hora agendada."
            )

            print(f"[BACKGROUND] Enviando WhatsApp a {telefono} por evento: {event_id}")

            # Envío de WhatsApp a través de la API oficial de Meta
            respuesta = enviar_mensaje_texto(telefono, mensaje)

            if respuesta and 'messages' in respuesta:
                database.registrar_notificacion(
                    event_id=event_id,
                    telefono=telefono,
                    paciente_nombre=titulo,
                    fecha_cita=fecha_corta,
                    hora_cita=hora_corta,
                    estado="ENVIADO",
                    respuesta_manychat=str(respuesta)
                )
                print(f"[BACKGROUND SUCCESS] Mensaje WhatsApp enviado a {telefono}")
            else:
                database.registrar_notificacion(
                    event_id=event_id,
                    telefono=telefono,
                    paciente_nombre=titulo,
                    fecha_cita=fecha_corta,
                    hora_cita=hora_corta,
                    estado="ERROR",
                    respuesta_manychat=str(respuesta)
                )
                print(f"[BACKGROUND ERROR] Error al enviar WhatsApp a {telefono}: {respuesta}")

    except Exception as e:
        print(f"[BACKGROUND ERROR] Error en ciclo de escaneo: {e}")

def escanear_calendario_continuamente():
    """Bucle que se ejecuta en segundo plano cada 30 segundos"""
    print("[BACKGROUND] Escáner automático de Google Calendar en segundo plano ACTIVO.")
    while True:
        try:
            escanear_eventos_y_notificar()
        except Exception as e:
            print(f"[BACKGROUND ERROR] Excepción inesperada: {e}")
        
        time.sleep(INTERVALO_ESCANEO_SEGUNDOS)