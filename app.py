from flask import Flask, send_file, request, jsonify
import os

app = Flask(__name__)

# -------------------------------------------------------------
# 1. RUTA PARA MOSTRAR EL QR (CÓDIGO NUEVO)
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
# 2. TU RUTA DEL WEBHOOK (TU CÓDIGO ACTUAL)
# -------------------------------------------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json()
    # AQUÍ MANTIENES TODA TU LÓGICA ORIGINAL DEL BOT
    # (por ejemplo: procesar citas, respuestas, etc.)
    return jsonify({"respuesta": "Mensaje procesado"})

# -------------------------------------------------------------
# 3. ARRANQUE DEL SERVIDOR EN RAILWAY (CÓDIGO ACTUALIZADO)
# -------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)