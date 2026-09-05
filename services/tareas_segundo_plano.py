import time
import re
from datetime import datetime, timedelta
from services.calendar_service import obtener_servicio, CALENDAR_ID, ZONA_HORARIA
from services.whatsapp_service import enviar_mensaje_texto

def escanear_calendario_continuamente():
    """
    Se ejecuta en segundo plano. Busca eventos futuros con un celular (57...)
    en la descripción, envía confirmación y etiqueta el evento.
    """
    print("[BACKGROUND] Hilo de escaneo en segundo plano INICIADO.")
    
    while True:
        try:
            servicio = obtener_servicio()
            ahora = datetime.now(ZONA_HORARIA)
            inicio_iso = ahora.isoformat()
            
            # Consultar eventos desde hoy hasta 30 días en el futuro
            fin_iso = (ahora + timedelta(days=30)).isoformat()
            
            events_result = servicio.events().list(
                calendarId=CALENDAR_ID,
                timeMin=inicio_iso,
                timeMax=fin_iso,
                singleEvents=True,
                orderBy='startTime',
                timeZone='America/Bogota'
            ).execute()

            eventos = events_result.get('items', [])

            for evento in eventos:
                descripcion = evento.get('description', '')
                
                # Ignorar si ya se notificó o si fue creado automáticamente por el bot
                if '[NOTIFICADO]' in descripcion or 'Enlace de la videollamada' in descripcion:
                    continue

                # Extraer el número de teléfono (57 seguido de 10 dígitos)
                match = re.search(r'(57\d{10})', descripcion)
                if match:
                    numero_paciente = match.group(1)
                    titulo = evento.get('summary', 'tu cita')
                    inicio = evento['start'].get('dateTime', evento['start'].get('date', ''))
                    fecha_corta = inicio[:10]

                    print(f"[BACKGROUND] Cita manual detectada para {numero_paciente}. Enviando mensaje...")

                    mensaje = f"✅ *Cita Confirmada*\nHola, confirmamos el agendamiento de: *{titulo}* para la fecha {fecha_corta}."
                    enviar_mensaje_texto(numero_paciente, mensaje)

                    # Etiquetar el evento para evitar doble envío
                    nueva_descripcion = f"{descripcion}\n\n[NOTIFICADO]".strip()
                    evento['description'] = nueva_descripcion
                    
                    servicio.events().update(
                        calendarId=CALENDAR_ID,
                        eventId=evento['id'],
                        body=evento
                    ).execute()
                    print(f"[BACKGROUND] Notificación enviada con éxito a {numero_paciente} y evento etiquetado.")

        except Exception as e:
            print(f"[ERROR BACKGROUND] {e}")
        
        # Pausa de 30 segundos entre escaneos
        time.sleep(30)