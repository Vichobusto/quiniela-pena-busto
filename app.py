import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 🗄️ CONEXIÓN AL ARCHIVADOR (Base de datos SQLite)
def conectar_bd():
    return sqlite3.connect("quiniela_pena.db")


# 🏗️ VERIFICACIÓN Y ACTUALIZACIÓN SEGURA DE TABLAS
def verificar_y_actualizar_base_datos():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Tabla de configuración
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor INTEGER
    )
    """)
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada', 1)")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('temporada', 2026)")
    
    # 2. Tabla de partidos (Incluye 'signo_doble' para saber exactamente qué signo firmó el del doble)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_partido INTEGER NOT NULL,
        local TEXT NOT NULL,
        visitante TEXT NOT NULL,
        division TEXT NOT NULL,
        doble_por TEXT DEFAULT '',
        signo_doble TEXT DEFAULT '',
        pronostico TEXT DEFAULT '-',      
        pleno_local TEXT DEFAULT '-',     
        pleno_visitante TEXT DEFAULT '-',
        resultado_real TEXT DEFAULT '-',       
        pleno_local_real TEXT DEFAULT '-',  
        pleno_visitante_real TEXT DEFAULT '-'
    )
    """)
    
    # Migración segura: si tu base de datos antigua aún no tiene 'signo_doble', la añadimos sin borrar datos
    cursor.execute("PRAGMA table_info(partidos)")
    columnas_partidos = [col[1] for col in cursor.fetchall()]
    if "signo_doble" not in columnas_partidos:
        cursor.execute("ALTER TABLE partidos ADD COLUMN signo_doble TEXT DEFAULT ''")
    
    # 3. Tabla de usuarios (Guarda aciertos, errores y el contador equitativo 'partidos_asignados')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        aciertos INTEGER DEFAULT 0,
        errores INTEGER DEFAULT 0,
        partidos_asignados INTEGER DEFAULT 0
    )
    """)
    
    # 🛡️ BLINDAJE: Solo creamos los 28 peñistas si la tabla está vacía
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
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante, doble_por, signo_doble) 
                    VALUES (15, 'Equipo Local 15', 'Equipo Visitante 15', 'PLENO', '-', '-', '-', '', '')
                """)
            else:
                div_label = "Primera" if i <= 8 else "Segunda"
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico, doble_por, signo_doble) 
                    VALUES (?, 'Equipo Local', 'Equipo Visitante', ?, '-', '', '')
                """, (i, div_label))
    
    conexion.commit()
    conexion.close()


verificar_y_actualizar_base_datos()


# ⚖️ FUNCIÓN MAESTRA DE REPARTO EQUITATIVO (Nadie repite en el mismo boleto)
def obtener_reparto_equitativo(cursor):
    # Ordenamos a los 28 peñistas de MENOR a MAYOR número de partidos jugados en el año
    cursor.execute("SELECT nombre, partidos_asignados FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
    lista_ordenada = cursor.fetchall()
    
    # Reparto sin repeticiones:
    # - Puestos 0 al 13 (14 socios): Titulares de los partidos 1 al 14
    # - Puestos 14 al 18 (5 socios): Encargados de los 5 dobles
    # - Puesto 19 (1 socio): Encargado del Pleno al 15
    # - Puestos 20 al 27 (8 socios): Descansan en la grada
    titulares_14 = [u[0] for u in lista_ordenada[:14]]
    dobleros_5 = [u[0] for u in lista_ordenada[14:19]]
    pleno_15_resp = lista_ordenada[19][0] if len(lista_ordenada) > 19 else lista_ordenada[0][0]
    
    convocados_20 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[:20]]
    descansan_8 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[20:]]
    
    return titulares_14, dobleros_5, pleno_15_resp, convocados_20, descansan_8


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
    
    # Obtenemos el reparto equitativo actual
    titulares_14, dobleros_5, pleno_15_resp, convocados_20, descansan_8 = obtener_reparto_equitativo(cursor)
    
    cursor.execute("""
        SELECT num_partido, local, visitante, division, doble_por, pronostico, 
               resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real, signo_doble
        FROM partidos ORDER BY num_partido ASC
    """)
    partidos_db = cursor.fetchall()
    
    partidos_limpios = []
    for p in partidos_db:
        num = p[0]
        if num <= 14:
            responsable = titulares_14[num - 1]
        else:
            responsable = pleno_15_resp
            
        lista_dobles_partido = [p[4]] if (p[4] and p[4] != "") else []
        
        partido = {
            "num": num,
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
            "pleno_visitante_real": p[10],
            "signo_doble": p[11]
        }
        if p[5] and p[5].strip().upper() == "X":
            partido["pronostico"] = "X"
        partidos_limpios.append(partido)
    
    # Ranking ordenado por aciertos (descendente) y errores (ascendente)
    cursor.execute("SELECT nombre, aciertos, errores FROM usuarios ORDER BY aciertos DESC, errores ASC, nombre ASC")
    usuarios_db = cursor.fetchall()
    peñistas_lista = [{"nombre": u[0], "aciertos": u[1], "errores": u[2]} for u in usuarios_db]
    
    conexion.close()
    
    return render_template(
        "index.html", 
        partidos=partidos_limpios, 
        peñistas=peñistas_lista,          
        los_del_doble=dobleros_5,      
        conjunto_dobles=dobleros_5,  
        convocados=convocados_20,            
        descansan=descansan_8,              
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
    
    cursor.execute("SELECT id, nombre, aciertos, errores FROM usuarios ORDER BY nombre ASC")
    usuarios = cursor.fetchall()
    
    conexion.close()
    return render_template("admin.html", partidos=partidos, jornada=jornada, temporada=temporada, usuarios=usuarios)


# 💾 GUARDAR PRONÓSTICO DESDE LA PORTADA
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
        if not sig:
            cursor.execute("UPDATE partidos SET pronostico = '-', doble_por = '', signo_doble = '' WHERE num_partido = ?", (num_partido,))
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


# 🔥 GUARDAR FIRMA Y SIGNO EXACTO DEL DOBLE
@app.route("/asignar_doble", methods=["POST"])
def asignar_doble():
    peñista = request.form.get("peñista")
    partido = request.form.get("partido")
    signo_doble = request.form.get("signo_doble", "")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE partidos SET doble_por = ?, signo_doble = ? WHERE num_partido = ?", (peñista, signo_doble, partido))
    conexion.commit()
    conexion.close()
    return "OK", 200


# 📋 ESCÁNER INTELIGENTE DE BOLETO (Pegar 15 partidos)
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
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico, doble_por, signo_doble) 
                VALUES (?, ?, ?, ?, '-', '', '')
            """, (contador, local, visitante, div_label))
        elif contador == 15:
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante, doble_por, signo_doble) 
                VALUES (15, ?, ?, 'PLENO', '-', '-', '-', '', '')
            """, (local, visitante))
            
        contador += 1
        if contador > 15:
            break
            
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 📝 GUARDAR EDICIÓN MANUAL DE PARTIDOS (Bloque 2 de /admin)
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
                SET local = ?, visitante = ?, pronostico = '-', doble_por = '', signo_doble = '', resultado_real = '-', pleno_local = '-', pleno_visitante = '-', pleno_local_real = '-', pleno_visitante_real = '-'
                WHERE num_partido = ?
            """, (local, visitante, i))
            
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 🎯 MARCAR RESULTADO REAL DE LA TELEVISIÓN (Bloque 1 de /admin)
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


# 🏆 ESCRUTINIO INDIVIDUAL EXACTO Y ROTACIÓN EQUITATIVA (Bloque 3 de /admin)
@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Obtenemos quiénes eran los 20 convocados de esta jornada según el reparto equitativo
    titulares_14, dobleros_5, pleno_15_resp, convocados_20, _ = obtener_reparto_equitativo(cursor)
    
    # 2. Revisamos los 14 partidos evaluables
    cursor.execute("""
        SELECT num_partido, pronostico, resultado_real, doble_por, signo_doble 
        FROM partidos 
        WHERE num_partido <= 14 
        ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    for p in partidos:
        num = p[0]
        pronostico_pena = p[1] or "-"
        resultado_tele = p[2] or "-"
        quien_doble = p[3] or ""
        signo_del_doble = p[4] or ""
        
        if resultado_tele == "-":
            continue
            
        titular = titulares_14[num - 1]
        
        # Caso 1: Este partido tiene un DOBLE firmado por otro compañero
        if quien_doble and signo_del_doble:
            # Deducimos cuál era el signo original del titular quitando el signo del doble
            signo_titular = pronostico_pena.replace(signo_del_doble, "")
            
            # Evaluamos al TITULAR por su signo individual
            if resultado_tele == signo_titular:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (titular,))
            else:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (titular,))
                
            # Evaluamos al DEL DOBLE por su signo individual
            if resultado_tele == signo_del_doble:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (quien_doble,))
            else:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (quien_doble,))
                
        # Caso 2: Partido simple (solo juega el titular)
        else:
            if resultado_tele in pronostico_pena:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (titular,))
            else:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (titular,))

    # 3. Sumamos +1 partido asignado a los 20 convocados de esta semana para que roten la próxima jornada
    for c in convocados_20:
        cursor.execute("UPDATE usuarios SET partidos_asignados = partidos_asignados + 1 WHERE nombre = ?", (c["nombre"],))

    # 4. Avanzamos el número de jornada activa en +1
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'jornada'")

    conexion.commit()
    conexion.close()
    return redirect("/")


# ✍️ AJUSTE MANUAL DE CLASIFICACIÓN (Bloque 3.B de /admin)
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
    return redirect("/admin")


# 🚨 REINICIO MAESTRO DE TEMPORADA (Bloque 4 de /admin)
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