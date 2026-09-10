import os
import threading
from flask import Flask, request, jsonify, render_template

import database
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
# RUTAS DE LA APLICACIÓN WEB
# ==============================================================================

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "bot": "Bot Agenda Médica",
        "modo": "Meta WhatsApp API Directa + Google Service Account"
    })

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