// ==========================================
// IMPORTACIÓN DE LIBRERÍAS
// ==========================================

// Importamos la librería WPPConnect para gestionar la automatización y conexión con WhatsApp Web
const wppconnect = require('@wppconnect-team/wppconnect');

// Importamos Axios para realizar peticiones HTTP POST hacia nuestro servidor Flask (Python)
const axios = require('axios');


// ==========================================
// INICIALIZACIÓN DE LA SESIÓN DE WHATSAPP
// ==========================================

// 'wppconnect.create' inicia una nueva instancia del cliente de WhatsApp con configuraciones específicas
wppconnect.create({
    // Nombre identificador para la sesión activa de WhatsApp
    session: 'bot-citas',

    // Callback que captura el código QR cuando WhatsApp solicita vinculación
    catchQR: (base64Qrimg, asciiQR) => {
        // Mensaje indicador para identificar el QR dentro de la consola
        console.log('--- ESCANEA ESTE CÓDIGO QR ---');

        // Imprime el código QR directamente en texto ASCII dentro de los logs (ideal para la nube/Render)
        console.log(asciiQR);
    },

    // Callback para rastrear los cambios en el estado de la conexión de la sesión (ej: 'isLogged', 'notLogged')
    statusFind: (statusSession, session) => {
        // Muestra en consola el estado actual de la sesión
        console.log('Estado de la sesión:', statusSession);
    },

    // Opciones de configuración de Puppeteer (navegador headless Chromium)
    puppeteerOptions: {
        // Carpeta local donde se guardarán los tokens para no pedir QR en cada reinicio
        userDataDir: './tokens/bot-citas',

        // Argumentos de optimización de Chromium indispensables para entornos con recursos reducidos como Render
        args: [
            '--no-sandbox',                      // Desactiva el aislamiento de procesos por seguridad para permitir ejecución en contenedores Docker
            '--disable-setuid-sandbox',        // Complemento de no-sandbox para permisos dentro de Linux
            '--disable-dev-shm-usage',          // Fuerza a Puppeteer a usar /tmp en lugar de /dev/shm para evitar crasheos por memoria compartida
            '--disable-accelerated-2d-canvas',  // Desactiva la aceleración 2D por hardware para ahorrar memoria RAM
            '--no-first-run',                   // Omite la tarea de primer arranque de Chromium
            '--no-zygote',                      // Evita la creación de procesos 'zygote' hijo innecesarios
            '--single-process',                 // Ejecuta Chromium en un único proceso para minimizar drásticamente el consumo de RAM
            '--disable-gpu',                    // Desactiva la renderización por GPU (inútil en un servidor sin pantalla)
            '--memory-pressure-off'             // Evita que el navegador lance advertencias de memoria que puedan detener la ejecución
        ]
    }
})
    // Promesa que se ejecuta cuando el cliente inicia correctamente la sesión de WhatsApp
    .then((client) => start(client))
    // Captura y muestra cualquier error que ocurra durante el proceso de inicialización
    .catch((error) => console.log(error));


// ==========================================
// FUNCIÓN PRINCIPAL DE MANEJO DE MENSAJES
// ==========================================

function start(client) {
    // Imprime en consola un mensaje de confirmación una vez vinculada la cuenta
    console.log('✅ ¡WhatsApp vinculado e iniciado con éxito!');

    // Listener que se dispara automáticamente cada vez que llega un nuevo mensaje a WhatsApp
    client.onMessage(async (message) => {

        // Condicional: Evaluamos que NO sea un mensaje de grupo (!isGroupMsg) Y que contenga texto (body)
        if (!message.isGroupMsg && message.body) {

            // Extraemos el número telefónico del remitente removiendo la extensión '@c.us'
            const telefono = message.from.replace('@c.us', '');

            // Guardamos el contenido textual enviado por el usuario
            const texto = message.body;

            // Imprimimos el mensaje recibido en los logs para trazabilidad
            console.log(`📩 Mensaje recibido de ${telefono}: "${texto}"`);

            try {
                // Realizamos una petición POST asíncrona hacia el servidor Flask en el puerto local 5000
                const response = await axios.post('http://127.0.0.1:5000/webhook', {
                    telefono: telefono, // Enviamos el número limpio
                    texto: texto       // Enviamos el mensaje del paciente
                });

                // Verificamos si Flask devolvió una respuesta válida con texto
                if (response.data && response.data.respuesta) {

                    // Enviamos la respuesta devuelta por Flask de vuelta al usuario en WhatsApp
                    await client.sendText(message.from, response.data.respuesta);

                    // Confirmamos el envío en los logs
                    console.log(`📤 Respuesta enviada a ${telefono}`);
                }
            } catch (err) {
                // Capturamos e imprimimos en consola si hubo un error al conectar con Flask (ej: app.py apagado)
                console.error('⚠️ Error al conectar con Flask:', err.message);
            }
        }
    });
}