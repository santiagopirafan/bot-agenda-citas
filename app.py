from flask import Flask, send_file, request, jsonify
import os

app = Flask(__name__)

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

if __name__ == '__main__':
    # Railway asigna el puerto mediante la variable PORT automáticamente
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)