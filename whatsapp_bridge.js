const wppconnect = require('@wppconnect-team/wppconnect');
const axios = require('axios');
const http = require('http');

let currentQrCode = null; // Guardará la imagen QR más reciente

// Servidor de salud y visualizador de QR en el navegador
const PORT = process.env.PORT || 10000;
http.createServer((req, res) => {
    if (req.url === '/qr' && currentQrCode) {
        // Muestra la imagen QR limpia directamente en el navegador
        const img = Buffer.from(currentQrCode.replace(/^data:image\/png;base64,/, ''), 'base64');
        res.writeHead(200, {
            'Content-Type': 'image/png',
            'Content-Length': img.length
        });
        res.end(img);
    } else {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`
            <h2>Bot de WhatsApp Activo</h2>
            <p>Para ver/escanear el QR actual entra a: <a href="/qr" target="_blank">/qr</a></p>
        `);
    }
}).listen(PORT, () => {
    console.log(`🌐 Servidor activo en puerto ${PORT}`);
});

wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    logQR: false,
    catchQR: (base64Qrimg) => {
        // Guardamos el QR actualizado automáticamente
        currentQrCode = base64Qrimg;
        console.log('🔄 ¡Nuevo código QR generado! Míralo en la URL del servicio /qr');
    },
    statusFind: (statusSession) => {
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
            '--disable-gpu'
        ]
    }
})
    .then((client) => start(client))
    .catch((err) => console.log('Error en WPPConnect:', err));

function start(client) {
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');
    currentQrCode = null; // Limpiamos el QR al iniciar sesión

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