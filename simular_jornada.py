# Guardar este archivo como: simular_jornada.py
import sqlite3
import os

# Aseguramos la ruta exacta del archivo en tu Escritorio
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_base_datos = os.path.join(ruta_actual, "quiniela_pena.db")

conexion = sqlite3.connect(ruta_base_datos)
cursor = conexion.cursor()

print("--- Lanzando actualización para los Peñistas Reales ---")

# Alvaro: 5 aciertos y 1 fallo (Ratio: 5.00)
cursor.execute("UPDATE usuarios SET aciertos = 5, errores = 1 WHERE nombre = 'Alvaro'")

# Vicente: 4 aciertos y 2 fallos (Ratio: 2.00)
cursor.execute("UPDATE usuarios SET aciertos = 4, errores = 2 WHERE nombre = 'Vicente'")

# Susi: 6 aciertos y 0 fallos (Ratio: liderará por tener más aciertos)
cursor.execute("UPDATE usuarios SET aciertos = 6, errores = 0 WHERE nombre = 'Susi'")

# Amez: 2 aciertos y 4 fallos (Ratio: 0.50)
cursor.execute("UPDATE usuarios SET aciertos = 2, errores = 4 WHERE nombre = 'Amez'")

conexion.commit()
conexion.close()

print("¡Datos de la jornada simulados con éxito para tu peña!")