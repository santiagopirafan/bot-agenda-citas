const wppconnect = require('@wppconnect-team/wppconnect');
const axios = require('axios');

wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    refreshQR: 15000, // Da 15 segundos entre recargas de QR para dar tiempo a escanear
    headless: 'new',  // Modo navegador silencioso
    puppeteerOptions: {
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
}).then((client) => start(client)).catch((error) => console.log('Error de inicio:', error));

function start(client) {
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');

    client.onMessage(async (message) => {
        // Procesamos solo mensajes individuales que contengan texto
        if (!message.isGroupMsg && message.body) {
            const telefono = message.from.replace('@c.us', '');
            const texto = message.body;

            console.log(`📩 Mensaje recibido de ${telefono}: "${texto}"`);

            try {
                // Enviar petición a Flask (app.py)
                const response = await axios.post('http://127.0.0.1:5000/webhook', {
                    telefono: telefono,
                    texto: texto
                });

                if (response.data && response.data.respuesta) {
                    await client.sendText(message.from, response.data.respuesta);
                    console.log(`📤 Respuesta enviada a ${telefono}`);
                }
            } catch (err) {
                console.error('⚠️ Error al conectar con Flask:', err.message);
            }
        }
    });
}