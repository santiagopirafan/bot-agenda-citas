import os
import json
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 1. Definimos los permisos (Scopes): Leer y escribir en Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# 2. Configuración de ID de Calendario centralizado
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "santipirafan1@gmail.com")
CREDENTIALS_FILE = 'credentials.json'

def obtener_servicio():
    """
    Carga credenciales desde archivo local 'credentials.json' 
    o desde la variable de entorno GOOGLE_CREDENTIALS_JSON (ideal para Render).
    """
    google_json_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if google_json_env:
        # Si se configura en Render como variable de entorno tipo JSON
        info = json.loads(google_json_env)
        credenciales = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif os.path.exists(CREDENTIALS_FILE):
        # Si existe el archivo físico credentials.json localmente
        credenciales = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
    else:
        raise FileNotFoundError("No se encontraron las credenciales de Google Calendar (credentials.json o GOOGLE_CREDENTIALS_JSON).")

    servicio = build('calendar', 'v3', credentials=credenciales)
    return servicio


def crear_evento_calendar(paciente, fecha_str, hora_str, duracion_minutos=30):
    servicio = obtener_servicio()

    inicio_dt = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
    fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)

    evento = {
        'summary': f'Cita Médica - {paciente}',
        'description': f'Cita médica agendada para {paciente}',
        'start': {
            'dateTime': inicio_dt.isoformat(),
            'timeZone': 'America/Bogota',
        },
        'end': {
            'dateTime': fin_dt.isoformat(),
            'timeZone': 'America/Bogota',
        },
    }

    evento_creado = servicio.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
    return evento_creado.get('id')


def eliminar_evento(event_id):
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


def esta_disponible(fecha_str, hora_str, duracion_minutos=30):
    """
    Verifica si hay un evento agendado en la fecha y hora indicadas.
    """
    servicio = obtener_servicio()
    
    inicio_dt = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
    fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)

    inicio_iso = inicio_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    fin_iso = fin_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")

    eventos_result = servicio.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio_iso,
        timeMax=fin_iso,
        singleEvents=True,
        timeZone='America/Bogota'
    ).execute()

    eventos = eventos_result.get('items', [])
    return len(eventos) == 0


def obtener_horarios_disponibles(fecha_str):
    """
    Revisa los eventos de Google Calendar para una fecha y devuelve 
    las horas libres dentro de la jornada laboral (8:00 a 17:00).
    """
    servicio = obtener_servicio()
    
    inicio_dia = f"{fecha_str}T08:00:00-05:00"
    fin_dia = f"{fecha_str}T17:00:00-05:00"

    eventos_result = servicio.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio_dia,
        timeMax=fin_dia,
        singleEvents=True,
        orderBy='startTime',
        timeZone='America/Bogota'
    ).execute()

    eventos = eventos_result.get('items', [])
    
    horas_ocupadas = []
    for evento in eventos:
        start = evento['start'].get('dateTime', '')
        if start:
            hora = start.split('T')[1][:5]
            horas_ocupadas.append(hora)

    jornada = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
    horas_libres = [h for h in jornada if h not in horas_ocupadas]
    
    return horas_libres