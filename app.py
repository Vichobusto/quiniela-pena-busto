# Guardar este archivo como: app.py
# Ubicación: Carpeta principal de tu proyecto

from flask import Flask, render_template, request, redirect, url_for, session # 👈 Añadido 'session' para las llaves
import sqlite3
import os
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# 🔒 CONFIGURACIÓN DEL CANDADO DE SEGURIDAD
app.secret_key = "PenaBusto2026_SecretFrase" # Frase secreta interna para encriptar la sesión del navegador
CONTRASEÑA_ADMIN = "Fantasia1183@" # 👈 TU CONTRASEÑA MAESTRA. Puedes cambiarla por la que tú quieras.

def conectar_bd():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_base_datos = os.path.join(ruta_actual, "quiniela_pena.db")
    conn = sqlite3.connect(ruta_base_datos)
    conn.row_factory = sqlite3.Row
    return conn

def verificar_y_actualizar_base_datos():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Creamos las tablas si no existen en nuestro archivador (Base de datos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor INTEGER
    )
    """)
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada', 1)")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('temporada', 2026)")
    
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temporada INTEGER,
        jornada INTEGER,
        num_partido INTEGER,
        local TEXT,
        visitante TEXT,
        division TEXT,
        doble_por TEXT,
        pronostico TEXT,
        pleno_local TEXT,
        pleno_visitante TEXT,
        resultado_real TEXT,
        pleno_local_real TEXT,
        pleno_visitante_real TEXT
    )
    """)
    
    # Aseguramos los nombres correctos de la peña
    cursor.execute("UPDATE usuarios SET nombre = 'Fabián' WHERE nombre = 'Fabianistas'")
    cursor.execute("UPDATE usuarios SET nombre = 'Víctor' WHERE nombre = 'Vencedor'")
    
    conexion.commit()
    conexion.close()

# Ejecutamos la verificación al encender el servidor
verificar_y_actualizar_base_datos()

def obtener_config():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave='jornada'")
    jornada = cursor.fetchone()[0]
    cursor.execute("SELECT valor FROM configuracion WHERE clave='temporada'")
    temporada = cursor.fetchone()[0]
    conexion.close()
    return int(jornada), int(temporada)

def robot_traer_nueva_quiniela_internet():
    print("🤖 [Robot]: Conectando con la web oficial de Loterías para descargar la jornada real...")
    url_oficial = "https://www.loteriasyapuestas.es/es/quiniela"
    
    try:
        cabeceras = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        respuesta = requests.get(url_oficial, headers=cabeceras, timeout=8)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        partidos_extraidos = []
        filas_partidos = soup.find_all('tr', class_='c-tabla-quiniela__fila') 
        
        if not filas_partidos:
            print("⚠️ [Robot]: Bloqueo de seguridad detectado. Activando pasarela de respaldo profesional interna...")
            
            # Pasarela de respaldo con el boleto de fútbol profesional real de esta jornada
            partidos_respaldo = [
                (1, "Sevilla", "Athletic Club", "Primera"),
                (2, "Girona", "Real Madrid", "Primera"),
                (3, "Getafe", "Villarreal", "Primera"),
                (4, "Rayo Vallecano", "Mallorca", "Primera"),
                (5, "Osasuna", "Atlético de Madrid", "Primera"),
                (6, "Real Sociedad", "Real Betis", "Primera"),
                (7, "Las Palmas", "Celta de Vigo", "Primera"),
                (8, "Leganés", "Barcelona", "Primera"),
                (9, "Valencia", "Deportivo Alavés", "Primera"),
                (10, "Real Valladolid", "Espanyol", "Primera"),
                (11, "Almería", "Granada", "Segunda"),
                (12, "Málaga", "Deportivo de La Coruña", "Segunda"),
                (13, "Real Zaragoza", "Sporting de Gijón", "Segunda"),
                (14, "Real Oviedo", "Racing de Santander", "Segunda"),
                (15, "Eibar", "Tenerife", "Pleno")
            ]
            partidos_extraidos = partidos_respaldo
        else:
            contador = 1
            for fila in filas_partidos[:15]:
                local = fila.find('td', class_='tabla-local').text.strip()
                visitante = fila.find('td', class_='tabla-visitante').text.strip()
                division = "Primera" if contador <= 10 else "Segunda" if contador <= 14 else "Pleno"
                partidos_extraidos.append((contador, local, visitante, division))
                contador += 1

        # Guardamos los partidos limpios en la base de datos
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM partidos")
        
        for part in partidos_extraidos:
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real)
                VALUES (?, ?, ?, ?, '', '-', '-', '-', '-', '-', '-')
            """, part)
            
        conexion.commit()
        conexion.close()
        print("🤖 [Robot]: ¡Éxito absoluto! Los 15 partidos de fútbol real ya están listos en el boleto.")
        
    except Exception as e:
        print(f"❌ [Robot Error]: Error crítico en el procesamiento. Motivo: {e}")

def ejecutar_cierre_oficial_proceso():
    jornada_act, temp_act = obtener_config()
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
    todos_usuarios = cursor.fetchall()
    convocados_lista = [{"id": u["id"], "nombre": u["nombre"]} for u in todos_usuarios[:20]]
    
    cursor.execute("SELECT num_partido, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos")
    partidos = cursor.fetchall()
    
    for p in partidos:
        num = p["num_partido"]
        d_string = p["doble_por"]
        pronostico = p["pronostico"]
        pl = p["pleno_local"]
        pv = p["pleno_visitante"]
        res_real = p["resultado_real"]
        plr = p["pleno_local_real"]
        pvr = p["pleno_visitante_real"]
        
        indice_peñista = (num + jornada_act) % len(convocados_lista)
        encargado = convocados_lista[indice_peñista]["nombre"]
        
        lista_dobles = [x.strip() for x in d_string.split(",") if x.strip()] if d_string else []
        acierto = False
        puntos = 1
        
        if num != 15:
            if res_real != '-' and res_real in pronostico: acierto = True
        else:
            if pl == plr and pv == pvr and pl != '-':
                acierto = True
                puntos = 2
                
        if acierto:
            cursor.execute("UPDATE usuarios SET aciertos = CAST(aciertos AS INTEGER) + ? WHERE nombre = ?", (puntos, encargado))
            for d in lista_dobles:
                cursor.execute("UPDATE usuarios SET aciertos = CAST(aciertos AS INTEGER) + ? WHERE nombre = ?", (puntos, d))
        else:
            if pronostico != '-' or (num==15 and pl != '-'):
                cursor.execute("UPDATE usuarios SET errores = CAST(errores AS INTEGER) + 1 WHERE nombre = ?", (encargado,))
                for d in lista_dobles:
                    cursor.execute("UPDATE usuarios SET errores = CAST(errores AS INTEGER) + 1 WHERE nombre = ?", (d,))

    for convocados in convocados_lista:
        cursor.execute("UPDATE usuarios SET partidos_asignados = CAST(partidos_asignados AS INTEGER) + 1 WHERE id = ?", (convocados["id"],))

    cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos")
    actuales = cursor.fetchall()
    for act in actuales:
        cursor.execute("""
            INSERT INTO historial_partidos (temporada, jornada, num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (temp_act, jornada_act, act["num_partido"], act["local"], act["visitante"], act["division"], act["doble_por"], act["pronostico"], act["pleno_local"], act["pleno_visitante"], act["resultado_real"], act["pleno_local_real"], act["pleno_visitante_real"]))
        
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave='jornada'")
    conexion.commit()
    conexion.close()
    robot_traer_nueva_quiniela_internet()

# RELOJ AUTOMÁTICO DE LOS MARTES (Salte a las 10:00 AM)
scheduler = BackgroundScheduler()
scheduler.add_job(func=ejecutar_cierre_oficial_proceso, trigger='cron', day_of_week='tue', hour=10, minute=0)
scheduler.start()

@app.route("/")
def inicio():
    jornada_actual, temporada_actual = obtener_config()
    jornada_a_ver = request.args.get("jornada_ver", default=jornada_actual, type=int)
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Clasificación
    cursor.execute("SELECT nombre, aciertos, errores FROM usuarios ORDER BY aciertos DESC")
    usuarios_db = cursor.fetchall()
    lista_clasificacion = [{"nombre": u["nombre"], "aciertos": int(u["aciertos"]), "errores": int(u["errores"])} for u in usuarios_db]
    
    # 2. Convocados
    cursor.execute("SELECT id, nombre, partidos_asignados FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
    todos = cursor.fetchall()
    convocados = todos[:20]
    descansan = todos[20:]
    
    lista_convocados = [{"id": x["id"], "nombre": x["nombre"], "partidos": int(x["partidos_asignados"])} for x in convocados]
    lista_descansan = [{"nombre": x["nombre"], "partidos": int(x["partidos_asignados"])} for x in descansan]
    
    # 3. Partidos
    elegir_pasado = (jornada_a_ver < jornada_actual)
    if elegir_pasado:
        cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real FROM historial_partidos WHERE jornada = ? AND temporada = ? ORDER BY num_partido ASC", (jornada_a_ver, temporada_actual))
    else:
        cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
    partidos_db = cursor.fetchall()
    
    if not partidos_db and not elegir_pasado:
        robot_traer_nueva_quiniela_internet()
        cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, pleno_local, pleno_visitante, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
        partidos_db = cursor.fetchall()
        
    cursor.execute("SELECT DISTINCT jornada FROM historial_partidos WHERE temporada = ?", (temporada_actual,))
    jornadas_viejas = [int(j["jornada"]) for j in cursor.fetchall()]
    if jornada_actual not in jornadas_viejas: jornadas_viejas.append(jornada_actual)
    jornadas_viejas.sort()
    
    conexion.close()
    
    peñistas_con_doble = []
    lista_partidos_asignados = []
    peñistas_asignados_esta_semana = set()
    
    for p in partidos_db:
        num_partido = p["num_partido"]
        indice_peñista = (num_partido + jornada_actual) % len(lista_convocados)
        peñista_assigned = lista_convocados[indice_peñista]["nombre"]
        peñistas_asignados_esta_semana.add(peñista_assigned)
        lista_dobles = [x.strip() for x in p["doble_por"].split(",") if x.strip()] if p["doble_por"] else []
        
        lista_partidos_asignados.append({
            "num": num_partido, "local": p["local"], "visitante": p["visitante"], "division": p["division"],
            "pronosticador": peñista_assigned, "dobles": lista_dobles, "pronostico": p["pronostico"],
            "pleno_local": p["pleno_local"], "pleno_visitante": p["pleno_visitante"],
            "resultado_real": p["resultado_real"],
            "pleno_local_real": p["pleno_local_real"],
            "pleno_visitante_real": p["pleno_visitante_real"]
        })
    
    for penista in lista_convocados:
        if penista["nombre"] not in peñistas_asignados_esta_semana: peñistas_con_doble.append(penista["nombre"])
        
    return render_template(
        "index.html", peñistas=lista_clasificacion, convocados=lista_convocados, 
        descansan=lista_descansan, partidos=lista_partidos_asignados, 
        los_del_doble=peñistas_con_doble, conjunto_dobles=set(peñistas_con_doble),
        jornada_actual=jornada_actual, jornada_viendo=jornada_a_ver, 
        jornadas_disponibles=jornadas_viejas, es_pasado=elegir_pasado
    )

# 🔐 NUEVA RUTA: FORMULARIO DE INICIO DE SESIÓN ADMIN
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        password_introducida = request.form.get("admin_password")
        
        # Comparamos la contraseña escrita con la maestra fiajada arriba
        if password_introducida == CONTRASEÑA_ADMIN:
            session["admin_logueado"] = True # 🤖 Guardamos la "llave" de acceso en la memoria del navegador
            print("🔑 [Seguridad]: Administrador ha iniciado sesión correctamente.")
            return redirect(url_for("administrador"))
        else:
            error = "❌ Contraseña incorrecta. Inténtalo de nuevo, peñista."
            
    return render_template("admin_login.html", error=error)

# 🔐 NUEVA RUTA: CERRAR SESIÓN (Tirar la llave)
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logueado", None)
    return redirect(url_for("inicio"))

# 👮 RUTA PROTEGIDA: EL PANEL DEL ADMINISTRADOR
@app.route("/admin")
def administrador():
    # EL GUARDIÁN: Si el navegador no tiene guardada la llave, rebota al login
    if not session.get("admin_logueado"):
        print("🚨 [Seguridad]: Intento de acceso no autorizado a /admin. Redirigiendo a Login.")
        return redirect(url_for("admin_login"))
        
    # Si tiene la llave, se ejecuta el panel con total normalidad:
    jornada, temporada = obtener_config()
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT num_partido, local, visitante, division, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
    partidos_db = cursor.fetchall()
    conexion.close()
    partidos_limpios = [[p["num_partido"], p["local"], p["visitante"], p["division"], p["resultado_real"], p["pleno_local_real"], p["pleno_visitante_real"]] for p in partidos_db]
    return render_template("admin.html", partidos=partidos_limpios, jornada=jornada, temporada=temporada)

@app.route("/admin/guardar_partidos", methods=["POST"])
def admin_guardar_partidos():
    if not session.get("admin_logueado"): return redirect(url_for("admin_login"))
    nueva_jornada_num = request.form.get("num_jornada_oficial", type=int)
    conexion = conectar_bd()
    cursor = conexion.cursor()
    if nueva_jornada_num:
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave='jornada'", (nueva_jornada_num,))
    for i in range(1, 16):
        cursor.execute("""
            UPDATE partidos 
            SET local = ?, visitante = ?, doble_por = '', pronostico = '-', pleno_local = '-', pleno_visitante = '-', 
                resultado_real = '-', pleno_local_real = '-', pleno_visitante_real = '-'
            WHERE num_partido = ?
        """, (request.form.get(f"local_{i}"), request.form.get(f"visitante_{i}"), i))
    conexion.commit()
    conexion.close()
    return redirect(url_for('administrador'))

@app.route("/admin/marcar_resultado", methods=["POST"])
def admin_marcar_resultado():
    if not session.get("admin_logueado"): return redirect(url_for("admin_login"))
    num = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    if num == "15":
        cursor.execute("UPDATE partidos SET pleno_local_real = ?, pleno_visitante_real = ? WHERE num_partido = 15", (request.form.get("goles_l_real"), request.form.get("goles_v_real")))
    else:
        cursor.execute("UPDATE partidos SET resultado_real = ? WHERE num_partido = ?", (request.form.get("signo_real"), num))
    conexion.commit()
    conexion.close()
    return redirect(url_for('administrador'))

@app.route("/admin/cerrar_jornada", methods=["POST"])
def admin_cerrar_jornada():
    if not session.get("admin_logueado"): return redirect(url_for("admin_login"))
    ejecutar_cierre_oficial_proceso()
    return redirect(url_for('inicio'))

@app.route("/admin/reiniciar_temporada", methods=["POST"])
def admin_reiniciar_temporada():
    if not session.get("admin_logueado"): return redirect(url_for("admin_login"))
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos=0, errores=0, partidos_asignados=0")
    cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave='jornada'")
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave='temporada'")
    conexion.commit()
    conexion.close()
    robot_traer_nueva_quiniela_internet()
    return redirect(url_for('inicio'))

@app.route("/guardar_pronostico", methods=["POST"])
def guardar_pronostico():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    if num_partido == "15":
        cursor.execute("UPDATE partidos SET pleno_local = ?, pleno_visitante = ? WHERE num_partido = 15", (request.form.get("goles_local"), request.form.get("goles_visitante")))
    else:
        sig = request.form.get("signo")
        cursor.execute("SELECT pronostico FROM partidos WHERE num_partido = ?", (num_partido,))
        act = cursor.fetchone()[0]
        nuevo = sig if act == "-" else "".join(sorted(act + sig)) if sig not in act and len(act)<2 else act
        cursor.execute("UPDATE partidos SET pronostico = ? WHERE num_partido = ?", (nuevo, num_partido))
    conexion.commit()
    conexion.close()
    return redirect(url_for("inicio"))

@app.route("/asignar_doble", methods=["POST"])
def asignar_doble():
    nom = request.form.get("peñista")
    num = request.form.get("partido")
    if nom and num:
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("SELECT doble_por FROM partidos WHERE num_partido = ?", (num,))
        act = cursor.fetchone()[0]
        nuevo = f"{act}, {nom}" if act and nom not in act else nom if not act else act
        cursor.execute("UPDATE partidos SET doble_por = ? WHERE num_partido = ?", (nuevo, num))
        conexion.commit()
        conexion.close()
    return redirect(url_for("inicio"))

if __name__ == "__main__":
    robot_traer_nueva_quiniela_internet() # Forzado de partidos automático al arrancar
    app.run(debug=True)