from flask import Flask, send_file, request, jsonify
import os
from main import recibir_mensaje

app = Flask(__name__)

# Puerto exclusivo para la aplicación de Python/Flask (5000 por defecto)
PORT = int(os.environ.get('FLASK_PORT', os.environ.get('PORT', 5000)))

@app.route('/')
@app.route('/qr')
def ver_qr():
    if os.path.exists('qr.png'):
        response = send_file('qr.png', mimetype='image/png')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return """
    <html>
        <head>
            <meta http-equiv="refresh" content="5">
            <title>Vincular WhatsApp</title>
        </head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
            <h2>🤖 Bot de Citas Médicas</h2>
            <p>Esperando la generación del código QR...</p>
            <p><small>La página se actualizará automáticamente cada 5 segundos.</small></p>
        </body>
    </html>
    """

@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json() or {}
    telefono = datos.get('telefono', '')
    texto = datos.get('texto', '')
    
    if not telefono or not texto:
        return jsonify({"respuesta": "Formato de mensaje no válido"}), 400

    respuesta_bot = recibir_mensaje(telefono, texto)
    return jsonify({"respuesta": respuesta_bot})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)