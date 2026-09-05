import os
import json
import uuid
import zoneinfo
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import GOOGLE_CALENDAR_ID, ZONA_HORARIA as CONFIG_TZ

# Permisos (Scopes) necesarios para gestionar los eventos en Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# ID del calendario principal donde se agendan las citas
CALENDAR_ID = GOOGLE_CALENDAR_ID

# Configuración de zona horaria local (Bogotá)
ZONA_HORARIA = zoneinfo.ZoneInfo("America/Bogota")


def obtener_servicio():
    """
    Autentica y devuelve el cliente oficial de la API de Google Calendar.
    Soporta credenciales por variable de entorno (JSON string) o archivo físico 'credentials.json'.
    """
    google_json_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if google_json_env:
        try:
            # 1. Limpieza de comillas externas y espacios innecesarios
            google_json_env = google_json_env.strip()
            if (google_json_env.startswith('"') and google_json_env.endswith('"')) or \
               (google_json_env.startswith("'") and google_json_env.endswith("'")):
                google_json_env = google_json_env[1:-1]

            # 2. Reemplazo de saltos de línea escapados '\\n' a caracteres reales '\n'
            google_json_env = google_json_env.replace('\\n', '\n')

            # 3. Parseo flexible del JSON
            info = json.loads(google_json_env, strict=False)
            
            # 4. Asegurar que la clave privada tenga el formato PEM adecuado
            if "private_key" in info and isinstance(info["private_key"], str):
                info["private_key"] = info["private_key"].replace('\\n', '\n')

            # Crear credenciales usando la información extraída del entorno
            credenciales = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            print(f"[ERROR PARSING GOOGLE CREDENTIALS] {e}")
            raise e
    elif os.path.exists('credentials.json'):
        # Si no hay variable de entorno, buscar el archivo local
        credenciales = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES
        )
    else:
        raise FileNotFoundError("No se encontraron las credenciales de Google Calendar.")

    # Construir y retornar el servicio cliente v3 de Google Calendar
    return build('calendar', 'v3', credentials=credenciales)


def es_dia_habilitado(fecha_dt, modalidad="VIRTUAL"):
    """
    Evalúa la regla de negocio para habilitar un día:
    - Fines de semana (Sábados/Domingos) deshabilitados por defecto (weekday >= 5).
    - VIRTUAL: Días IMPARES del mes.
    - PRESENCIAL: Días PARES del mes.
    """
    if fecha_dt.weekday() >= 5:  # Sábados (5) y Domingos (6)
        return False
        
    dia_del_mes = fecha_dt.day
    if modalidad.upper() == "VIRTUAL":
        return dia_del_mes % 2 != 0  # Impar
    else:
        return dia_del_mes % 2 == 0   # Par


def obtener_dias_disponibles(modalidad="VIRTUAL", dias_a_evaluar=14):
    """
    Genera la lista de próximos días disponibles filtrados por modalidad (pares/impares),
    respetando eventos manuales de excepción ('Bloqueado' o 'Habilitar') puestos por la doctora.
    """
    servicio = obtener_servicio()
    hoy = datetime.now(ZONA_HORARIA).date()
    dias_disponibles = []

    # Consultar eventos del calendario en el rango de días
    inicio_iso = datetime.combine(hoy, datetime.min.time()).isoformat() + '-05:00'
    fin_eval = hoy + timedelta(days=dias_a_evaluar)
    fin_iso = datetime.combine(fin_eval, datetime.max.time()).isoformat() + '-05:00'

    events_result = servicio.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio_iso,
        timeMax=fin_iso,
        singleEvents=True,
        orderBy='startTime',
        timeZone='America/Bogota'
    ).execute()
    
    eventos = events_result.get('items', [])

    # Evaluar la disponibilidad de los siguientes días
    for i in range(1, dias_a_evaluar + 1):
        fecha_eval = hoy + timedelta(days=i)
        fecha_str = fecha_eval.strftime('%Y-%m-%d')
        
        bloqueado = False
        habilitado_manual = False

        # Verificar si existe alguna anotación administrativa en Calendar para este día
        for ev in eventos:
            start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date', '')
            if start.startswith(fecha_str):
                titulo = ev.get('summary', '').lower()
                if any(k in titulo for k in ['bloqueado', 'no disponible', 'vacaciones', 'cerrado']):
                    bloqueado = True
                elif any(k in titulo for k in ['habilitar', 'abierto', 'excepcion']):
                    habilitado_manual = True

        # El día califica si fue habilitado manualmente O si cumple la regla par/impar y no está bloqueado
        if not bloqueado and (habilitado_manual or es_dia_habilitado(fecha_eval, modalidad)):
            dias_disponibles.append({
                "fecha_iso": fecha_str,
                "fecha_str": fecha_eval.strftime('%d/%m/%Y')
            })

    return dias_disponibles


def obtener_horas_disponibles(fecha_str, modalidad="VIRTUAL"):
    """
    Consulta horas ocupadas en Google Calendar y devuelve los slots libres formateados en AM/PM.
    Permite agregar horas extra manualmente leyendo palabras clave ('habilitar' o 'extra').
    """
    servicio = obtener_servicio()
    
    # Definir rango de horas atendidas según modalidad
    if modalidad.upper() == "VIRTUAL":
        jornada = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    else:
        jornada = ["11:00", "12:00", "13:00", "14:00", "15:00"]

    inicio_dia = f"{fecha_str}T00:00:00-05:00"
    fin_dia = f"{fecha_str}T23:59:59-05:00"

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
    horas_extra = []

    for e in eventos:
        if 'dateTime' in e.get('start', {}):
            hora_evento = e['start']['dateTime'].split('T')[1][:5]
            titulo = e.get('summary', '').lower()
            
            # Si el evento tiene las palabras clave, se toma como hora extra
            if 'habilitar' in titulo or 'extra' in titulo:
                horas_extra.append(hora_evento)
            else:
                horas_ocupadas.append(hora_evento)

    # Combina la jornada normal con las horas extra y elimina duplicados
    jornada_total = list(set(jornada + horas_extra))
    jornada_total.sort()

    horas_libres = []

    for hora in jornada_total:
        if hora not in horas_ocupadas:
            hora_num = int(hora[:2])
            
            # Formateo de hora amigable a AM/PM
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


def agendar_cita(resumen, fecha, hora_inicio, descripcion, modalidad="VIRTUAL"):
    """
    Crea un evento en Google Calendar. Al usar Service Accounts con un Gmail gratuito,
    se asigna un enlace fijo de Meet para evitar el bloqueo de la API.
    """
    service = obtener_servicio()

    start_datetime = f"{fecha}T{hora_inicio}:00-05:00"
    hora, minuto = map(int, hora_inicio.split(':'))
    hora_fin = f"{hora + 1:02d}:{minuto:02d}"
    end_datetime = f"{fecha}T{hora_fin}:00-05:00"

    # ⚠️ IMPORTANTE: Genera un enlace de Meet permanente desde tu cuenta y ponlo aquí
    LINK_MEET_FIJO = "https://meet.google.com/tu-enlace-fijo" 

    if modalidad == "VIRTUAL":
        descripcion += f"\n\n💻 Enlace de la videollamada: {LINK_MEET_FIJO}"

    evento_body = {
        'summary': resumen,
        'description': descripcion,
        'start': {
            'dateTime': start_datetime,
            'timeZone': 'America/Bogota',
        },
        'end': {
            'dateTime': end_datetime,
            'timeZone': 'America/Bogota',
        }
    }

    try:
        # Se elimina 'conferenceData' para evitar el HttpError 400
        evento_creado = service.events().insert(
            calendarId=CALENDAR_ID,
            body=evento_body
        ).execute()

        event_id = evento_creado.get('id')
        
        # Asignamos el enlace fijo para que llegue al mensaje final de WhatsApp
        meet_link = LINK_MEET_FIJO if modalidad == "VIRTUAL" else None

        print(f"[CALENDAR SUCCESS] Cita {modalidad.capitalize()} creada: ID {event_id}")
        
        return event_id, meet_link

    except Exception as e:
        print(f"[ERROR CALENDAR INSERT] Fallo al crear evento: {e}")
        raise e

def eliminar_evento(event_id):
    """Elimina un evento de Google Calendar según su ID."""
    if not event_id:
        return True
    servicio = obtener_servicio()
    try:
        servicio.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        return True
    except HttpError as e:
        # Si el evento ya fue borrado previamente (404 o 410)
        if e.resp.status in [404, 410]:
            return True
        print(f"[ERROR CALENDAR DELETE] {e}")
        return False


def buscar_citas_manuales_nuevas():
    """
    Escanea en Google Calendar los eventos creados manualmente por la recepcionista o doctora.
    Retorna la lista de eventos desde la hora actual en adelante.
    """
    servicio = obtener_servicio()
    ahora_iso = datetime.now(ZONA_HORARIA).isoformat()

    try:
        events_result = servicio.events().list(
            calendarId=CALENDAR_ID,
            timeMin=ahora_iso,
            singleEvents=True,
            orderBy='startTime',
            timeZone='America/Bogota'
        ).execute()

        return events_result.get('items', [])
    except Exception as e:
        print(f"[ERROR ESCANEO MANUAL CALENDAR] {e}")
        return []