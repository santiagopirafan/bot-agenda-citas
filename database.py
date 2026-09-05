import sqlite3
import json

DB_NAME = "database.db"

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
        conn.commit()

# --- GESTIÓN DE ESTADOS DE USUARIOS ---

def guardar_estado_usuario(telefono, estado, datos_temp=None):
    if datos_temp is None:
        datos_temp = {}
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO usuarios (telefono, estado, datos_temp) VALUES (?, ?, ?)",
            (telefono, estado, json.dumps(datos_temp))
        )
        conn.commit()

def obtener_estado_usuario(telefono):
    with get_connection() as conn:
        row = conn.execute("SELECT estado, datos_temp FROM usuarios WHERE telefono = ?", (telefono,)).fetchone()
        if row:
            return row["estado"], json.loads(row["datos_temp"] or "{}")
        return "INICIO", {}

# --- GESTIÓN DE CITAS ---

def guardar_cita_pendiente(data):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO citas (
                telefono, paciente, tipo_cita, modalidad, 
                fecha_iso, fecha_str, hora_iso, hora_str, 
                estado, plan_nombre, citas_restantes, event_id, meet_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['telefono'], data['paciente'], data['tipo_cita'], data['modalidad'],
            data['fecha_iso'], data['fecha_str'], data['hora_iso'], data['hora_str'],
            data.get('estado', 'PENDIENTE_PAGO'), data.get('plan_nombre'), 
            data.get('citas_restantes', 1), data.get('event_id'), data.get('meet_link')
        ))
        conn.commit()

def obtener_cita_activa(telefono):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM citas WHERE telefono = ? AND estado IN ('PAGADO', 'PRESENCIAL_PENDIENTE', 'AGENDADO_MANUAL') ORDER BY id DESC LIMIT 1",
            (telefono,)
        ).fetchone()
        return dict(row) if row else None

def obtener_cita_pendiente(telefono):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM citas WHERE telefono = ? AND estado = 'PENDIENTE_PAGO' ORDER BY id DESC LIMIT 1",
            (telefono,)
        ).fetchone()
        return dict(row) if row else None

def confirmar_cita_pagada(telefono, event_id, meet_link=None):
    with get_connection() as conn:
        conn.execute("""
            UPDATE citas 
            SET estado = 'PAGADO', event_id = ?, meet_link = ? 
            WHERE telefono = ? AND estado = 'PENDIENTE_PAGO'
        """, (event_id, meet_link, telefono))
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
    with get_connection() as conn:
        row = conn.execute("SELECT event_id FROM citas WHERE telefono = ? AND estado IN ('PAGADO', 'PRESENCIAL_PENDIENTE', 'AGENDADO_MANUAL')", (telefono,)).fetchone()
        event_id = row["event_id"] if row else None
        conn.execute("DELETE FROM citas WHERE telefono = ?", (telefono,))
        conn.commit()
        return event_id

def existe_evento_registrado(event_id):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM citas WHERE event_id = ?", (event_id,)).fetchone()
        return row is not None

# Inicializar BD al importar la base de datos
init_db()