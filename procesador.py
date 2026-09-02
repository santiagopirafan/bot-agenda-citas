from datetime import datetime

def procesar_opcion_menu(mensaje):
    texto = mensaje.strip().lower()

    # Mapeo consistente con el menú mostrado al usuario en main.py
    if texto in ["1", "disponibilidad", "ver disponibilidad"] or "disponibilidad" in texto:
        return {"accion": "disponibilidad"}
    elif texto in ["2", "agendar", "reservar"] or "agendar" in texto or "reservar" in texto:
        return {"accion": "agendar"}
    elif texto in ["3", "consultar", "mis citas"] or "consultar" in texto or "mis citas" in texto:
        return {"accion": "consultar"}
    elif texto in ["4", "eliminar", "cancelar"] or "eliminar" in texto or "cancelar" in texto:
        return {"accion": "eliminar"}
    else:
        return {"accion": "desconocida"}


def procesar_tipo_cita(mensaje):
    text = mensaje.strip().lower()

    if text == "1" or "primera" in text or "nueva" in text:
        return {"tipo": "primera_vez", "duracion_minutos": 30}
    elif text == "2" or "control" in text or "reconsulta" in text or "seguimiento" in text:
        return {"tipo": "control", "duracion_minutos": 60}
    else:
        return {"tipo": "desconocido"}


def extraer_datos_cita(mensaje):
    text = mensaje.strip().split()

    if len(text) < 4:
        return {
            "valido": False, 
            "error": "⚠️ Faltan datos. El formato correcto es:\n`agendar YYYY-MM-DD HH:MM Nombre`\n*(Ej: agendar 2026-09-10 10:00 Carlos Gomez)*"
        }

    fecha = text[1]
    hora = text[2]
    # Mantenemos las mayúsculas originales para el nombre del paciente
    paciente = " ".join(text[3:])

    # Validación rápida del formato de fecha
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {
            "valido": False,
            "error": "⚠️ La fecha ingresada no es válida. Usa el formato YYYY-MM-DD (Ej: 2026-09-10)."
        }

    return {
        "valido": True,
        "fecha": fecha,
        "hora": hora,
        "paciente": paciente
    }