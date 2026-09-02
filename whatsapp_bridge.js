const wppconnect = require('@wppconnect-team/wppconnect');
const axios = require('axios');
const http = require('http');

let currentQrCode = null;
let statusMessage = 'Iniciando navegador WhatsApp...';

// Servidor de salud y visor de QR
const PORT = process.env.PORT || 10000;
http.createServer((req, res) => {
    const url = req.url.toLowerCase();

    if ((url === '/qr' || url === '/qr/') && currentQrCode) {
        // Sirve la imagen PNG directamente
        const base64Data = currentQrCode.replace(/^data:image\/png;base64,/, '');
        const img = Buffer.from(base64Data, 'base64');
        res.writeHead(200, {
            'Content-Type': 'image/png',
            'Content-Length': img.length
        });
        res.end(img);
    } else {
        // Pagina de estado si no hay QR o se consulta la raíz
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`
            <html>
                <head><meta http-equiv="refresh" content="5"></head>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h2>Bot de WhatsApp</h2>
                    <p><strong>Estado:</strong> ${statusMessage}</p>
                    ${currentQrCode
                ? '<h3>👇 Escanea este QR 👇</h3><br><img src="/qr" width="300"/>'
                : '<p>Cargando código QR... Esta página se recargará automáticamente en 5 segundos.</p>'
            }
                </body>
            </html>
        `);
    }
}).listen(PORT, () => {
    console.log(`🌐 Servidor HTTP activo en puerto ${PORT}`);
});

wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    logQR: false,
    catchQR: (base64Qrimg) => {
        currentQrCode = base64Qrimg;
        statusMessage = 'Esperando escaneo de código QR';
        console.log('🔄 Nuevo QR generado y listo en /qr');
    },
    statusFind: (statusSession) => {
        console.log('Estado de la sesión:', statusSession);
        if (statusSession === 'isLogged' || statusSession === 'inChat') {
            statusMessage = '✅ Conectado y activo';
            currentQrCode = null;
        }
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
            '--disable-gpu'
        ]
    }
})
    .then((client) => start(client))
    .catch((err) => {
        console.log('Error en WPPConnect:', err);
        statusMessage = 'Error iniciando WhatsApp: ' + err.message;
    });

function start(client) {
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');
    statusMessage = '✅ WhatsApp vinculado correctamente';
    currentQrCode = null;

    client.onMessage(async (message) => {
        if (!message.isGroupMsg && message.body) {
            const telefono = message.from.replace(/@c\.us|@s\.whatsapp\.net/g, '');
            console.log(`📩 Mensaje de ${telefono}: "${message.body}"`);

            try {
                const response = await axios.post('http://127.0.0.1:5000/webhook', {
                    telefono: telefono,
                    texto: message.body
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