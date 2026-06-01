import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 🗄️ FUNCIÓN DE CONEXIÓN A LA BASE DE DATOS
def conectar_bd():
    conexion = sqlite3.connect("quiniela_pena.db")
    return conexion

# 🏗️ VERIFICACIÓN Y CONFIGURACIÓN INICIAL DE LA BASE DE DATOS
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
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada', 66)")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('temporada', 2026)")
    
    # 2. Tabla de partidos (Con pronóstico y resultados reales)
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
    
    # 3. Tabla de usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        aciertos INTEGER DEFAULT 0,
        errores INTEGER DEFAULT 0,
        partidos_asignados INTEGER DEFAULT 0
    )
    """)
    
    # 🚨 INYECCIÓN INDESTRUCTIBLE DE PEÑISTAS REALES
    cursor.execute("DELETE FROM usuarios")
    peñistas_reales = [("Fabián",), ("Víctor",)] 
    cursor.executemany("INSERT INTO usuarios (nombre) VALUES (?)", peñistas_reales)
    
    # 🛠️ REPARACIÓN MAESTRA: Recreamos los 15 partidos base siempre para evitar bloqueos
    cursor.execute("DELETE FROM partidos")
    for i in range(1, 16):
        # Repartimos de forma equitativa quién rellena cada partido para que el HTML no explote
        pronosticador_asignado = "Fabián" if i % 2 == 0 else "Víctor"
        
        if i == 15:
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante, doble_por) 
                VALUES (15, 'España', 'Alemania', 'PLENO', '-', '-', '-', ?)
            """, (pronosticador_assigned if 'pronosticador_assigned' in locals() else pronosticador_asignado,))
        else:
            div_label = "Primera" if i <= 8 else "Segunda"
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronostico, doble_por) 
                VALUES (?, 'Equipo L', 'Equipo V', ?, '-', '')
            """, (i, div_label))
    
    conexion.commit()
    conexion.close()

# Ejecutamos la configuración limpia al arrancar el servidor
verificar_y_actualizar_base_datos()


# 🏠 RUTA PÚBLICA: PORTADA DE LA PEÑA (ENLAZADA AL 100% CON TU INDEX.HTML)
@app.route("/")
def inicio():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Recuperamos la jornada seleccionada en el desplegable (o la activa por defecto)
    jornada_solicitada = request.args.get("jornada_ver", type=int)
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada_activa = cursor.fetchone()[0]
    
    jornada_viendo = jornada_solicitada if jornada_solicitada else jornada_activa
    
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada'")
    temporada = cursor.fetchone()[0]
    
    # 2. Traemos los partidos mapeando los nombres exactos que pide tu index.html (part.num, part.local...)
    cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
    partidos_db = cursor.fetchall()
    
    partidos_limpios = []
    for p in partidos_db:
        # Repartimos dinámicamente los responsables para que salgan en el HTML
        responsable = "Fabián" if p[0] % 2 == 0 else "Víctor"
        
        # Estructuramos la lista de dobles como un array si existe un doble asignado
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
        if partido["pronostico"].strip().upper() == "X": partido["pronostico"] = "X"
        partidos_limpios.append(partido)
    
    # 3. Traemos el Ranking ordenado por aciertos (Variable 'peñistas' en tu HTML)
    cursor.execute("SELECT nombre, aciertos, errores FROM usuarios ORDER BY aciertos DESC, nombre ASC")
    usuarios_db = cursor.fetchall()
    peñistas_lista = []
    for u in usuarios_db:
        peñistas_lista.append({
            "nombre": u[0],
            "aciertos": u[1],
            "errores": u[2]
        })
    
    conexion.close()
    
    # 4. Fabricamos las variables secundarias para que los paneles de abajo no den error
    jornadas_disponibles = [64, 65, 66] # Historial seleccionable
    los_del_doble = ["Fabián", "Víctor"]
    conjunto_dobles = ["Fabián", "Víctor"]
    
    # Listas de Convocados simuladas para alimentar las cajas verdes y rojas
    convocados = [{"nombre": "Fabián", "partidos": 7}, {"nombre": "Víctor", "partidos": 8}]
    descansan = []
    
    return render_template(
        "index.html", 
        partidos=partidos_limpios, 
        peñistas=peñistas_lista,          # Var ranking
        los_del_doble=los_del_doble,      # Var panel dobles
        conjunto_dobles=conjunto_dobles,  # Var control js
        convocados=convocados,            # Var box verde
        descansan=descansan,              # Var box roja
        jornada_viendo=jornada_viendo, 
        jornadas_disponibles=jornadas_disponibles,
        temporada=temporada,
        es_pasado=False
    )


# 🔐 RUTA DE ADMINISTRACIÓN
@app.route("/admin")
def admin_panel():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada'")
    temporada = cursor.fetchone()[0]
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada = cursor.fetchone()[0]
    cursor.execute("SELECT num_partido, local, visitante, division, resultado_real, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
    partidos = cursor.fetchall()
    conexion.close()
    return render_template("admin.html", partidos=partidos, jornada=jornada, temporada=temporada)


# 💾 RUTA PARA GUARDAR LOS PRONÓSTICOS DEL BOLETO
@app.route("/guardar_pronostico", methods=["POST"])
def guardar_pronostico():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    if num_partido == "15":
        cursor.execute("UPDATE partidos SET pleno_local = ?, pleno_visitante = ? WHERE num_partido = 15", (request.form.get("goles_local"), request.form.get("goles_visitante")))
    else:
        sig = request.form.get("signo")
        if sig and sig.strip().upper() == "X": sig = "X"
        cursor.execute("SELECT pronostico FROM partidos WHERE num_partido = ?", (num_partido,))
        act = cursor.fetchone()[0]
        nuevo = sig if act == "-" else "".join(sorted(act + sig)) if sig not in act and len(act)<2 else act
        cursor.execute("UPDATE partidos SET pronostico = ? WHERE num_partido = ?", (nuevo, num_partido))
    conexion.commit()
    conexion.close()
    return redirect(url_for("inicio"))


# 🤖 EL ROBOT POR API INTERNA DE LOTERÍAS DEL ESTADO
def clonar_quiniela_oficial():
    url = "https://www.loteriasyapuestas.es/servicios/feeder/BoletosFormularioFeeder?gameId=LAQU"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9'
    }
    try:
        respuesta = requests.get(url, headers=headers, timeout=12)
        if respuesta.status_code != 200: return False, f"Error HTTP {respuesta.status_code}"
        datos = respuesta.json()
        if not datos or len(datos) == 0 or 'filas' not in datos[0]: return False, "JSON vacío."
        
        jornada_api = datos[0].get('jornada', '66')
        lista_partidos = datos[0]['filas']
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'jornada'", (jornada_api,))
        cursor.execute("DELETE FROM partidos")
        
        contador = 1
        for p in lista_partidos:
            texto_partido = p.get('texto', '')
            if " - " in texto_partido: local, visitante = texto_partido.split(" - ", 1)
            elif "-" in texto_partido: local, visitante = texto_partido.split("-", 1)
            else: local, visitante = texto_partido, "Incógnita"
            
            div_label = "Primera" if contador <= 8 else "Segunda" if contador <= 14 else "PLENO"
            
            if contador <= 14:
                cursor.execute("INSERT INTO partidos (num_partido, local, visitante, division, pronostico) VALUES (?, ?, ?, ?, '-')", (contador, local.strip(), visitante.strip(), div_label))
            elif contador == 15:
                cursor.execute("INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante) VALUES (15, ?, ?, ?, '-', '-', '-')", (local.strip(), visitante.strip(), div_label))
            contador += 1
            if contador > 15: break
                
        conexion.commit()
        conexion.close()
        return True, f"¡Jornada {jornada_api} clonada!"
    except Exception as e:
        return False, f"Fallo: {str(e)}"


# ⚡ RUTA DEL BOTÓN DE CLONACIÓN
@app.route("/admin/clonar_oficial", methods=["POST"])
def admin_clonar_oficial():
    exito, mensaje = clonar_quiniela_oficial()
    print(f"🤖 [Consola de Render]: {mensaje}")
    return redirect("/admin")

# 🔒 ASIGNAR DOBLE AUXILIAR PARA EL SCRIPT JS
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

# 🔒 ESCRUTINIO VACÍO DE SEGURIDAD
@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada(): return redirect("/admin")

# 🚨 REINICIO MAESTRO
@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    conexion.commit()
    conexion.close()
    return redirect("/admin")

# 🖥️ ENLACE INTELIGENTE DE PUERTOS
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)
    