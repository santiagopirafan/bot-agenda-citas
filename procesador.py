
from datetime import datetime

def procesar_opcion_menu(mensaje):

    texto = mensaje.strip().lower()

    if texto == "1" or "agendar" in texto or "reservar" in texto:
        return{"accion": "agendar"}
    elif texto == "2" or "consultar" in texto or "mi cita" in texto:
        return{"accion": "consultar"}
    elif texto == "3" or "eliminar" in texto or "cancelar" in texto:
        return{"accion": "eliminar"}
    else:
        return {"accion": "desconocida"}


def procesar_tipo_cita(mensaje):

    text = mensaje.strip().lower()

    if text == "1" or "primera" in text or "primera vez" in text or "nueva" in text:
        return {"tipo": "primera_vez", "duracion_minutos": 30}
    elif text == "2" or "control" in text or "reconsulta" in text or "seguimiento" in text:
        return {"tipo": "control", "duracion_minutos": 60}
    else:
        return {"tipo": "desconocido"}


def extraer_datos_cita(mensaje):

    text = mensaje.strip().lower().split()

    if len(text) < 4 :
        return {"valido": False, "error": "Faltan datos. Formato: Cita YYYY-MM-DD HH:MM Nombre"}
    

    fecha = text[1]
    hora = text[2]
    paciente = " ".join(text[3:]) if len(text) > 3 else ""
    

    return {
        "valido": True,
        "fecha": fecha,
        "hora": hora,
        "paciente": paciente
    }

    

