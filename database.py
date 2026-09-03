import sqlite3
import os

# Permite override del path de base de datos desde variables de entorno (ideal para Persistent Disk en Render)
DB_PATH = os.environ.get('DATABASE_PATH', 'database.db')

def crear_tabla():
    conexion = sqlite3.connect(DB_PATH)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS citas(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono TEXT,
                paciente TEXT,
                fecha TEXT,
                hora TEXT,
                event_id TEXT
            )"""
        )
        conexion.commit()
    finally:
        conexion.close()

# Se asegura de crear la tabla al importar el módulo
crear_tabla()

def guardar_cita(telefono, paciente, fecha, hora, event_id):
    conexion = sqlite3.connect(DB_PATH)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """INSERT INTO citas (telefono, paciente, fecha, hora, event_id) VALUES (?,?,?,?,?)""",
            (str(telefono).strip(), paciente, fecha, hora, event_id)
        )
        conexion.commit()
        return f"Tu cita para el paciente {paciente} (Tel: {telefono}) el día {fecha} a las {hora} fue guardada con éxito."
    finally:
        conexion.close()

def consultar_citas(telefono):
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row 
    try:
        cursor = conexion.cursor()
        # Trae la cita más reciente registrada para este número
        cursor.execute(
            """SELECT paciente, fecha, hora, event_id FROM citas WHERE telefono = ? ORDER BY id DESC""", 
            (str(telefono).strip(),)
        )
        consulta = cursor.fetchone() 
        if consulta:
            return dict(consulta)
        return None
    finally:
        conexion.close()

def eliminar_cita(telefono):
    conexion = sqlite3.connect(DB_PATH)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """DELETE FROM citas WHERE telefono = ?""", 
            (str(telefono).strip(),)
        )
        conexion.commit()
        return f"La cita asociada al teléfono {telefono} fue eliminada correctamente."
    finally:
        conexion.close()