const wppconnect = require('@wppconnect-team/wppconnect');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Tomamos dinámicamente el puerto de la variable de entorno PORT o usamos 5000 por defecto
const PORT = process.env.PORT || 5000;

wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    logQR: false, // Desactivamos el logger interno para dibujarlo manualmente sin fallos
    catchQR: (base64Qrimg, asciiQR) => {
        console.log('\n==================================================');
        console.log('👇 ESCANEA ESTE CÓDIGO QR CON TU WHATSAPP 👇');
        console.log('==================================================\n');

        // Si asciiQR llega definido lo usa, de lo contrario forzamos la renderización
        if (asciiQR) {
            console.log(asciiQR);
        } else {
            // Convierte la imagen base64 a un código QR impreso en la consola de Render
            qrcode.generate(base64Qrimg, { small: true });
        }

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
        // Log para confirmar la entrada bruta de cualquier tipo de mensaje
        console.log(`📩 [LOG BRUTO] Mensaje capturado de: ${message.from}`);

        // Procesamos mensajes individuales que contengan texto (no grupales)
        if (!message.isGroupMsg && message.body) {
            // Limpiamos la extensión para soportar cuentas estándar (@c.us) y de empresa (@s.whatsapp.net)
            const telefono = message.from.replace(/@c\.us|@s\.whatsapp\.net/g, '');
            const texto = message.body;

            console.log(`📩 Procesando mensaje de ${telefono}: "${texto}"`);

            try {
                // Petición HTTP a Flask usando el puerto dinámico local
                const response = await axios.post(`http://127.0.0.1:${PORT}/webhook`, {
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