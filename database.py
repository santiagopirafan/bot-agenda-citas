import sqlite3 


db_data = 'database.db'

def crear_tabla():

    conexion = sqlite3.connect(db_data)
    cursor = conexion.cursor()
    cursor.execute(
            """CREATE TABLE IF NOT EXISTS citas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono TEXT,
            paciente TEXT,
            fecha TEXT,
            hora TEXT,
            event_id TEXT
            )
    """)

    conexion.commit()
    conexion.close()

crear_tabla()

def guardar_cita(telefono, paciente, fecha, hora, event_id):

    conexion = sqlite3.connect(db_data)
    cursor = conexion.cursor()
    cursor.execute(
        """ INSERT INTO citas (telefono, paciente, fecha, hora, event_id) VALUES (?,?,?,?,?) """,
        (telefono, paciente, fecha, hora, event_id)
    )

    conexion.commit()
    conexion.close()

    return f"Tu cita para el paciente {paciente} (Tel: {telefono}) el día {fecha} a las {hora} fue guardada con éxito. "

def consultar_citas(telefono):
    conexion = sqlite3.connect(db_data)
    # 1. Esta línea permite acceder por nombre de columna (ej: cita['paciente'])
    conexion.row_factory = sqlite3.Row 
    cursor = conexion.cursor()
    
    cursor.execute(
        """ SELECT paciente, fecha, hora, event_id FROM citas WHERE telefono = ? """, 
        (str(telefono),)
    )
    
    # 2. Usamos fetchone() para traer UN solo registro (un diccionario), NO una lista
    consulta = cursor.fetchone() 
    conexion.close()
    
    if consulta:
        return dict(consulta)
    return None


def eliminar_cita(telefono):

    conexion = sqlite3.connect(db_data)
    cursor = conexion.cursor()
    cursor.execute(
        """ DELETE FROM citas WHERE telefono = ? """, (telefono,)
    )

    conexion.commit()

    conexion.close()

    return f"tu {telefono} fue eliminada correctamente"

print(eliminar_cita(1))



