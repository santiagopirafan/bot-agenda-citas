const wppconnect = require('@wppconnect-team/wppconnect');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

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