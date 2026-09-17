import os
import threading
from flask import Flask, request, jsonify, render_template

import database
from main import recibir_mensaje
from services.calendar_service import buscar_citas_manuales_nuevas
from services.whatsapp_service import enviar_mensaje_texto
from services.tareas_segundo_plano import escanear_calendario_continuamente

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'clave_secreta_por_defecto')

# Inicializar Base de Datos (SQLite/PostgreSQL)
database.init_db()

# ==============================================================================
# INICIO DE TAREAS EN SEGUNDO PLANO (COMPATIBLE CON GUNICORN/RENDER)
# ==============================================================================
try:
    hilo_escaneo = threading.Thread(target=escanear_calendario_continuamente, daemon=True)
    hilo_escaneo.start()
    print("[SISTEMA] Hilo de escaneo en segundo plano INICIADO correctamente para Gunicorn.")
except Exception as e:
    print(f"[ERROR SISTEMA] No se pudo iniciar el hilo en segundo plano: {e}")

# ==============================================================================
# RUTAS DE LA APLICACIÓN WEB & WEBHOOK METAV1
# ==============================================================================

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "bot": "Bot Agenda Médica",
        "modo": "Meta WhatsApp API Directa + Google Service Account"
    })

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Endpoint principal que procesa la verificación y mensajes entrantes de Meta."""
    # VERIFICACIÓN WEBHOOK (Petición GET de Meta)
    if request.method == 'GET':
        mode = request.args.get('hub.mode') or request.args.get('hub_mode')
        token = request.args.get('hub.verify_token') or request.args.get('hub_verify_token')
        challenge = request.args.get('hub.challenge') or request.args.get('hub_challenge')

        token_esperado = os.environ.get('WEBHOOK_VERIFY_TOKEN', 'mi_token_de_verificacion_seguro')

        if mode == 'subscribe' and token == token_esperado:
            print("[WEBHOOK] Verificación exitosa por Meta.")
            return str(challenge), 200
        else:
            print("[WEBHOOK ERROR] Verificación fallida. Token o modo incorrecto.")
            return "Token de verificación inválido", 403

    # PROCESAMIENTO DE MENSAJES (Petición POST de Meta)
    elif request.method == 'POST':
        data = request.get_json()
        try:
            if data and "entry" in data:
                for entry in data["entry"]:
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        
                        if messages:
                            msg = messages[0]
                            telefono = msg.get("from")
                            
                            texto = ""
                            interactive_id = None

                            if msg.get("type") == "text":
                                texto = msg.get("text", {}).get("body", "")
                            elif msg.get("type") == "interactive":
                                interactive = msg.get("interactive", {})
                                if interactive.get("type") == "button_reply":
                                    interactive_id = interactive.get("button_reply", {}).get("id")
                                    texto = interactive.get("button_reply", {}).get("title", "")
                                elif interactive.get("type") == "list_reply":
                                    interactive_id = interactive.get("list_reply", {}).get("id")
                                    texto = interactive.get("list_reply", {}).get("title", "")

                            if telefono:
                                recibir_mensaje(telefono, texto, interactive_id)

            return jsonify({"status": "success"}), 200
        except Exception as e:
            print(f"[ERROR WEBHOOK POST]: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/historial')
def ver_historial():
    try:
        notificaciones = database.obtener_todas_notificaciones(limite=100)
        return render_template('historial.html', notificaciones=notificaciones)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/probar-escaneo', methods=['GET', 'POST'])
def probar_escaneo():
    """Endpoint manual para forzar la revisión de Google Calendar"""
    eventos = buscar_citas_manuales_nuevas()
    return jsonify({
        "status": "success",
        "eventos_encontrados": len(eventos),
        "eventos": eventos
    })

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT, debug=False)