import sqlite3
import json
from datetime import datetime
import zoneinfo

DB_NAME = "database.db"
ZONA_HORARIA = zoneinfo.ZoneInfo("America/Bogota")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla de usuarios (Estado en la conversación)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                telefono TEXT PRIMARY KEY,
                estado TEXT NOT NULL,
                datos_temp TEXT
            )
        """)
        
        # Tabla de citas (Agendamientos, planes y sincronización)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono TEXT NOT NULL,
                paciente TEXT NOT NULL,
                tipo_cita TEXT NOT NULL,
                modalidad TEXT NOT NULL,
                fecha_iso TEXT NOT NULL,
                fecha_str TEXT NOT NULL,
                hora_iso TEXT NOT NULL,
                hora_str TEXT NOT NULL,
                estado TEXT NOT NULL, -- 'PENDIENTE_PAGO', 'PAGADO', 'PRESENCIAL_PENDIENTE', 'AGENDADO_MANUAL'
                plan_nombre TEXT,
                citas_restantes INTEGER DEFAULT 1,
                event_id TEXT,
                meet_link TEXT,
                notificado_manual INTEGER DEFAULT 0,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de notificaciones enviadas (Para evitar duplicados del escáner)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                enviado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# --- GESTIÓN DE ESTADOS DE USUARIOS ---

def guardar_estado_usuario(telefono, estado, datos_temp=None):
    tel_limpio = str(telefono).replace("+", "").strip()
    if datos_temp is None:
        datos_temp = {}
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO usuarios (telefono, estado, datos_temp) VALUES (?, ?, ?)",
            (tel_limpio, estado, json.dumps(datos_temp))
        )
        conn.commit()

def obtener_estado_usuario(telefono):
    tel_limpio = str(telefono).replace("+", "").strip()
    with get_connection() as conn:
        row = conn.execute("SELECT estado, datos_temp FROM usuarios WHERE telefono = ?", (tel_limpio,)).fetchone()
        if row:
            return row["estado"], json.loads(row["datos_temp"] or "{}")
        return "INICIO", {}

# --- GESTIÓN DE CITAS ---

def guardar_cita_pendiente(data):
    tel_limpio = str(data['telefono']).replace("+", "").strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO citas (
                telefono, paciente, tipo_cita, modalidad, 
                fecha_iso, fecha_str, hora_iso, hora_str, 
                estado, plan_nombre, citas_restantes, event_id, meet_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tel_limpio, data['paciente'], data['tipo_cita'], data['modalidad'],
            data['fecha_iso'], data['fecha_str'], data['hora_iso'], data['hora_str'],
            data.get('estado', 'PENDIENTE_PAGO'), data.get('plan_nombre'), 
            data.get('citas_restantes', 1), data.get('event_id'), data.get('meet_link')
        ))
        conn.commit()

def obtener_cita_activa(telefono):
    """
    Retorna la cita únicamente si sigue VIGENTE en fecha y hora.
    Si la cita ya ocurrió, se considera vencida y retorna None (libera el agendamiento).
    """
    tel_limpio = str(telefono).replace("+", "").strip()
    tel_con_mas = f"+{tel_limpio}"
    ahora = datetime.now(ZONA_HORARIA)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM citas 
            WHERE (telefono = ? OR telefono = ?) 
              AND estado IN ('PAGADO', 'AGENDADO_MANUAL') 
            ORDER BY id DESC
            """,
            (tel_limpio, tel_con_mas)
        ).fetchall()

        for row in rows:
            cita = dict(row)
            try:
                # Comprobar la vigencia comparando con la fecha/hora actual de Bogotá
                fecha_hora_str = f"{cita['fecha_iso']} {cita['hora_iso']}"
                fecha_hora_cita = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M").replace(tzinfo=ZONA_HORARIA)

                if fecha_hora_cita >= ahora:
                    return cita  # Cita futura/activa encontrada
            except Exception:
                return cita

    return None

def obtener_cita_pendiente(telefono):
    tel_limpio = str(telefono).replace("+", "").strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM citas WHERE (telefono = ? OR telefono = ?) AND estado = 'PENDIENTE_PAGO' ORDER BY id DESC LIMIT 1",
            (tel_limpio, f"+{tel_limpio}")
        ).fetchone()
        return dict(row) if row else None

def confirmar_cita_pagada(telefono, event_id, meet_link=None):
    tel_limpio = str(telefono).replace("+", "").strip()
    with get_connection() as conn:
        conn.execute("""
            UPDATE citas 
            SET estado = 'PAGADO', event_id = ?, meet_link = ? 
            WHERE (telefono = ? OR telefono = ?) AND estado = 'PENDIENTE_PAGO'
        """, (event_id, meet_link, tel_limpio, f"+{tel_limpio}"))
        conn.commit()

def actualizar_evento_cita(cita_id, fecha_iso, fecha_str, hora_iso, hora_str, event_id, meet_link=None):
    with get_connection() as conn:
        conn.execute("""
            UPDATE citas 
            SET fecha_iso = ?, fecha_str = ?, hora_iso = ?, hora_str = ?, event_id = ?, meet_link = ?
            WHERE id = ?
        """, (fecha_iso, fecha_str, hora_iso, hora_str, event_id, meet_link, cita_id))
        conn.commit()

def eliminar_cita_por_telefono(telefono):
    tel_limpio = str(telefono).replace("+", "").strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT event_id FROM citas WHERE (telefono = ? OR telefono = ?) AND estado IN ('PAGADO', 'AGENDADO_MANUAL')", 
            (tel_limpio, f"+{tel_limpio}")
        ).fetchone()
        
        event_id = row["event_id"] if row else None
        conn.execute("DELETE FROM citas WHERE telefono = ? OR telefono = ?", (tel_limpio, f"+{tel_limpio}"))
        conn.commit()
        return event_id

def existe_evento_registrado(event_id):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM citas WHERE event_id = ?", (event_id,)).fetchone()
        return row is not None

# --- DEDUPLICACIÓN DE ESCÁNER DE CALENDARIO Y NOTIFICACIONES ---

def evento_ya_notificado(event_id):
    """Verifica si un evento de Google Calendar ya fue procesado por el escáner."""
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM notificaciones_enviadas WHERE event_id = ?", (event_id,)).fetchone()
        return row is not None

def registrar_notificacion_enviada(event_id):
    """Registra que un evento ya fue procesado para no duplicar mensajes."""
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO notificaciones_enviadas (event_id) VALUES (?)", (event_id,))
        conn.commit()

def registrar_notificacion(*args, **kwargs):
    """Alias flexible compatible con múltiples parámetros para el escáner de segundo plano."""
    event_id = kwargs.get('event_id') or (args[0] if args else None)
    if event_id:
        registrar_notificacion_enviada(event_id)
    return True

def obtener_todas_notificaciones(limite=100):
    """Obtiene el historial de citas y notificaciones registradas."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM citas ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return [dict(r) for r in rows]

# Inicializar BD al importar la base de datos
init_db()