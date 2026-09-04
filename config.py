import os

# --- PRECIOS Y DURACIÓN (Variables Temporales / Editables) ---
PRECIO_PRIMERA_CITA = int(os.getenv("PRECIO_PRIMERA_CITA", 50000))
PRECIO_SEGUIMIENTO = int(os.getenv("PRECIO_SEGUIMIENTO", 30000))
DURACION_CITA_MINUTOS = int(os.getenv("DURACION_CITA_MINUTOS", 30))

# --- LINK DE PAGO DIRECTO ---
LINK_DE_PAGO = os.getenv("LINK_DE_PAGO", "https://checkout.wompi.co/l/test_VPOS_6fb1HX")