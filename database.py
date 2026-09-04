import sqlite3
import json

DB_NAME = "database.db"

def init_db():
    """Inicializa la base de datos y crea/actualiza las tablas si no existen."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de estados de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            telefono TEXT PRIMARY KEY,
            estado TEXT DEFAULT 'INICIO',
            datos_temp TEXT DEFAULT '{}',
            nombre TEXT
        )
    ''')
    
    # Tabla de citas agendadas y pendientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono TEXT,
            paciente TEXT,
            fecha TEXT,
            fecha_iso TEXT,
            hora TEXT,
            hora_iso TEXT,
            tipo_cita TEXT,
            event_id TEXT,
            meet_link TEXT,
            estado TEXT DEFAULT 'PENDIENTE'
        )
    ''')
    
    # Migración liviana por si la tabla 'citas' ya existía sin las nuevas columnas
    cursor.execute("PRAGMA table_info(citas)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    columnas_nuevas = {
        'fecha_iso': 'TEXT',
        'hora_iso': 'TEXT',
        'tipo_cita': 'TEXT',
        'meet_link': 'TEXT',
        'estado': "TEXT DEFAULT 'PENDIENTE'"
    }
    
    for col, col_type in columnas_nuevas.items():
        if col not in columnas:
            cursor.execute(f"ALTER TABLE citas ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def obtener_usuario(telefono):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT telefono, estado, datos_temp, nombre FROM usuarios WHERE telefono = ?', (telefono,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "telefono": row[0],
            "estado": row[1],
            "datos_temp": json.loads(row[2]) if row[2] else {},
            "nombre": row[3]
        }
    return None


def guardar_estado_usuario(telefono, estado, datos_temp=None, nombre=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    usuario = obtener_usuario(telefono)
    datos_json = json.dumps(datos_temp) if datos_temp is not None else '{}'

    if usuario:
        cursor.execute('''
            UPDATE usuarios 
            SET estado = ?, datos_temp = ?, nombre = COALESCE(?, nombre)
            WHERE telefono = ?
        ''', (estado, datos_json, nombre, telefono))
    else:
        cursor.execute('''
            INSERT INTO usuarios (telefono, estado, datos_temp, nombre)
            VALUES (?, ?, ?, ?)
        ''', (telefono, estado, datos_json, nombre))

    conn.commit()
    conn.close()


# ==========================================
# FUNCIONES DE GESTIÓN DE CITAS
# ==========================================

def guardar_cita_pendiente(telefono, paciente, fecha_str, fecha_iso, hora_str, hora_iso, tipo_cita="Consulta"):
    """Guarda una pre-reserva con estado PENDIENTE a la espera del pago en Wompi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO citas (telefono, paciente, fecha, fecha_iso, hora, hora_iso, tipo_cita, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
    ''', (telefono, paciente, fecha_str, fecha_iso, hora_str, hora_iso, tipo_cita))
    conn.commit()
    conn.close()


def guardar_cita(telefono, paciente, fecha, hora, event_id=None, meet_link=None, estado='PENDIENTE'):
    """Guarda o actualiza un registro genérico de cita."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO citas (telefono, paciente, fecha, hora, event_id, meet_link, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (telefono, paciente, fecha, hora, event_id, meet_link, estado))
    conn.commit()
    conn.close()


def obtener_cita_pendiente(telefono):
    """Recupera la última pre-reserva pendiente del usuario para confirmarla cuando el pago apruebe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT paciente, fecha, fecha_iso, hora, hora_iso, tipo_cita 
        FROM citas 
        WHERE telefono = ? AND estado = 'PENDIENTE'
        ORDER BY id DESC LIMIT 1
    ''', (telefono,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'paciente': row[0],
            'fecha_str': row[1],
            'fecha_iso': row[2],
            'hora_str': row[3],
            'hora_iso': row[4],
            'tipo_cita': row[5]
        }
    return None


def confirmar_cita_pagada(telefono, event_id, meet_link=None):
    """Actualiza el estado de la cita a 'PAGADO', guarda el ID de Calendar y la URL de Google Meet."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE citas 
        SET estado = 'PAGADO', event_id = ?, meet_link = ?
        WHERE telefono = ? AND estado = 'PENDIENTE'
    ''', (event_id, meet_link, telefono))
    conn.commit()
    conn.close()


def consultar_citas(telefono):
    """Obtiene la última cita (pagada o confirmada) del usuario incluyendo su enlace a Meet."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT paciente, fecha, hora, event_id, meet_link, estado 
        FROM citas 
        WHERE telefono = ? AND estado = 'PAGADO'
        ORDER BY id DESC LIMIT 1
    ''', (telefono,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "paciente": row[0],
            "fecha": row[1],
            "hora": row[2],
            "event_id": row[3],
            "meet_link": row[4],
            "estado": row[5]
        }
    return None


def eliminar_cita(telefono):
    """Elimina las citas registradas asociadas a un número de teléfono."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM citas WHERE telefono = ?', (telefono,))
    conn.commit()
    conn.close()


# Se ejecuta automáticamente al cargar el módulo para crear/actualizar la base de datos
init_db()