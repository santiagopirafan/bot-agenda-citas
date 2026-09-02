const wppconnect = require('@wppconnect-team/wppconnect');
const QRCode = require('qrcode');
const axios = require('axios');
const http = require('http');

// 1. Crear un servidor HTTP dummy para que Render detecte el servicio como "Saludable" (Healthy) y NO marque Timed Out
const PORT = process.env.PORT || 10000;
http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Bot de WhatsApp activo y escuchando.\n');
}).listen(PORT, () => {
    console.log(`🌐 Servidor de salud activo en puerto ${PORT}`);
});

// 2. Inicializar WPPConnect
wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    logQR: false,
    catchQR: (base64Qrimg) => {
        console.log('\n==================================================');
        console.log('👇 ESCANEA ESTE CÓDIGO QR CON TU WHATSAPP 👇');
        console.log('==================================================\n');

        // Genera el código QR en formato de texto plano (small) garantizando compatibilidad
        QRCode.toString(base64Qrimg, { type: 'terminal', small: true }, function (err, url) {
            if (err) {
                console.log('Error generando QR:', err);
            } else {
                console.log(url);
            }
        });

        console.log('\n==================================================\n');
    },
    statusFind: (statusSession, session) => {
        console.log('Estado de la sesión:', statusSession);
    },
    puppeteerOptions: {
        userDataDir: './tokens/bot-citas',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu',
            '--memory-pressure-off'
        ]
    }
})
    .then((client) => start(client))
    .catch((error) => console.log('Error al iniciar WPPConnect:', error));

function start(client) {
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');

    client.onMessage(async (message) => {
        console.log(`📩 [LOG BRUTO] Mensaje capturado de: ${message.from}`);

        if (!message.isGroupMsg && message.body) {
            const telefono = message.from.replace(/@c\.us|@s\.whatsapp\.net/g, '');
            const texto = message.body;

            console.log(`📩 Procesando mensaje de ${telefono}: "${texto}"`);

            try {
                // Comunicación interna con Flask en el puerto 5000
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