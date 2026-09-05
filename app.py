from flask import Flask, request, jsonify
import threading
import database
from config import PORT, VERIFY_TOKEN, LINK_DE_PAGO
from main import recibir_mensaje
from services.whatsapp_service import enviar_mensaje_texto
from services.wompi_service import procesar_webhook_wompi
import services.calendar_service as calendar_service
from services.tareas_segundo_plano import escanear_calendario_continuamente

app = Flask(__name__)

# Inicializamos la base de datos al arrancar la aplicación
database.init_db()

@app.route('/')
def home():
    return "🤖 Bot de Agendamiento de Citas Médicas activo.", 200

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token and mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token no válido", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json() or {}

    try:
        entries = data.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                if messages:
                    msg = messages[0]
                    telefono = msg.get('from')
                    tipo_msg = msg.get('type')
                    
                    texto = ""
                    interactive_id = None

                    if tipo_msg == 'text':
                        texto = msg.get('text', {}).get('body', '')
                    elif tipo_msg == 'interactive':
                        interactive = msg.get('interactive', {})
                        if interactive.get('type') == 'button_reply':
                            btn = interactive.get('button_reply', {})
                            interactive_id = btn.get('id')
                            texto = btn.get('title', '')
                        elif interactive.get('type') == 'list_reply':
                            lst = interactive.get('list_reply', {})
                            interactive_id = lst.get('id')
                            texto = lst.get('title', '')

                    if telefono:
                        # Ruteamos la entrada capturando el id interactivo
                        recibir_mensaje(telefono, texto, interactive_id=interactive_id)

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")

    return jsonify({"status": "success"}), 200

@app.route('/wompi-webhook', methods=['POST'])
def wompi_webhook():
    payload = request.get_json() or {}
    res_wompi = procesar_webhook_wompi(payload)

    if res_wompi["exitoso"]:
        telefono = res_wompi["telefono"]
        if telefono:
            cita_pendiente = database.obtener_cita_pendiente(telefono)
            if cita_pendiente:
                event_id, meet_link = None, None
                modalidad_cita = cita_pendiente.get('modalidad', 'VIRTUAL')
                
                try:
                    res_cal = calendar_service.agendar_cita(
                        resumen=f"{cita_pendiente['tipo_cita']} - {cita_pendiente['paciente']}",
                        fecha=cita_pendiente['fecha_iso'],
                        hora_inicio=cita_pendiente['hora_iso'],
                        descripcion=f"Paciente: {cita_pendiente['paciente']}\nTeléfono: {telefono}\nModalidad: {modalidad_cita}",
                        modalidad=modalidad_cita
                    )
                    if isinstance(res_cal, tuple):
                        event_id, meet_link = res_cal
                    else:
                        event_id = res_cal
                except Exception as e:
                    print(f"[ERROR CALENDAR WOMPI] {e}")

                database.confirmar_cita_pagada(telefono, event_id, meet_link)
                database.guardar_estado_usuario(telefono, 'INICIO', {})

                texto_meet = f"💻 *Google Meet:* {meet_link}\n" if meet_link else ""
                msg = (
                    f"✅ *¡Pago confirmado! Cita agendada.*\n\n"
                    f"👤 *Paciente:* {cita_pendiente['paciente']}\n"
                    f"📍 *Modalidad:* {modalidad_cita}\n"
                    f"📅 *Fecha:* {cita_pendiente['fecha_str']}\n"
                    f"⏰ *Hora:* {cita_pendiente['hora_str']}\n"
                    f"{texto_meet}"
                )
                enviar_mensaje_texto(telefono, msg)

    elif res_wompi["estado"] in ['DECLINED', 'ERROR', 'VOIDED']:
        telefono = res_wompi["telefono"]
        if telefono:
            enviar_mensaje_texto(telefono, f"❌ El pago no se completó. Inténtalo de nuevo:\n{LINK_DE_PAGO}")

    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    # Inicia el hilo en segundo plano antes de arrancar Flask
    thread = threading.Thread(target=escanear_calendario_continuamente, daemon=True)
    thread.start()
    print("[SISTEMA] Hilo de escaneo registrado correctamente.")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)