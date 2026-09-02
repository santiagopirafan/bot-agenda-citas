from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 1. Definimos los permisos (Scopes): Leer y escribir en Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# 2. Ruta a tu archivo de llaves secretas
CREDENTIALS_FILE = 'credentials.json'

def obtener_servicio():
    # Carga la llave privada desde tu archivo local
    credenciales = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    
    # Construye el cliente HTTP para interactuar con la API v3 de Calendar
    servicio = build('calendar', 'v3', credentials=credenciales)
    return servicio


# --- PASO 2: Función para formatear e insertar el evento ---
def crear_evento_calendar(paciente, fecha_str, hora_str, duracion_minutos=30):
    servicio = obtener_servicio()

    # 1. Convertimos los textos (ej: "2026-10-05" y "15:00") a un objeto DateTime real
    inicio_dt = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
    
    # 2. Calculamos la hora de fin sumándole los minutos de duración
    fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)

    # 3. Armamos la estructura de datos que exige la API de Google
    evento = {
        'summary': f'Cita Médica - {paciente}',
        'description': f'Cita médica agendada para {paciente}',
        'start': {
            'dateTime': inicio_dt.isoformat(),
            'timeZone': 'America/Bogota',  # Ajusta tu zona horaria si es diferente
        },
        'end': {
            'dateTime': fin_dt.isoformat(),
            'timeZone': 'America/Bogota',
        },
    }

    # 4. Enviamos la petición a Google Calendar
    evento_creado = servicio.events().insert(calendarId='santipirafan1@gmail.com', body=evento).execute()
    
    # 5. Google nos responde con un ID único de evento
    return evento_creado.get('id')

# En calendar_service.py
def eliminar_evento(event_id):
    servicio = obtener_servicio()
    try:
        servicio.events().delete(
            calendarId= 'santipirafan1@gmail.com',
            eventId=event_id
        ).execute()
        return True
    except HttpError as e:
        # Si el evento no existe (404/410), continuamos normalmente
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

    # Formateamos con el offset explícito para America/Bogota (-05:00)
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
    
    # Definimos el rango del día completo (de 08:00 a 17:00)
    inicio_dia = f"{fecha_str}T08:00:00-05:00"
    fin_dia = f"{fecha_str}T17:00:00-05:00"

    eventos_result = servicio.events().list(
        calendarId='santipirafan1@gmail.com',
        timeMin=inicio_dia,
        timeMax=fin_dia,
        singleEvents=True,
        orderBy='startTime',
        timeZone='America/Bogota'
    ).execute()

    eventos = eventos_result.get('items', [])
    
    # Extraemos las horas de inicio que ya están ocupadas
    horas_ocupadas = []
    for evento in eventos:
        start = evento['start'].get('dateTime', '')
        if start:
            # Extrae solo la hora en formato "HH:MM" (ej. "15:00")
            hora = start.split('T')[1][:5]
            horas_ocupadas.append(hora)

    # Definimos la jornada laboral estándar (citas de 1 hora)
    jornada = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
    
    # Filtramos las horas que no están en la lista de ocupadas
    horas_libres = [h for h in jornada if h not in horas_ocupadas]
    
    return horas_libres

