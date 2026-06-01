import os
import sqlite3
import requests
from bs4 import BeautifulSoup
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
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('jornada', 1)")
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
    
    # Cimientos: Registramos a los peñistas oficiales si está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        peñistas_iniciales = [("Fabián",), ("Víctor",)]
        cursor.executemany("INSERT INTO usuarios (nombre) VALUES (?)", peñistas_iniciales)
    
    conexion.commit()
    conexion.close()

# Ejecutamos la revisión de la base de datos al arrancar
verificar_y_actualizar_base_datos()


# 🏠 RUTA PÚBLICA: PORTADA DE LA PEÑA (FILTRO BLINDADO CONTRA LAS "X")
@app.route("/")
def inicio():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Traemos los datos de la temporada y jornada actuales
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'temporada'")
    temporada = cursor.fetchone()[0]
    cursor.execute("SELECT valor FROM configuracion WHERE clave = 'jornada'")
    jornada = cursor.fetchone()[0]
    
    # Traemos los partidos de la base de datos
    cursor.execute("SELECT num_partido, local, visitante, division, doble_por, pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real FROM partidos ORDER BY num_partido ASC")
    partidos_db = cursor.fetchall()
    
    # Traemos la lista de usuarios
    cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
    usuarios = [fila[0] for fila in cursor.fetchall()]
    
    conexion.close()
    
    partidos_limpios = []
    for p in partidos_db:
        partido = {
            "num_partido": p[0],
            "local": p[1],
            "visitante": p[2],
            "division": p[3],
            "doble_por": p[4],
            "pronostico": p[5] if p[5] else "-",
            "resultado_real": p[6] if p[6] else "-",
            "pleno_local": p[7],
            "pleno_visitante": p[8],
            "pleno_local_real": p[9],
            "pleno_visitante_real": p[10]
        }
        # Aseguramos que la X no se transforme en Incógnita al pintar la pantalla
        if partido["pronostico"].strip().upper() == "X":
            partido["pronostico"] = "X"
        if partido["resultado_real"].strip().upper() == "X":
            partido["resultado_real"] = "X"
            
        partidos_limpios.append(partido)
        
    return render_template("index.html", partidos=partidos_limpios, usuarios=usuarios, jornada=jornada, temporada=temporada)


# 🔐 RUTA DE ADMINISTRACIÓN: EL DESPACHO SECRETO
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


# 💾 RUTA PARA GUARDAR LOS PRONÓSTICOS DEL BOLETO (BLINDADA CONTRA LA "X")
@app.route("/guardar_pronostico", methods=["POST"])
def guardar_pronostico():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if num_partido == "15":
        cursor.execute("UPDATE partidos SET pleno_local = ?, pleno_visitante = ? WHERE num_partido = 15", (request.form.get("goles_local"), request.form.get("goles_visitante")))
    else:
        sig = request.form.get("signo")
        if sig and sig.strip().upper() == "X":
            sig = "X"
            
        cursor.execute("SELECT pronostico FROM partidos WHERE num_partido = ?", (num_partido,))
        act = cursor.fetchone()[0]
        nuevo = sig if act == "-" else "".join(sorted(act + sig)) if sig not in act and len(act)<2 else act
        
        cursor.execute("UPDATE partidos SET pronostico = ? WHERE num_partido = ?", (nuevo, num_partido))
        
    conexion.commit()
    conexion.close()
    return redirect(url_for("inicio"))


# 📺 RUTA PARA INTRODUCIR LOS RESULTADOS REALES DE LA TELEVISIÓN DESDE EL PANEL
@app.route("/admin/marcar_resultado", methods=["POST"])
def marcar_resultado():
    num_partido = request.form.get("partido_num")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    if num_partido == "15":
        gl = request.form.get("goles_l_real")
        gv = request.form.get("goles_v_real")
        cursor.execute("UPDATE partidos SET pleno_local_real = ?, pleno_visitante_real = ? WHERE num_partido = 15", (gl, gv))
    else:
        sig_real = request.form.get("signo_real")
        if sig_real and sig_real.strip().upper() == "X":
            sig_real = "X"
        cursor.execute("UPDATE partidos SET resultado_real = ? WHERE num_partido = ?", (sig_real, num_partido))
        
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 📝 RUTA PARA REDEFINIR MANUALMENTE LOS EQUIPOS DEL BOLETO
@app.route("/admin/guardar_partidos", methods=["POST"])
def guardar_partidos():
    num_jornada = request.form.get("num_jornada_oficial")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'jornada'", (num_jornada,))
    
    for i in range(1, 16):
        loc = request.form.get(f"local_{i}")
        vis = request.form.get(f"visitante_{i}")
        if loc and vis:
            cursor.execute("UPDATE partidos SET local = ?, visitante = ? WHERE num_partido = ?", (loc, vis, i))
            
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 🤖 EL NUEVO MOTOR DEL ROBOT SCRAPER: CONEXIÓN POR API (INFALIBLE VERANO E INVIERNO)
def clonar_quiniela_oficial():
    # Nos conectamos a la tubería JSON central que alimenta las aplicaciones de Loterías
    url = "https://www.loteriasyapuestas.es/servicios/feeder/BoletosFormularioFeeder?gameId=LAQU"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            return False, f"Error de conexión con Loterías (Código {respuesta.status_code})"
            
        datos = respuesta.json()
        
        if not datos or len(datos) == 0 or 'filas' not in datos[0]:
            return False, "No hay ninguna jornada activa publicada en este momento."
            
        jornada_api = datos[0].get('jornada', '66')
        lista_partidos = datos[0]['filas']
        
        conexion = conectar_bd()
        cursor = conexion.cursor()
        
        # 1. Actualizamos el número de jornada automáticamente
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'jornada'", (jornada_api,))
        
        # 2. Vaciamos los partidos viejos para meter la jornada 66 real
        cursor.execute("DELETE FROM partidos")
        
        contador = 1
        for p in lista_partidos:
            texto_partido = p.get('texto', '')
            if " - " in texto_partido:
                local, visitante = texto_partido.split(" - ", 1)
            else:
                local, visitante = "Equipo Local", "Equipo Visitante"
                
            division = "Especial"
            
            if contador <= 14:
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico)
                    VALUES (?, ?, ?, ?, '-')
                """, (contador, local.strip(), visitante.strip(), division))
            elif contador == 15:
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronostico, pleno_local, pleno_visitante)
                    VALUES (15, ?, ?, ?, '-', '-', '-')
                """, (local.strip(), visitante.strip(), division))
                
            contador += 1
            if contador > 15:
                break
                
        conexion.commit()
        conexion.close()
        return True, f"¡Jornada {jornada_api} clonada con éxito total!"
        
    except Exception as e:
        return False, f"Fallo en la tubería de datos: {str(e)}"


# ⚡ LA RUTA EXACTA DEL BOTÓN ENTRAR (EMPAREJADA CON ADMIN.HTML)
@app.route("/admin/clonar_oficial", methods=["POST"])
def admin_clonar_oficial():
    exito, mensaje = clonar_quiniela_oficial()
    print(f"🤖 [Consola de Render]: {mensaje}")
    return redirect("/admin")


# 🔒 RUTA PARA ARCHIVAR LA JORNADA Y CALCULAR PUNTOS (ESCRUTINIO)
@app.route("/admin/cerrar_jornada", methods=["POST"])
def cerrar_jornada():
    return redirect("/admin")


# 🚨 RUTA PARA REINICIAR LA CLASIFICACIÓN GENERAL A CERO
@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    conexion.commit()
    conexion.close()
    return redirect("/admin")


# 🖥️ ENLACE INTELIGENTE DE PUERTOS (ADAPTADO TANTO PARA TU CASA COMO PARA RENDER)
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)