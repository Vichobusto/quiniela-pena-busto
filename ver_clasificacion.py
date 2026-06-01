# Guardar este archivo como: ver_clasificacion.py
import sqlite3

# 1. Nos conectamos a la base de datos
conexion = sqlite3.connect("quiniela_pena.db")
cursor = conexion.cursor()

# 2. Le pedimos que traiga a todos los usuarios de la tabla
cursor.execute("SELECT nombre, aciertos, errores FROM usuarios")
usuarios = cursor.fetchall()  # 'fetchall' recupera todas las filas que encontró

print("\n=== CLASIFICACIÓN DE LA PEÑA ===")

# 3. Recorremos cada usuario con un bucle (for) para calcular su ratio
for u in usuarios:
    nombre = u[0]
    aciertos = u[1]
    errores = u[2]
    
    # Aquí aplicamos la lógica de tu fórmula de Excel:
    # Si los errores son 0, evitamos la división entre cero
    if errores == 0:
        ratio = 0.0  # O el valor inicial que prefieras para el comienzo
    else:
        ratio = aciertos / errores
        
    # Imprimimos los datos ordenados en la terminal
    print(f"Peñista: {nombre} | V: {aciertos} | X: {errores} | Ratio: {ratio:.2f}")

# 4. Cerramos el archivador
conexion.close()