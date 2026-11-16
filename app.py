import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 🗄️ FUNCIÓN DE CONEXIÓN A LA BASE DE DATOS (Nuestro archivador)
def conectar_bd():
    conexion = sqlite3.connect("quiniela_pena.db")
    return conexion

# 🏗️ VERIFICACIÓN Y CONFIGURACIÓN INICIAL DE LA BASE DE DATOS
def verificar_y_actualizar_base_datos():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Tabla de configuración (Guarda jornada y temporada)
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
    
    # 3. Tabla de usuarios (La plantilla oficial)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        aciertos INTEGER DEFAULT 0,
        errores INTEGER DEFAULT 0,
        partidos_asignados INTEGER DEFAULT 0
    )
    """)
    
    # 🚨 PLANTILLA INALTERABLE DE TUS 28 PEÑISTAS REALES
    cursor.execute("DELETE FROM usuarios")
    peñistas_reales = [
        ("Fabián",), ("Víctor",), ("Vicente",), ("Jose",), ("Orly",), 
        ("Alberto",), ("Alvaro",), ("Benja",), ("Braulio",), ("Dani",), 
        ("Diego",), ("Eloy",), ("Isaac",), ("Javi",), ("Povis",), 
        ("Juanjo",), ("Julio",), ("Marcos",), ("Omar",), ("Amez",), 
        ("Paju",), ("Pana",), ("Kius",), ("Ramon",), ("Susi",), 
        ("Ugalde",), ("Valentin",), ("Vilo",)
    ]
    cursor.executemany("INSERT INTO usuarios (nombre) VALUES (?)", peñistas_reales)
    
    # 🛠️ Creamos los 15 huecos base si la tabla está vacía
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

# Arrancamos y verificamos la base de datos al iniciar
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
    
    cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
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
        if p[5] and p[5].strip().upper() == "X": partido["pronostico"] = "X"
        partidos_limpios.append(partido)
    
    cursor.execute("SELECT nombre, aciertos, errores FROM usuarios ORDER BY aciertos DESC, nombre ASC")
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


# 🤖 EL NUEVO ROBOT CONECTADO A LA API OFICIAL DE FOOTBALL-DATA
def clonar_quiniela_oficial():
    # 🔑 ¡ATENCIÓN! Pega aquí dentro tu código secreto del correo entre las comillas
    MI_API_TOKEN = 'f9a7f0df4c834ad2bfaacc3a9997ed8f'
    
    # Pedimos los próximos partidos programados de Primera División (PD) y Champions (CL) para llenar los 15 huecos
    url = "https://api.football-data.org/v4/matches?competitions=PD,CL&status=SCHEDULED,TIMED"
    headers = {
        'X-Auth-Token': MI_API_TOKEN
    }
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=12)
        
        if respuesta.status_code != 200:
            print(f"❌ [ERROR API]: Football-Data respondió con código {respuesta.status_code} - {respuesta.text}")
            return False, f"Error HTTP {respuesta.status_code}"
            
        datos = respuesta.json()
        lista_partidos = datos.get('matches', [])
        
        if len(lista_partidos) == 0:
            print("⚠️ [AVISO API]: No hay partidos programados próximamente en estas competiciones.")
            return False, "Sin partidos programados."
            
        # Sacamos el número de jornada del primer partido que nos llega
        jornada_api = lista_partidos[0].get('matchday', 1)
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'jornada'", (jornada_api,))
        cursor.execute("DELETE FROM partidos")
        
        contador = 1
        for p in lista_partidos:
            # Extraemos los nombres limpios de los equipos desde el JSON oficial
            local = p['homeTeam'].get('shortName') or p['homeTeam'].get('name', 'Local')
            visitante = p['awayTeam'].get('shortName') or p['awayTeam'].get('name', 'Visitante')
            
            # Etiquetamos la competición
            competicion = p['competition'].get('code', 'PD')
            div_label = "Primera" if competicion == "PD" else "PLENO" if contador == 15 else "Segunda"
            
            if contador <= 14:
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
                break # Paramos exactamente al llegar al partido 15
                
        conexion.commit()
        conexion.close()
        print(f"✅ [ÉXITO API]: ¡Se han importado {contador - 1} partidos reales de la Jornada {jornada_api}!")
        return True, f"¡Jornada {jornada_api} cargada con éxito!"
        
    except Exception as e:
        print(f"💥 [FALLO CRÍTICO API]: {str(e)}")
        return False, f"Error técnico: {str(e)}"


@app.route("/admin/clonar_oficial", methods=["POST"])
def admin_clonar_oficial():
    exito, mensaje = clonar_quiniela_oficial()
    return redirect("/admin")

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

@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada(): return redirect("/admin")

@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    conexion.commit()
    conexion.close()
    return redirect("/admin")
# 📋 RUTA NUEVA: ESCÁNER INTELIGENTE PARA PEGAR EL BOLETO OFICIAL EN 5 SEGUNDOS
@app.route("/admin/pegar_boleto", methods=["POST"])
def pegar_boleto():
    # Recogemos el texto completo que has pegado en el cuadro del formulario
    texto_bruto = request.form.get("texto_partidos", "")
    
    # Dividimos el texto línea por línea (cada partido es una línea)
    lineas = texto_bruto.strip().split("\n")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Vaciamos los partidos viejos para meter los 15 nuevos exactos
    cursor.execute("DELETE FROM partidos")
    
    contador = 1
    for linea in lineas:
        linea_limpia = linea.strip()
        if not linea_limpia:
            continue # Si hay una línea en blanco, la saltamos
            
        # Buscamos el guion que separa al equipo local del visitante
        if " - " in linea_limpia:
            local, visitante = linea_limpia.split(" - ", 1)
        elif "-" in linea_limpia:
            local, visitante = linea_limpia.split("-", 1)
        else:
            # Si viene sin guion (ej. separado por tabulador), lo dividimos por la mitad
            local, visitante = linea_limpia, "Visitante"
            
        # Quitamos posibles números delante del nombre (ej: "1. Real Madrid" -> "Real Madrid")
        local = local.lstrip("0123456789.-) ").strip()
        visitante = visitante.strip()
        
        # Asignamos la etiqueta de división según el número de casilla
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
            break # En cuanto llegamos al partido 15, paramos de leer
            
    conexion.commit()
    conexion.close()
    print(f"✅ [ESCÁNER]: Se han cargado {contador - 1} partidos exactos pegados por el presidente.")
    return redirect("/admin")
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)