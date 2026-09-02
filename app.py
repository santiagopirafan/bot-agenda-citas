from flask import Flask, send_file, request, jsonify
import os
from main import recibir_mensaje

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 8080))

@app.route('/')
@app.route('/qr')
def ver_qr():
    if os.path.exists('qr.png'):
        response = send_file('qr.png', mimetype='image/png')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
    return """
    <html>
        <head><meta http-equiv="refresh" content="5"></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h2>Bot de WhatsApp</h2>
            <p>Generando código QR... La página se recargará en 5 segundos.</p>
        </body>
    </html>
    """

@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json() or {}
    telefono = datos.get('telefono', '')
    texto = datos.get('texto', '')
    respuesta_bot = recibir_mensaje(telefono, texto)
    return jsonify({"respuesta": respuesta_bot})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)