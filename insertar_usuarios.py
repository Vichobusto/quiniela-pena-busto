# Guardar este archivo como: insertar_usuarios.py
import sqlite3
import os

# Aseguramos la ruta exacta para que no cree archivos fantasma en Windows
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_base_datos = os.path.join(ruta_actual, "quiniela_pena.db")

# 1. Nos conectamos al archivador usando la ruta correcta
conexion = sqlite3.connect(ruta_base_datos)
cursor = conexion.cursor()

# 2. LIMPIEZA: Borramos la tabla vieja para estructurarla de cero
cursor.execute("DROP TABLE IF EXISTS usuarios")

# Recreamos la tabla limpia con la nueva columna de turnos
cursor.execute("""
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    aciertos INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,
    partidos_asignados INTEGER DEFAULT 0
)
""")

# 3. LOS 28 MIEMBROS REALES DE LA PEÑA BUSTO
miembros_oficiales = [
    ("Alvaro",), ("Vicente",), ("Susi",), ("Amez",),
    ("Povis",), ("Omar",), ("Javi",), ("Pajudo",),
    ("Alberto",), ("Vilo",), ("Kius",), ("Orlando",),
    ("Valentin",), ("Fabian",), ("Eloy",), ("Panadero",),
    ("Isaac",), ("Ugalde",), ("Ramon",), ("Julio",),
    ("Diego",), ("Jose",), ("Victor",), ("Braulio",),
    ("Juanjo",), ("Marcos",), ("Daniel",), ("Benja",)
]

# 4. Insertamos solo el nombre (los ceros se ponen solos automáticamente)
cursor.executemany("""
INSERT INTO usuarios (nombre)
VALUES (?)
""", miembros_oficiales)

# 5. Guardamos cambios y cerramos
conexion.commit()
conexion.close()

print("¡Los 28 miembros oficiales de la Peña Busto han sido registrados con éxito!")