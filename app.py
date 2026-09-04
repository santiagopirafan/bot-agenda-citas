import os
import requests
from flask import Flask, request, jsonify
from main import recibir_mensaje
import database  # Importamos la base de datos
import calendar_service # Importación del módulo completo

app = Flask(__name__)

# Aseguramos la creación de tablas al iniciar la aplicación Flask
database.init_db()

# Configuración de variables de entorno (Render / Hosting)
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_de_verificacion_seguro")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN" , "EAAgl5uomwpIBSTBCXF01foZCpLjexGFlMEyeT6o840dSoNoCRzemUGaFgiH2INWRNOWqD6RQHlMjmUt8GXdrZBvqVk07getTcjU0SsEUffyIsSLsZBalGBFoRvTajc4cKLhFbh2L974OE6nV0aZAMPQU1vJKpL9NtfmyuZC01RkHF9DHWx7zoFi4HBveQqkTFUAZDZD")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "1243724885499477")
LINK_DE_PAGO = os.getenv("LINK_DE_PAGO", "https://checkout.wompi.co/l/test_VPOS_6fb1HX")
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
            
            # Extraer teléfono (desde customer_data o la referencia)
            customer_data = transaction.get('customer_data', {})
            telefono = customer_data.get('phone_number') or transaction.get('reference')
            
            if telefono:
                telefono = str(telefono).replace('whatsapp:', '').replace('+', '').strip()

            if status == 'APPROVED' and telefono:
                print(f"[WOMPI] ¡Pago APROBADO! Teléfono/Ref: {telefono}")
                
                # 1. Obtener la cita pendiente guardada previamente en SQLite
                cita_pendiente = database.obtener_cita_pendiente(telefono)
                
                if cita_pendiente:
                    event_id = None
                    meet_link = None
                    
                    # 2. Crear la cita en Google Calendar
                    try:
                        func_agendar = getattr(calendar_service, 'agendar_cita', None) or getattr(calendar_service, 'agendar_cita_google_calendar', None)
                        
                        if func_agendar:
                            res_event = func_agendar(
                                resumen=f"{cita_pendiente.get('tipo_cita', 'Consulta')} - {cita_pendiente.get('paciente')}",
                                fecha=cita_pendiente.get('fecha_iso'),
                                hora_inicio=cita_pendiente.get('hora_iso'),
                                descripcion=f"Paciente: {cita_pendiente.get('paciente')}\nTeléfono: {telefono}"
                            )
                            
                            # Manejar si retorna tupla (event_id, meet_link) o valor único
                            if isinstance(res_event, tuple):
                                event_id, meet_link = res_event
                            else:
                                event_id = res_event

                            print("[GOOGLE CALENDAR] Cita y videoconferencia de Meet procesadas.")
                    except Exception as cal_err:
                        print(f"[ERROR GOOGLE CALENDAR] {cal_err}")
                    
                    # 3. Confirmar la cita como PAGADA en SQLite guardando event_id y meet_link
                    database.confirmar_cita_pagada(telefono, event_id, meet_link)
                    database.guardar_estado_usuario(telefono, 'INICIO', {})

                    # 4. Enviar mensaje de confirmación directa al cliente por WhatsApp
                    texto_meet = f"💻 *Enlace a la videollamada (Google Meet):*\n{meet_link}\n\n" if meet_link else ""
                    
                    mensaje_exito = (
                        f"✅ *¡Pago recibido exitosamente!*\n\n"
                        f"👤 *Paciente:* {cita_pendiente.get('paciente')}\n"
                        f"📅 *Fecha:* {cita_pendiente.get('fecha_str')}\n"
                        f"⏰ *Hora:* {cita_pendiente.get('hora_str')}\n\n"
                        f"{texto_meet}"
                        f"Tu cita médica ha sido confirmada y agendada en nuestro calendario. ¡Te esperamos!"
                    )
                    enviar_mensaje_meta(telefono, mensaje_exito)

            elif status in ['DECLINED', 'ERROR', 'VOIDED']:
                print(f"[WOMPI] Pago NO COMPLETADO ({status}). Referencia/Teléfono: {telefono}")
                if telefono:
                    mensaje_rechazo = (
                        "❌ El pago no se completó de manera correcta. Por favor, intenta nuevamente para asegurar tu turno.\n\n"
                        f"👉 *Enlace de pago:* {LINK_DE_PAGO}"
                    )
                    enviar_mensaje_meta(telefono, mensaje_rechazo)

    except Exception as e:
        print(f"[ERROR PROCESANDO WEBHOOK WOMPI] {e}")

    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)