import requests
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID

# URL oficial de Graph API de Meta
URL_META_WHATSAPP = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

def obtener_headers():
    """Retorna los encabezados con la autorización Bearer para Meta API."""
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

def enviar_mensaje_texto(telefono, texto):
    """Envia un mensaje de texto tradicional o con formato Markdown (*negrita*, _cursiva_)."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("[ERROR WHATSAPP] Faltan WHATSAPP_TOKEN o PHONE_NUMBER_ID en las variables de entorno.")
        return None

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    
    try:
        response = requests.post(URL_META_WHATSAPP, headers=obtener_headers(), json=payload)
        return response.json()
    except Exception as e:
        print(f"[ERROR WHATSAPP TEXTO] {e}")
        return None

def enviar_botones_interactivos(telefono, texto, botones):
    """
    Envia un mensaje con botones interactivos (máximo 3).
    'botones' debe ser una lista de tuplas: [("ID_OPCION_1", "Texto Botón 1"), ...]
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("[ERROR WHATSAPP] Faltan credenciales de Meta.")
        return None

    lista_botones = []
    for btn_id, btn_title in botones:
        lista_botones.append({
            "type": "reply",
            "reply": {
                "id": btn_id,
                "title": btn_title[:20]  # Meta limita el título a 20 caracteres
            }
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {"buttons": lista_botones}
        }
    }

    try:
        response = requests.post(URL_META_WHATSAPP, headers=obtener_headers(), json=payload)
        return response.json()
    except Exception as e:
        print(f"[ERROR WHATSAPP BOTONES] {e}")
        return None

def enviar_lista_interactiva(telefono, texto, boton_texto, titulo_seccion, opciones):
    """
    Envia un menú desplegable interactivo (List Message).
    'opciones' es una lista de dicts: [{"id": "ID_1", "title": "Título", "description": "Detalle"}]
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("[ERROR WHATSAPP] Faltan credenciales de Meta.")
        return None

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": texto},
            "action": {
                "button": boton_texto[:20],
                "sections": [
                    {
                        "title": titulo_seccion[:24],
                        "rows": opciones
                    }
                ]
            }
        }
    }

    try:
        response = requests.post(URL_META_WHATSAPP, headers=obtener_headers(), json=payload)
        return response.json()
    except Exception as e:
        print(f"[ERROR WHATSAPP LISTA] {e}")
        return None