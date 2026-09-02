from flask import Flask, request, jsonify
import main
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json()
    
    if datos and 'telefono' in datos and 'texto' in datos:
        telefono = datos['telefono']
        texto = datos['texto']
        
        # Procesamos con la lógica de main.py
        respuesta_texto = main.recibir_mensaje(telefono, texto)
        
        # Retornamos la respuesta al puente en JS
        return jsonify({"respuesta": respuesta_texto}), 200

    return jsonify({"error": "Datos no válidos"}), 400

if __name__ == "__main__":
    # Fijamos Flask localmente en el puerto 5000 para la comunicación con el bridge
    app.run(host="127.0.0.1", port=5000)