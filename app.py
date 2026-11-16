import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

# 🔐 LLAVE DE SEGURIDAD PARA LAS SESIONES VIP Y CONTRASEÑA MAESTRA
app.secret_key = "llave_secreta_pena_busto_elite_2026"
PASSWORD_ADMIN = "Fantasia1183@"


# 🗄️ CONEXIÓN AL ARCHIVADOR (Base de datos SQLite)
def conectar_bd():
    return sqlite3.connect("quiniela_pena.db")


# 🏗️ VERIFICACIÓN Y ACTUALIZACIÓN SEGURA DE TABLAS
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
    
    # 2. Tabla de partidos activos (La pizarra de la semana actual)
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
    
    # Migración segura de columna signo_doble por si la base de datos ya existía
    cursor.execute("PRAGMA table_info(partidos)")
    columnas_partidos = [col[1] for col in cursor.fetchall()]
    if "signo_doble" not in columnas_partidos:
        cursor.execute("ALTER TABLE partidos ADD COLUMN signo_doble TEXT DEFAULT ''")
        
    # 3. Tabla de HISTORIAL DE JORNADAS (El álbum de fotos de boletos cerrados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_jornadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jornada INTEGER NOT NULL,
        num_partido INTEGER NOT NULL,
        local TEXT NOT NULL,
        visitante TEXT NOT NULL,
        division TEXT NOT NULL,
        pronosticador TEXT NOT NULL,
        doble_por TEXT DEFAULT '',
        pronostico TEXT DEFAULT '-',
        resultado_real TEXT DEFAULT '-',
        pleno_local TEXT DEFAULT '-',
        pleno_visitante TEXT DEFAULT '-',
        pleno_local_real TEXT DEFAULT '-',
        pleno_visitante_real TEXT DEFAULT '-'
    )
    """)
    
    # 4. Tabla de usuarios (Plantilla oficial de los 28 peñistas)
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


# ⚖️ FUNCIÓN DE REPARTO EQUITATIVO (Nadie repite en el mismo boleto)
def obtener_reparto_equitativo(cursor):
    cursor.execute("SELECT nombre, partidos_asignados FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
    lista_ordenada = cursor.fetchall()
    
    titulares_14 = [u[0] for u in lista_ordenada[:14]]
    dobleros_5 = [u[0] for u in lista_ordenada[14:19]]
    pleno_15_resp = lista_ordenada[19][0] if len(lista_ordenada) > 19 else lista_ordenada[0][0]
    
    convocados_20 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[:20]]
    descansan_8 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[20:]]
    
    return titulares_14, dobleros_5, pleno_15_resp, convocados_20, descansan_8


# 🏠 RUTA PÚBLICA: PORTADA DE LA PEÑA (Soporta jornada activa y jornadas archivadas)
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
    
    # Obtenemos qué jornadas existen en el historial + la jornada activa actual
    cursor.execute("SELECT DISTINCT jornada FROM historial_jornadas ORDER BY jornada ASC")
    jornadas_hist = [fila[0] for fila in cursor.fetchall()]
    jornadas_disponibles = sorted(list(set(jornadas_hist + [jornada_activa])))
    
    titulares_14, dobleros_5, pleno_15_resp, convocados_20, descansan_8 = obtener_reparto_equitativo(cursor)
    
    partidos_limpios = []
    es_pasado = False
    
    # Si el usuario selecciona en el desplegable una jornada anterior ya archivada:
    if jornada_viendo != jornada_activa and jornada_viendo in jornadas_hist:
        es_pasado = True
        cursor.execute("""
            SELECT num_partido, local, visitante, division, pronosticador, doble_por, pronostico, 
                   resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
            FROM historial_jornadas WHERE jornada = ? ORDER BY num_partido ASC
        """, (jornada_viendo,))
        for p in cursor.fetchall():
            lista_dobles = [p[5]] if (p[5] and p[5] != "") else []
            partidos_limpios.append({
                "num": p[0], "local": p[1], "visitante": p[2], "division": p[3],
                "pronosticador": p[4], "doble_por": p[5], "dobles": lista_dobles,
                "pronostico": p[6], "resultado_real": p[7],
                "pleno_local": p[8], "pleno_visitante": p[9],
                "pleno_local_real": p[10], "pleno_visitante_real": p[11]
            })
    else:
        # Mostramos la jornada activa actual
        cursor.execute("""
            SELECT num_partido, local, visitante, division, doble_por, pronostico, 
                   resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real, signo_doble
            FROM partidos ORDER BY num_partido ASC
        """)
        for p in cursor.fetchall():
            num = p[0]
            responsable = titulares_14[num - 1] if num <= 14 else pleno_15_resp
            lista_dobles_partido = [p[4]] if (p[4] and p[4] != "") else []
            partido = {
                "num": num, "local": p[1], "visitante": p[2], "division": p[3],
                "doble_por": p[4], "dobles": lista_dobles_partido, "pronosticador": responsable,
                "pronostico": p[5] if p[5] else "-", "resultado_real": p[6] if p[6] else "-",
                "pleno_local": p[7], "pleno_visitante": p[8],
                "pleno_local_real": p[9], "pleno_visitante_real": p[10],
                "signo_doble": p[11]
            }
            if p[5] and p[5].strip().upper() == "X":
                partido["pronostico"] = "X"
            partidos_limpios.append(partido)
    
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
        jornadas_disponibles=jornadas_disponibles,
        temporada=temporada,
        es_pasado=es_pasado
    )


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


# ==============================================================================
# 🔐 ZONA PROTEGIDA DE ADMINISTRACIÓN
# ==============================================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        clave_introducida = request.form.get("admin_password", "")
        if clave_introducida == PASSWORD_ADMIN:
            session["es_admin"] = True
            return redirect("/admin")
        else:
            return render_template("admin_login.html", error="❌ Contraseña incorrecta. Inténtalo de nuevo.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("es_admin", None)
    return redirect("/")


@app.route("/admin")
def admin_panel():
    if not session.get("es_admin"):
        return render_template("admin_login.html")
        
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


# 📋 ESCÁNER DE PARTIDOS (Pegar 15 partidos)
@app.route("/admin/pegar_boleto", methods=["POST"])
def pegar_boleto():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    texto_bruto = request.form.get("texto_partidos", "")
    lineas = texto_bruto.strip().split("\n")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM partidos")
    
    contador = 1
    for linea in lineas:
        linea_limpia = linea.strip()
        if not linea_limpia or "-" not in linea_limpia:
            continue
            
        if " - " in linea_limpia:
            local, visitante = linea_limpia.split(" - ", 1)
        else:
            local, visitante = linea_limpia.split("-", 1)
            
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


# 🎯 ESCÁNER DE RESULTADOS (Lee parejas exactas: Línea 1 = Partido, Línea 2 = Signo)
@app.route("/admin/pegar_resultados", methods=["POST"])
def pegar_resultados():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    texto_bruto = request.form.get("texto_resultados", "")
    # Limpiamos cualquier línea en blanco que se haya colado al copiar y pegar
    lineas = [l.strip() for l in texto_bruto.strip().split("\n") if l.strip()]
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    num_partido_actual = 1
    # Avanzamos de 2 en 2: en 'i' está el partido y en 'i + 1' está el resultado
    for i in range(0, len(lineas) - 1, 2):
        if num_partido_actual > 15:
            break
            
        resultado = lineas[i + 1].upper().strip()
        
        if num_partido_actual <= 14:
            if resultado in ["1", "X", "2"]:
                cursor.execute("UPDATE partidos SET resultado_real = ? WHERE num_partido = ?", (resultado, num_partido_actual))
                num_partido_actual += 1
        elif num_partido_actual == 15:
            if "-" in resultado:
                goles_l, goles_v = resultado.split("-", 1)
                cursor.execute("""
                    UPDATE partidos 
                    SET pleno_local_real = ?, pleno_visitante_real = ? 
                    WHERE num_partido = 15
                """, (goles_l.strip(), goles_v.strip()))
                num_partido_actual += 1
                
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 📝 GUARDAR EDICIÓN MANUAL DE PARTIDOS
@app.route("/admin/guardar_partidos", methods=["POST"])
def guardar_partidos():
    if not session.get("es_admin"):
        return redirect("/admin")
        
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


# 🎯 MARCAR RESULTADO REAL INDIVIDUAL
@app.route("/admin/marcar_resultado", methods=["POST"])
def marcar_resultado():
    if not session.get("es_admin"):
        return redirect("/admin")
        
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


# 🏆 ESCRUTINIO INDIVIDUAL EXACTO, ARCHIVADO EN HISTORIAL Y ROTACIÓN EQUITATIVA
@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada_actual = cursor.fetchone()[0]
    
    titulares_14, dobleros_5, pleno_15_resp, convocados_20, _ = obtener_reparto_equitativo(cursor)
    
    cursor.execute("""
        SELECT num_partido, local, visitante, division, pronostico, resultado_real, 
               doble_por, signo_doble, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real 
        FROM partidos 
        ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    # Borramos si hubiera un archivo previo de esta misma jornada para evitar duplicados
    cursor.execute("DELETE FROM historial_jornadas WHERE jornada = ?", (jornada_actual,))
    
    for p in partidos:
        num, local, visitante, division = p[0], p[1], p[2], p[3]
        pronostico_pena = p[4] or "-"
        resultado_tele = p[5] or "-"
        quien_doble = p[6] or ""
        signo_del_doble = p[7] or ""
        pleno_l, pleno_v, pleno_l_real, pleno_v_real = p[8], p[9], p[10], p[11]
        
        responsable = titulares_14[num - 1] if num <= 14 else pleno_15_resp
        
        # 1. Guardamos la foto de este partido en el ÁLBUM HISTÓRICO
        cursor.execute("""
            INSERT INTO historial_jornadas (
                jornada, num_partido, local, visitante, division, pronosticador, doble_por, 
                pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (jornada_actual, num, local, visitante, division, responsable, quien_doble, 
              pronostico_pena, resultado_tele, pleno_l, pleno_v, pleno_l_real, pleno_v_real))
        
        # 2. Calculamos aciertos y errores en los primeros 14 partidos
        if num <= 14 and resultado_tele != "-":
            if quien_doble and signo_del_doble:
                signo_titular = pronostico_pena.replace(signo_del_doble, "")
                
                if resultado_tele == signo_titular:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (responsable,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (responsable,))
                    
                if resultado_tele == signo_del_doble:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (quien_doble,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (quien_doble,))
            else:
                if resultado_tele in pronostico_pena:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (responsable,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (responsable,))

    # 3. Rotamos a los 20 convocados sumándoles +1 partido asignado
    for c in convocados_20:
        cursor.execute("UPDATE usuarios SET partidos_asignados = partidos_asignados + 1 WHERE nombre = ?", (c["nombre"],))

    # 4. Avanzamos a la siguiente jornada
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'jornada'")

    conexion.commit()
    conexion.close()
    return redirect("/")


# ✍️ AJUSTE MANUAL DE CLASIFICACIÓN
@app.route("/admin/guardar_clasificacion_manual", methods=["POST"])
def guardar_clasificacion_manual():
    if not session.get("es_admin"):
        return redirect("/admin")
        
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


# 🚨 REINICIO MAESTRO DE TEMPORADA
@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    cursor.execute("DELETE FROM historial_jornadas")
    cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave = 'jornada'")
    conexion.commit()
    conexion.close()
    return redirect("/admin")


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)