from flask import Flask, send_file, request, jsonify
import os

app = Flask(__name__)

# Definimos el puerto antes de todo
PORT = int(os.environ.get('PORT', 8080))

# -------------------------------------------------------------
# 1. RUTA PARA MOSTRAR EL QR
# -------------------------------------------------------------
@app.route('/')
@app.route('/qr')
def ver_qr():
    if os.path.exists('qr.png'):
        return send_file('qr.png', mimetype='image/png')
    return """
    <html>
        <head><meta http-equiv="refresh" content="5"></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h2>Bot de WhatsApp</h2>
            <p>Generando código QR... La página se recargará en 5 segundos.</p>
        </body>
    </html>
    """

# -------------------------------------------------------------
# 2. RUTA DEL WEBHOOK PARA WHATSAPP
# -------------------------------------------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json() or {}
    telefono = datos.get('telefono', '')
    texto = datos.get('texto', '')

    # Aquí procesas tu lógica de negocio / citas
    print(f"Mensaje recibido de {telefono}: {texto}")

    return jsonify({"respuesta": "Mensaje procesado correctamente"})

# -------------------------------------------------------------
# 3. ARRANQUE DEL SERVIDOR PARA RAILWAY
# -------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)