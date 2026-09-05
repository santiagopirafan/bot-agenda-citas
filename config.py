import os

# --- SERVIDOR Y CONFIGURACIÓN GENERAL ---
PORT = int(os.environ.get("PORT", 5000))
ZONA_HORARIA = "America/Bogota"
DURACION_CITA_MINUTOS = int(os.getenv("DURACION_CITA_MINUTOS", 45))

# --- CREDENCIALES DE META WHATSAPP CLOUD API ---
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_de_verificacion_seguro")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "EAAgl5uomwpIBSZApg0HtAT5nU2e9W672nrulZBTBZBsIIS0TWhE0o9L80kJHXIdoGOt8pG47QvQZCWBIZCay9EWGbweZBzQZCdXnOoIUvpXpYWKJufIc2EIm6qasz7ZC94MqpbEH7ctUZCUcsWHBTK9fLINDHECnBU60ZCBzA5qICIUoV9sLQbGrcvFsu8gczPySqTawZDZD")

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "1243724885499477")

# --- GOOGLE CALENDAR ---
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "santipirafan1@gmail.com")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Frecuencia de revisión para notificaciones de agendamiento manual (en segundos)
INTERVALO_REVISION_CALENDAR = int(os.getenv("INTERVALO_REVISION_CALENDAR", 120))

# --- TARIFAS Y PRECIOS INFORMATIVOS (COP) ---
PRECIO_VALORACION = int(os.getenv("PRECIO_VALORACION", 130000))
PRECIO_CONTROL_EFECTIVO = int(os.getenv("PRECIO_CONTROL_EFECTIVO", 260000))

PRECIO_PLAN_1 = int(os.getenv("PRECIO_PLAN_1", 160000))  # 1 Cita Virtual
PRECIO_PLAN_2 = int(os.getenv("PRECIO_PLAN_2", 405000))  # 3 Citas Virtuales
PRECIO_PLAN_3 = int(os.getenv("PRECIO_PLAN_3", 675000))  # 5 Citas Virtuales

# --- LINKS DE PAGO DE WOMPI POR TARIFA / PLAN ---
LINK_PAGO_VALORACION = os.getenv("LINK_PAGO_VALORACION", "https://checkout.wompi.co/l/valoracion_130k")
LINK_PAGO_PLAN_1 = os.getenv("LINK_PAGO_PLAN_1", "https://checkout.wompi.co/l/plan_1_160k")
LINK_PAGO_PLAN_2 = os.getenv("LINK_PAGO_PLAN_2", "https://checkout.wompi.co/l/plan_2_405k")
LINK_PAGO_PLAN_3 = os.getenv("LINK_PAGO_PLAN_3", "https://checkout.wompi.co/l/plan_3_675k")
LINK_DE_PAGO = LINK_PAGO_VALORACION  # Respaldo de compatibilidad