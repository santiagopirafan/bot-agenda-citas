const wppconnect = require('@wppconnect-team/wppconnect');
const axios = require('axios');
const fs = require('fs');

wppconnect.create({
    session: 'bot-citas',
    autoClose: 0,
    logQR: false,
    catchQR: (base64Qrimg) => {
        // Guarda la imagen del QR físicamente en disco para que Flask la sirva
        const base64Data = base64Qrimg.replace(/^data:image\/png;base64,/, '');
        fs.writeFileSync('qr.png', base64Data, 'base64');
        console.log('🔄 ¡Nuevo QR guardado en qr.png!');
    },
    statusFind: (statusSession) => {
        console.log('Estado de la sesión:', statusSession);
        if (statusSession === 'isLogged' || statusSession === 'inChat') {
            if (fs.existsSync('qr.png')) fs.unlinkSync('qr.png');
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
    .catch((err) => console.log('Error en WPPConnect:', err));

function start(client) {
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');
    if (fs.existsSync('qr.png')) fs.unlinkSync('qr.png');

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