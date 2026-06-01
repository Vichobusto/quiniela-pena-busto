# Guardar este archivo como: crear_base_datos.py
import sqlite3  # Importamos la librería que maneja las bases de datos

# 1. Conectamos con la base de datos (si el archivo no existe, Python lo creará automáticamente)
conexion = sqlite3.connect("quiniela_pena.db")

# 2. Creamos un "cursor", que es como el lápiz que escribe las órdenes dentro de la base de datos
cursor = conexion.cursor()

# 3. Le damos la orden de crear la tabla de usuarios si no existe todavía
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    aciertos INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,
    partidos_asignados INTEGER DEFAULT 0
)
""")

# 4. Guardamos los cambios de forma definitiva
conexion.commit()

# 5. Cerramos la conexión por seguridad
conexion.close()

print("¡Base de datos y tabla 'usuarios' creadas con éxito!")