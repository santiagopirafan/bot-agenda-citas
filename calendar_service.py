import os
import json
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
        # Reemplazar posibles saltos de línea mal formateados en Render
        google_json_env = google_json_env.replace('\\n', '\n')
        info = json.loads(google_json_env)
        
        # Corregir la clave privada si los saltos de línea se escaparon doblemente
        if "private_key" in info and isinstance(info["private_key"], str):
            info["private_key"] = info["private_key"].replace('\\n', '\n')

        credenciales = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
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
    horas_ocupadas = [
        e['start'].get('dateTime', '').split('T')[1][:5]
        for e in eventos if 'dateTime' in e['start']
    ]

    jornada = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
    horas_libres = []

    for hora in jornada:
        if hora not in horas_ocupadas:
            horas_libres.append({
                'hora_iso': hora,
                'hora_str': f"{hora} AM" if int(hora[:2]) < 12 else f"{int(hora[:2])-12 if int(hora[:2]) > 12 else 12}:00 PM"
            })
            
    return horas_libres


def agendar_cita(resumen, fecha, hora_inicio, duracion_minutos=30, descripcion=""):
    """
    Crea el evento en Google Calendar y retorna el event_id creado (o None si falla).
    """
    try:
        servicio = obtener_servicio()
        inicio_dt = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)

        evento = {
            'summary': resumen,
            'description': descripcion,
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
    except Exception as e:
        print(f"Error agendando cita: {e}")
        return None


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