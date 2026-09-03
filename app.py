import os
import requests
from flask import Flask, request, jsonify
from main import recibir_mensaje
import database  # Importamos la base de datos

app = Flask(__name__)

# Aseguramos la creación de tablas al iniciar la aplicación Flask
database.init_db()

# Configuración de variables de entorno (Render)
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_de_verificacion_seguro")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "1243724885499477")
PORT = int(os.environ.get("PORT", 5000))

def enviar_mensaje_meta(telefono, texto):
    """
    Envía una respuesta de texto de regreso al usuario a través de la API oficial de Meta.
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("[ERROR] Falta configurar WHATSAPP_TOKEN o PHONE_NUMBER_ID en las variables de entorno.")
        return

    url = f"https://graph.facebook.com/v26.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[META RESPONSE] Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"[ERROR SENDING TO META] {e}")

@app.route('/')
def home():
    return "🤖 Bot de Agendamiento de Citas Médicas activo y corriendo en Meta Cloud API.", 200

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    """
    Endpoint de verificación que requiere Meta para validar el Webhook.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("[WEBHOOK] Verificación exitosa con Meta.")
            return challenge, 200
        else:
            print("[WEBHOOK] Token de verificación inválido.")
            return "Token de verificación no válido", 403
    return "Parámetros faltantes", 400

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Procesa las notificaciones entrantes de mensajes enviados por los usuarios en WhatsApp.
    """
    data = request.get_json() or {}

    try:
        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                if messages:
                    mensaje = messages[0]
                    telefono = mensaje.get('from')  # Número del usuario que escribe
                    tipo_mensaje = mensaje.get('type')

                    # Extraer el texto ingresado por el usuario
                    texto = ""
                    if tipo_mensaje == 'text':
                        texto = mensaje.get('text', {}).get('body', '')
                    elif tipo_mensaje == 'interactive':
                        interactive = mensaje.get('interactive', {})
                        if interactive.get('type') == 'button_reply':
                            texto = interactive.get('button_reply', {}).get('title', '')
                        elif interactive.get('type') == 'list_reply':
                            texto = interactive.get('list_reply', {}).get('title', '')

                    if telefono and texto:
                        print(f"[INCOMING] De: {telefono} | Mensaje: '{texto}'")
                        
                        # 1. Tu lógica procesa la respuesta
                        respuesta_bot = recibir_mensaje(telefono, texto)
                        
                        # 2. Enviar respuesta de regreso a través de Meta API
                        if respuesta_bot:
                            enviar_mensaje_meta(telefono, respuesta_bot)

    except Exception as e:
        print(f"[ERROR PROCESANDO WEBHOOK META] {e}")

    # Meta requiere siempre una respuesta 200 OK inmediata
    return jsonify({"status": "success"}), 200

@app.route('/wompi-webhook', methods=['POST'])
def wompi_webhook():
    """
    Endpoint para recibir las notificaciones de pago en segundo plano enviadas por Wompi.
    """
    data = request.get_json() or {}
    print(f"[WOMPI EVENT] Evento recibido: {data}")

    try:
        event = data.get('event')
        
        if event == 'transaction.updated':
            transaction = data.get('data', {}).get('transaction', {})
            status = transaction.get('status')
            reference = transaction.get('reference')  # Referencia o teléfono del cliente

            if status == 'APPROVED':
                print(f"[WOMPI] ¡Pago APROBADO! Referencia/Teléfono: {reference}")
                
                # Enviar mensaje de confirmación directa al cliente por WhatsApp
                if reference:
                    mensaje_exito = (
                        "✅ *¡Pago recibido exitosamente!*\n\n"
                        "Tu cita ha sido confirmada y registrada en nuestro sistema. "
                        "¡Te esperamos!"
                    )
                    enviar_mensaje_meta(reference, mensaje_exito)

            elif status == 'DECLINED':
                print(f"[WOMPI] Pago RECHAZADO. Referencia/Teléfono: {reference}")
                if reference:
                    mensaje_rechazo = (
                        "❌ Tu pago no pudo ser procesado. "
                        "Por favor, intenta nuevamente utilizando el enlace enviado."
                    )
                    enviar_mensaje_meta(reference, mensaje_rechazo)

    except Exception as e:
        print(f"[ERROR PROCESANDO WEBHOOK WOMPI] {e}")

    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)