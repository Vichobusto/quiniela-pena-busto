import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 🗄️ FUNCIÓN DE CONEXIÓN A LA BASE DE DATOS (Nuestro archivador de metal)
def conectar_bd():
    conexion = sqlite3.connect("quiniela_pena.db")
    return conexion


# 🏗️ VERIFICACIÓN Y CONFIGURACIÓN INICIAL DE LA BASE DE DATOS
def verificar_y_actualizar_base_datos():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Tabla de configuración (Guarda jornada y temporada actual)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor INTEGER
    )
    """)
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada', 1)")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('temporada', 2026)")
    
    # 2. Tabla de partidos (Guarda los 15 encuentros del boleto)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_partido INTEGER NOT NULL,
        local TEXT NOT NULL,
        visitante TEXT NOT NULL,
        division TEXT NOT NULL,
        doble_por TEXT DEFAULT '',
        pronostico TEXT DEFAULT '-',      
        pleno_local TEXT DEFAULT '-',     
        pleno_visitante TEXT DEFAULT '-',
        resultado_real TEXT DEFAULT '-',       
        pleno_local_real TEXT DEFAULT '-',  
        pleno_visitante_real TEXT DEFAULT '-'
    )
    """)
    
    # 3. Tabla de usuarios (La plantilla oficial de la peña)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        aciertos INTEGER DEFAULT 0,
        errores INTEGER DEFAULT 0,
        partidos_asignados INTEGER DEFAULT 0
    )
    """)
    
    # 🛡️ BLINDAJE DE DATOS: Solo insertamos los 28 peñistas si la tabla está vacía.
    # Así evitamos borrar los puntos manuales o acumulados cuando el servidor se reinicie.
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        peñistas_reales = [
            ("Fabián",), ("Víctor",), ("Vicente",), ("Jose",), ("Orly",), 
            ("Alberto",), ("Alvaro",), ("Benja",), ("Braulio",), ("Dani",), 
            ("Diego",), ("Eloy",), ("Isaac",), ("Javi",), ("Povis",), 
            ("Juanjo",), ("Julio",), ("Marcos",), ("Omar",), ("Amez",), 
            ("Paju",), ("Pana",), ("Kius",), ("Ramon",), ("Susi",), 
            ("Ugalde",), ("Valentin",), ("Vilo",)
        ]
        cursor.executemany("INSERT INTO usuarios (nombre) VALUES (?)", peñistas_reales)
    
    # 🛠️ Creamos los 15 huecos base si la tabla de partidos está vacía
    cursor.execute("SELECT COUNT(*) FROM partidos")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 16):
            if i == 15:
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante, doble_por) 
                    VALUES (15, 'Equipo Local 15', 'Equipo Visitante 15', 'PLENO', '-', '-', '-', '')
                """)
            else:
                div_label = "Primera" if i <= 8 else "Segunda"
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico, doble_por) 
                    VALUES (?, 'Equipo Local', 'Equipo Visitante', ?, '-', '')
                """, (i, div_label))
    
    conexion.commit()
    conexion.close()


# Arrancamos y verificamos la base de datos al iniciar la aplicación
verificar_y_actualizar_base_datos()


# 🏠 RUTA PÚBLICA: PORTADA DE LA PEÑA
@app.route("/")
def inicio():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    jornada_solicitada = request.args.get("jornada_ver", type=int)
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada_activa = cursor.fetchone()[0]
    jornada_viendo = jornada_solicitada if jornada_solicitada else jornada_activa
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada'")
    temporada = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT num_partido, local, visitante, division, doble_por, pronostico, 
               resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real 
        FROM partidos ORDER BY num_partido ASC
    """)
    partidos_db = cursor.fetchall()
    
    cursor.execute("SELECT nombre FROM usuarios ORDER BY id ASC")
    todos_usuarios = [u[0] for u in cursor.fetchall()]
    
    partidos_limpios = []
    for p in partidos_db:
        idx_resp = (p[0] - 1) % len(todos_usuarios) if todos_usuarios else 0
        responsable = todos_usuarios[idx_resp] if todos_usuarios else "Peñista"
        lista_dobles_partido = [p[4]] if (p[4] and p[4] != "") else []
        
        partido = {
            "num": p[0],
            "local": p[1],
            "visitante": p[2],
            "division": p[3],
            "doble_por": p[4],
            "dobles": lista_dobles_partido,
            "pronosticador": responsable,
            "pronostico": p[5] if p[5] else "-",
            "resultado_real": p[6] if p[6] else "-",
            "pleno_local": p[7],
            "pleno_visitante": p[8],
            "pleno_local_real": p[9],
            "pleno_visitante_real": p[10]
        }
        if p[5] and p[5].strip().upper() == "X":
            partido["pronostico"] = "X"
        partidos_limpios.append(partido)
    
    # Ordenamos el ranking por mayor número de aciertos y, en caso de empate, alfabéticamente
    cursor.execute("SELECT nombre, aciertos, errores FROM usuarios ORDER BY aciertos DESC, errores ASC, nombre ASC")
    usuarios_db = cursor.fetchall()
    peñistas_lista = [{"nombre": u[0], "aciertos": u[1], "errores": u[2]} for u in usuarios_db]
    
    conexion.close()
    
    # Los 5 encargados de los dobles semanales
    los_del_doble = todos_usuarios[0:5] if len(todos_usuarios) >= 5 else todos_usuarios
    
    # 20 convocados y 8 en la grada
    convocados = [{"nombre": name, "partidos": 10} for name in todos_usuarios[:20]]
    descansan = [{"nombre": name, "partidos": 8} for name in todos_usuarios[20:]]
    
    return render_template(
        "index.html", 
        partidos=partidos_limpios, 
        peñistas=peñistas_lista,          
        los_del_doble=los_del_doble,      
        conjunto_dobles=los_del_doble,  
        convocados=convocados,            
        descansan=descansan,              
        jornada_viendo=jornada_viendo, 
        jornadas_disponibles=[1, 2, 3, jornada_activa],
        temporada=temporada,
        es_pasado=False
    )


# 🔐 RUTA DEL PANEL DE ADMINISTRACIÓN
@app.route("/admin")
def admin_panel():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada'")
    temporada = cursor.fetchone()[0]
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT num_partido, local, visitante, division, resultado_real, pleno_local_real, pleno_visitante_real 
        FROM partidos ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    # Cargamos los 28 peñistas para poder editar sus puntos manualmente en el Bloque 3.B
    cursor.execute("SELECT id, nombre, aciertos, errores FROM usuarios ORDER BY nombre ASC")
    usuarios = cursor.fetchall()
    
    conexion.close()
    return render_template("admin.html", partidos=partidos, jornada=jornada, temporada=temporada, usuarios=usuarios)


# 💾 RUTA PARA GUARDAR LOS PRONÓSTICOS DEL BOLETO DESDE LA PORTADA
@app.route("/guardar_pronostico", methods=["POST"])
def guardar_pronostico():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if num_partido == "15":
        cursor.execute("""
            UPDATE partidos 
            SET pleno_local = ?, pleno_visitante = ? 
            WHERE num_partido = 15
        """, (request.form.get("goles_local"), request.form.get("goles_visitante")))
    else:
        sig = request.form.get("signo")
        # Si no viene signo (petición de limpieza de un doble anterior), reseteamos la casilla
        if not sig:
            cursor.execute("UPDATE partidos SET pronostico = '-', doble_por = '' WHERE num_partido = ?", (num_partido,))
        else:
            if sig.strip().upper() == "X":
                sig = "X"
            cursor.execute("SELECT pronostico FROM partidos WHERE num_partido = ?", (num_partido,))
            act = cursor.fetchone()[0]
            nuevo = sig if act == "-" else "".join(sorted(act + sig)) if sig not in act and len(act) < 2 else act
            cursor.execute("UPDATE partidos SET pronostico = ? WHERE num_partido = ?", (nuevo, num_partido))
            
    conexion.commit()
    conexion.close()
    return redirect(url_for("inicio"))


# 🔥 RUTA PARA FIRMAR UN DOBLE EN UN PARTIDO
@app.route("/asignar_doble", methods=["POST"])
def asignar_doble():
    peñista = request.form.get("peñista")
    partido = request.form.get("partido")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE partidos SET doble_por = ? WHERE num_partido = ?", (peñista, partido))
    conexion.commit()
    conexion.close()
    return "OK", 200


# 📋 RUTA ESCÁNER INTELIGENTE: PEGAR LOS 15 PARTIDOS OFICIALES EN 5 SEGUNDOS
@app.route("/admin/pegar_boleto", methods=["POST"])
def pegar_boleto():
    texto_bruto = request.form.get("texto_partidos", "")
    lineas = texto_bruto.strip().split("\n")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM partidos")
    
    contador = 1
    for linea in lineas:
        linea_limpia = linea.strip()
        if not linea_limpia:
            continue
            
        if " - " in linea_limpia:
            local, visitante = linea_limpia.split(" - ", 1)
        elif "-" in linea_limpia:
            local, visitante = linea_limpia.split("-", 1)
        else:
            local, visitante = linea_limpia, "Visitante"
            
        local = local.lstrip("0123456789.-) ").strip()
        visitante = visitante.strip()
        
        if contador <= 14:
            div_label = "Primera" if contador <= 8 else "Segunda / Fem"
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico) 
                VALUES (?, ?, ?, ?, '-')
            """, (contador, local, visitante, div_label))
        elif contador == 15:
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante) 
                VALUES (15, ?, ?, 'PLENO', '-', '-', '-')
            """, (local, visitante))
            
        contador += 1
        if contador > 15:
            break
            
    conexion.commit()
    conexion.close()
    print(f"✅ [ESCÁNER]: Se han cargado {contador - 1} partidos exactos pegados por el presidente.")
    return redirect("/admin")


# 📝 RUTA PARA GUARDAR EDICIÓN MANUAL DE PARTIDOS Y Nº DE JORNADA (Bloque 2 de /admin)
@app.route("/admin/guardar_partidos", methods=["POST"])
def guardar_partidos():
    num_jornada = request.form.get("num_jornada_oficial", type=int, default=1)
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'jornada'", (num_jornada,))
    
    for i in range(1, 16):
        local = request.form.get(f"local_{i}", "").strip()
        visitante = request.form.get(f"visitante_{i}", "").strip()
        if local and visitante:
            cursor.execute("""
                UPDATE partidos 
                SET local = ?, visitante = ?, pronostico = '-', doble_por = '', resultado_real = '-', pleno_local = '-', pleno_visitante = '-', pleno_local_real = '-', pleno_visitante_real = '-'
                WHERE num_partido = ?
            """, (local, visitante, i))
            
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 🎯 RUTA PARA MARCAR EL RESULTADO REAL DE CADA PARTIDO (1, X, 2 o goles del Pleno)
@app.route("/admin/marcar_resultado", methods=["POST"])
def marcar_resultado():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if num_partido == "15":
        goles_l = request.form.get("goles_l_real")
        goles_v = request.form.get("goles_v_real")
        cursor.execute("""
            UPDATE partidos 
            SET pleno_local_real = ?, pleno_visitante_real = ? 
            WHERE num_partido = 15
        """, (goles_l, goles_v))
    else:
        signo_real = request.form.get("signo_real")
        cursor.execute("""
            UPDATE partidos 
            SET resultado_real = ? 
            WHERE num_partido = ?
        """, (signo_real, num_partido))
        
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 🏆 RUTA PARA CALCULAR ACIERTOS Y ACTUALIZAR LA CLASIFICACIÓN AUTOMÁTICAMENTE (Bloque 3)
@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre FROM usuarios ORDER BY id ASC")
    todos_usuarios = [u[0] for u in cursor.fetchall()]
    
    cursor.execute("""
        SELECT num_partido, pronostico, resultado_real, doble_por 
        FROM partidos 
        WHERE num_partido <= 14 
        ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    for p in partidos:
        num = p[0]
        pronostico_pena = p[1] or "-"
        resultado_tele = p[2] or "-"
        quien_puso_doble = p[3] or ""
        
        if resultado_tele == "-":
            continue
            
        idx_resp = (num - 1) % len(todos_usuarios)
        titular = todos_usuarios[idx_resp]
        
        if resultado_tele in pronostico_pena:
            cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (titular,))
            if quien_puso_doble and quien_puso_doble != titular:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (quien_puso_doble,))
        else:
            cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (titular,))
            if quien_puso_doble and quien_puso_doble != titular:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (quien_puso_doble,))

    conexion.commit()
    conexion.close()
    print("🏆 [ESCRUTINIO]: ¡Clasificación de la Peña Busto actualizada con éxito!")
    return redirect("/")


# ✍️ RUTA PARA AJUSTAR ACIERTOS Y ERRORES MANUALMENTE (Bloque 3.B de /admin)
@app.route("/admin/guardar_clasificacion_manual", methods=["POST"])
def guardar_clasificacion_manual():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id FROM usuarios")
    ids_usuarios = [fila[0] for fila in cursor.fetchall()]
    
    for uid in ids_usuarios:
        aciertos_nuevos = request.form.get(f"aciertos_{uid}", type=int, default=0)
        errores_nuevos = request.form.get(f"errores_{uid}", type=int, default=0)
        
        cursor.execute("""
            UPDATE usuarios 
            SET aciertos = ?, errores = ? 
            WHERE id = ?
        """, (aciertos_nuevos, errores_nuevos, uid))
        
    conexion.commit()
    conexion.close()
    print("✅ [ADMIN]: Clasificación manual actualizada correctamente.")
    return redirect("/admin")


# 🚨 RUTA DE REINICIO MAESTRO DE TEMPORADA (Bloque 4 de /admin)
@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    conexion.commit()
    conexion.close()
    return redirect("/admin")


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)