from config import (
    PRECIO_VALORACION,
    PRECIO_PLAN_1,
    PRECIO_PLAN_2,
    PRECIO_PLAN_3,
    LINK_PAGO_VALORACION,
    LINK_PAGO_PLAN_1,
    LINK_PAGO_PLAN_2,
    LINK_PAGO_PLAN_3
)

def obtener_link_pago(tipo_servicio):
    """
    Evalúa el tipo o plan seleccionado y devuelve la tupla (LINK_PAGO, PRECIO).
    """
    tipo = str(tipo_servicio).upper()

    if "PLAN_1" in tipo or "PLAN 1" in tipo or "1 CITA" in tipo:
        return LINK_PAGO_PLAN_1, PRECIO_PLAN_1

    elif "PLAN_2" in tipo or "PLAN 2" in tipo or "3 CITAS" in tipo:
        return LINK_PAGO_PLAN_2, PRECIO_PLAN_2

    elif "PLAN_3" in tipo or "PLAN 3" in tipo or "5 CITAS" in tipo:
        return LINK_PAGO_PLAN_3, PRECIO_PLAN_3

    # Valoración inicial o respaldo por defecto
    return LINK_PAGO_VALORACION, PRECIO_VALORACION


def procesar_webhook_wompi(payload):
    """
    Desempaqueta el JSON recibido de Wompi cuando cambia el estado de una transacción.
    """
    try:
        data = payload.get("data", {})
        transaction = data.get("transaction", {})

        estado_pago = transaction.get("status")
        referencia = transaction.get("reference", "")
        monto_in_cents = transaction.get("amount_in_cents", 0)
        monto_cop = monto_in_cents / 100 if monto_in_cents else 0

        # Obtener teléfono desde los datos del cliente o la referencia
        customer_data = transaction.get("customer_data", {})
        phone_number = customer_data.get("phone_number") or referencia

        if phone_number:
            phone_number = str(phone_number).replace('whatsapp:', '').replace('+', '').strip()

        print(f"[WOMPI WEBHOOK] Estado: {estado_pago} | Ref: {referencia} | Valor: ${monto_cop:,.0f} COP | Tel: {phone_number}")

        return {
            "exitoso": estado_pago == "APPROVED",
            "estado": estado_pago,
            "referencia": referencia,
            "monto": monto_cop,
            "telefono": phone_number,
            "transaction_id": transaction.get("id")
        }

    except Exception as e:
        print(f"[ERROR PARSEANDO WEBHOOK WOMPI] {e}")
        return {
            "exitoso": False,
            "estado": "ERROR",
            "referencia": None,
            "monto": 0,
            "telefono": None,
            "transaction_id": None
        }