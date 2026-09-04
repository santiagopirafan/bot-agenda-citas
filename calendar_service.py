import os
import json
import uuid
import zoneinfo
import calendar
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "santipirafan1@gmail.com")
CREDENTIALS_FILE = 'credentials.json'
ZONA_HORARIA = zoneinfo.ZoneInfo("America/Bogota")


def obtener_servicio():
    google_json_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if google_json_env:
        try:
            # 1. Limpieza inicial de comillas adicionales y saltos de línea
            google_json_env = google_json_env.strip()
            if (google_json_env.startswith('"') and google_json_env.endswith('"')) or \
               (google_json_env.startswith("'") and google_json_env.endswith("'")):
                google_json_env = google_json_env[1:-1]

            # 2. Reemplazo de saltos de línea escapados
            google_json_env = google_json_env.replace('\\n', '\n')

            # 3. Parseo con strict=False para tolerar caracteres de control
            info = json.loads(google_json_env, strict=False)
            
            # 4. Asegurar formato PEM correcto en private_key
            if "private_key" in info and isinstance(info["private_key"], str):
                info["private_key"] = info["private_key"].replace('\\n', '\n')

            credenciales = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            print(f"[ERROR PARSING GOOGLE CREDENTIALS] {e}")
            raise e
    elif os.path.exists(CREDENTIALS_FILE):
        credenciales = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
    else:
        raise FileNotFoundError("No se encontraron las credenciales de Google Calendar.")

    return build('calendar', 'v3', credentials=credenciales)


def obtener_dias_disponibles():
    """
    Genera la lista de todos los días del mes actual a partir de hoy,
    excluyendo únicamente los domingos (weekday 6).
    """
    dias = []
    hoy = datetime.now(ZONA_HORARIA)
    mes_actual = hoy.month
    
    dia_iteracion = hoy
    while dia_iteracion.month == mes_actual:
        # Excluir domingos (weekday() == 6)
        if dia_iteracion.weekday() != 6:
            dias.append({
                'fecha_iso': dia_iteracion.strftime("%Y-%m-%d"),
                'fecha_str': dia_iteracion.strftime("%d/%m/%Y")
            })
        
        # Avanzar 1 día
        dia_iteracion += timedelta(days=1)

    return dias


def obtener_horas_disponibles(fecha_str):
    """
    Consulta los eventos ocupados en Calendar y devuelve los horarios libres formateados.
    Jornada extendida: 06:00 AM a 07:00 PM (19:00) de corrido.
    """
    servicio = obtener_servicio()
    
    inicio_dia = f"{fecha_str}T06:00:00-05:00"
    fin_dia = f"{fecha_str}T20:00:00-05:00"

    eventos_result = servicio.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio_dia,
        timeMax=fin_dia,
        singleEvents=True,
        orderBy='startTime',
        timeZone='America/Bogota'
    ).execute()

    eventos = eventos_result.get('items', [])
    horas_ocupadas = [
        e['start'].get('dateTime', '').split('T')[1][:5]
        for e in eventos if 'dateTime' in e['start']
    ]

    # Jornada extendida de 06:00 AM a 07:00 PM (19:00)
    jornada = [
        "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", 
        "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"
    ]
    
    horas_libres = []

    for hora in jornada:
        if hora not in horas_ocupadas:
            hora_num = int(hora[:2])
            
            # Formateo amigable AM/PM
            if hora_num < 12:
                hora_str = f"{hora_num:02d}:00 AM"
            elif hora_num == 12:
                hora_str = "12:00 PM"
            else:
                hora_str = f"{hora_num - 12:02d}:00 PM"

            horas_libres.append({
                'hora_iso': hora,
                'hora_str': hora_str
            })
            
    return horas_libres


def agendar_cita(resumen, fecha, hora_inicio, duracion_minutos=30, descripcion=""):
    """
    Crea el evento en Google Calendar y genera el enlace de Google Meet.
    Retorna una tupla: (event_id, meet_link).
    """
    servicio = obtener_servicio()

    # 1. Limpieza de fecha y hora
    fecha_clean = str(fecha).split('T')[0].strip()
    
    # Extraer solo HH:MM si viene en formato "09:00" o "09:00:00"
    hora_clean = str(hora_inicio).strip().split(' ')[0]
    if len(hora_clean.split(':')) > 2:
        hora_clean = ":".join(hora_clean.split(':')[:2])

    try:
        inicio_dt = datetime.strptime(f"{fecha_clean} {hora_clean}", "%Y-%m-%d %H:%M")
    except Exception as err_parse:
        print(f"[ERROR PARSEO FECHA/HORA] No se pudo parsear fecha='{fecha}' hora='{hora_inicio}': {err_parse}")
        return None, None

    fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)

    base_evento = {
        'summary': resumen,
        'description': descripcion,
        'start': {
            'dateTime': inicio_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00"),
            'timeZone': 'America/Bogota',
        },
        'end': {
            'dateTime': fin_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00"),
            'timeZone': 'America/Bogota',
        }
    }

    # 2. Intentar crear evento con Google Meet
    try:
        evento_con_meet = base_evento.copy()
        evento_con_meet['conferenceData'] = {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {
                    'type': 'addOn'
                }
            }
        }

        evento_creado = servicio.events().insert(
            calendarId=CALENDAR_ID, 
            body=evento_con_meet,
            conferenceDataVersion=1
        ).execute()

        event_id = evento_creado.get('id')
        
        # Extraer enlace de Meet
        meet_link = evento_creado.get('hangoutLink')
        if not meet_link:
            entry_points = evento_creado.get('conferenceData', {}).get('entryPoints', [])
            for ep in entry_points:
                if ep.get('entryPointType') == 'video':
                    meet_link = ep.get('uri')
                    break

        print(f"[CALENDAR SUCCESS] Evento creado con ID: {event_id} | Meet: {meet_link}")
        return event_id, meet_link

    except Exception as err:
        print(f"[WARN MEET] Error al adjuntar Meet ({err}). Creando evento simple...")
        try:
            evento_creado = servicio.events().insert(
                calendarId=CALENDAR_ID, 
                body=base_evento
            ).execute()
            
            print(f"[CALENDAR SUCCESS] Evento simple creado con ID: {evento_creado.get('id')}")
            return evento_creado.get('id'), None
        except Exception as e_simple:
            print(f"[ERROR CRÍTICO CALENDAR] No se pudo crear ni el evento simple: {e_simple}")
            return None, None


def eliminar_evento(event_id):
    """
    Elimina un evento de Google Calendar mediante su ID.
    """
    servicio = obtener_servicio()
    try:
        servicio.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status in [404, 410]:
            return True
        raise e