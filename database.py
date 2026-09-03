import sqlite3
import json

DB_NAME = "database.db"

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
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
    
    # Tabla de citas agendadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono TEXT,
            paciente TEXT,
            fecha TEXT,
            hora TEXT,
            event_id TEXT
        )
    ''')
    
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

def guardar_cita(telefono, paciente, fecha, hora, event_id=None):
    """Guarda un registro de cita agendada."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO citas (telefono, paciente, fecha, hora, event_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (telefono, paciente, fecha, hora, event_id))
    conn.commit()
    conn.close()


def consultar_citas(telefono):
    """Obtiene la última cita registrada asociada al número de teléfono."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT paciente, fecha, hora, event_id 
        FROM citas 
        WHERE telefono = ? 
        ORDER BY id DESC LIMIT 1
    ''', (telefono,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "paciente": row[0],
            "fecha": row[1],
            "hora": row[2],
            "event_id": row[3]
        }
    return None


def eliminar_cita(telefono):
    """Elimina las citas asociadas a un número de teléfono."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM citas WHERE telefono = ?', (telefono,))
    conn.commit()
    conn.close()


# Se ejecuta automáticamente al cargar el módulo para prevenir errores
init_db()