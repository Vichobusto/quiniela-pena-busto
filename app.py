import os
import sqlite3
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

# 🔐 LLAVE DE SEGURIDAD PARA LAS SESIONES VIP Y CONTRASEÑA MAESTRA
app.secret_key = "llave_secreta_pena_busto_elite_2026"
PASSWORD_ADMIN = "Fantasia1183@"

# 🗄️ DIRECCIÓN DE TU BASE DE DATOS PERMANENTE EN NEON
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_e0j8EXSFGwfT@ep-winter-dream-baefyf0x-pooler.c-8.eu-central-1.aws.neon.tech/neondb?sslmode=require"
)


# 🔄 ADAPTADOR INTELIGENTE: Traduce las consultas SQLite a PostgreSQL automáticamente
class CursorPostgresAdaptado:
    def __init__(self, cursor_pg):
        self.cursor = cursor_pg

    def execute(self, sql, params=None):
        sql_pg = sql.replace("?", "%s")
        if params is not None:
            return self.cursor.execute(sql_pg, params)
        return self.cursor.execute(sql_pg)

    def executemany(self, sql, seq_of_params):
        sql_pg = sql.replace("?", "%s")
        return self.cursor.executemany(sql_pg, seq_of_params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class ConexionPostgresAdaptada:
    def __init__(self, conn_pg):
        self.conn = conn_pg

    def cursor(self):
        return CursorPostgresAdaptado(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


# 🔌 CONEXIÓN AL ARCHIVADOR (PostgreSQL permanente en Neon / SQLite local de respaldo)
def conectar_bd():
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        try:
            conn_pg = psycopg2.connect(DATABASE_URL)
            return ConexionPostgresAdaptada(conn_pg)
        except Exception as e:
            print(f"⚠️ No se pudo conectar a PostgreSQL remoto ({e}), usando respaldo local SQLite...")
    return sqlite3.connect("quiniela_pena.db")


# 🏗️ VERIFICACIÓN Y CREACIÓN DE TABLAS EN LA BASE DE DATOS
def verificar_y_actualizar_base_datos():
    conexion = conectar_bd()
    cursor = conexion.cursor()
    es_postgres = isinstance(conexion, ConexionPostgresAdaptada)
    
    tipo_id = "SERIAL PRIMARY KEY" if es_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # 1. Tabla de configuración (jornada, temporada y dobleros manuales)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor INTEGER,
        texto TEXT DEFAULT ''
    )
    """)
    
    if es_postgres:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN IF NOT EXISTS texto TEXT DEFAULT ''")
        cursor.execute("INSERT INTO configuracion (clave, valor, texto) VALUES ('jornada', 1, '') ON CONFLICT (clave) DO NOTHING")
        cursor.execute("INSERT INTO configuracion (clave, valor, texto) VALUES ('temporada', 2026, '') ON CONFLICT (clave) DO NOTHING")
        for d in range(1, 7):
            cursor.execute(f"INSERT INTO configuracion (clave, valor, texto) VALUES ('doblero_manual_{d}', 0, '') ON CONFLICT (clave) DO NOTHING")
    else:
        cursor.execute("PRAGMA table_info(configuracion)")
        cols_cfg = [c[1] for c in cursor.fetchall()]
        if "texto" not in cols_cfg:
            cursor.execute("ALTER TABLE configuracion ADD COLUMN texto TEXT DEFAULT ''")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor, texto) VALUES ('jornada', 1, '')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor, texto) VALUES ('temporada', 2026, '')")
        for d in range(1, 7):
            cursor.execute(f"INSERT OR IGNORE INTO configuracion (clave, valor, texto) VALUES ('doblero_manual_{d}', 0, '')")
    
    # 2. Tabla de partidos activos
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS partidos (
        id {tipo_id},
        num_partido INTEGER NOT NULL,
        local TEXT NOT NULL,
        visitante TEXT NOT NULL,
        division TEXT NOT NULL,
        pronosticador_manual TEXT DEFAULT '',
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
    
    if es_postgres:
        cursor.execute("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS pronosticador_manual TEXT DEFAULT ''")
    else:
        cursor.execute("PRAGMA table_info(partidos)")
        cols = [c[1] for c in cursor.fetchall()]
        if "pronosticador_manual" not in cols:
            cursor.execute("ALTER TABLE partidos ADD COLUMN pronosticador_manual TEXT DEFAULT ''")
        
    # 3. Tabla de HISTORIAL DE JORNADAS
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS historial_jornadas (
        id {tipo_id},
        jornada INTEGER NOT NULL,
        num_partido INTEGER NOT NULL,
        local TEXT NOT NULL,
        visitante TEXT NOT NULL,
        division TEXT NOT NULL,
        pronosticador TEXT NOT NULL,
        doble_por TEXT DEFAULT '',
        signo_doble TEXT DEFAULT '',
        pronostico TEXT DEFAULT '-',
        resultado_real TEXT DEFAULT '-',
        pleno_local TEXT DEFAULT '-',
        pleno_visitante TEXT DEFAULT '-',
        pleno_local_real TEXT DEFAULT '-',
        pleno_visitante_real TEXT DEFAULT '-'
    )
    """)

    if es_postgres:
        cursor.execute("ALTER TABLE historial_jornadas ADD COLUMN IF NOT EXISTS signo_doble TEXT DEFAULT ''")
    else:
        cursor.execute("PRAGMA table_info(historial_jornadas)")
        cols_hist = [c[1] for c in cursor.fetchall()]
        if "signo_doble" not in cols_hist:
            cursor.execute("ALTER TABLE historial_jornadas ADD COLUMN signo_doble TEXT DEFAULT ''")
    
    # 4. Tabla de usuarios (Plantilla oficial de los 28 peñistas)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS usuarios (
        id {tipo_id},
        nombre TEXT NOT NULL,
        aciertos INTEGER DEFAULT 0,
        errores INTEGER DEFAULT 0,
        partidos_asignados INTEGER DEFAULT 0
    )
    """)
    
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
    
    cursor.execute("SELECT COUNT(*) FROM partidos")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 16):
            if i == 15:
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronosticador_manual, pronostico, pleno_local, pleno_visitante, doble_por, signo_doble) 
                    VALUES (15, 'Equipo Local 15', 'Equipo Visitante 15', 'PLENO', '', '-', '-', '-', '', '')
                """)
            else:
                div_label = "Primera" if i <= 8 else "Segunda"
                cursor.execute("""
                    INSERT INTO partidos (num_partido, local, visitante, division, pronosticador_manual, pronostico, doble_por, signo_doble) 
                    VALUES (?, 'Equipo Local', 'Equipo Visitante', ?, '', '-', '', '')
                """, (i, div_label))
    
    conexion.commit()
    conexion.close()


verificar_y_actualizar_base_datos()


# ⚖️ FUNCIÓN DE REPARTO EQUITATIVO (14 titulares + 6 dobles + 1 Pleno = 21 convocados)
def obtener_reparto_equitativo(cursor):
    cursor.execute("SELECT nombre, partidos_asignados FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
    lista_ordenada = cursor.fetchall()
    
    titulares_14 = [u[0] for u in lista_ordenada[:14]]
    dobleros_auto_6 = [u[0] for u in lista_ordenada[14:20]]
    pleno_15_resp = lista_ordenada[20][0] if len(lista_ordenada) > 20 else lista_ordenada[0][0]
    
    dobleros_manuales = []
    for d in range(1, 7):
        cursor.execute("SELECT texto FROM configuracion WHERE clave = ?", (f"doblero_manual_{d}",))
        fila = cursor.fetchone()
        if fila and fila[0] and fila[0].strip() != "":
            dobleros_manuales.append(fila[0].strip())
            
    dobleros_6 = dobleros_manuales if len(dobleros_manuales) > 0 else dobleros_auto_6
    
    convocados_21 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[:21]]
    descansan_7 = [{"nombre": u[0], "partidos": u[1]} for u in lista_ordenada[21:]]
    
    return titulares_14, dobleros_6, pleno_15_resp, convocados_21, descansan_7


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
    
    cursor.execute("SELECT DISTINCT jornada FROM historial_jornadas ORDER BY jornada ASC")
    jornadas_hist = [fila[0] for fila in cursor.fetchall()]
    jornadas_disponibles = sorted(list(set(jornadas_hist + [jornada_activa])))
    
    titulares_14, dobleros_6, pleno_15_resp, convocados_21, descansan_7 = obtener_reparto_equitativo(cursor)
    
    partidos_limpios = []
    es_pasado = False
    titulares_reales_jornada = []
    
    if jornada_viendo != jornada_activa and jornada_viendo in jornadas_hist:
        es_pasado = True
        cursor.execute("""
            SELECT num_partido, local, visitante, division, pronosticador, doble_por, signo_doble, pronostico, 
                   resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
            FROM historial_jornadas WHERE jornada = ? ORDER BY num_partido ASC
        """, (jornada_viendo,))
        for p in cursor.fetchall():
            num_p = p[0]
            titular_p = p[4] or ""
            doblero_p = p[5] or ""
            sig_doble_p = (p[6] or "").strip().upper()
            pron_p = (p[7] or "-").strip().upper()
            real_p = (p[8] or "-").strip().upper()
            pleno_l_p, pleno_v_p = p[9], p[10]
            pleno_lr_p, pleno_vr_p = p[11], p[12]

            # Calculamos exactamente quién acertó el partido para mostrarlo en pequeño
            acertante_texto = ""
            if num_p <= 14 and real_p != "-" and real_p in pron_p:
                if doblero_p and sig_doble_p:
                    if real_p == sig_doble_p:
                        acertante_texto = f"Acertó: {doblero_p} (Doble)"
                    else:
                        acertante_texto = f"Acertó: {titular_p}"
                elif not doblero_p:
                    acertante_texto = f"Acertó: {titular_p}"
            elif num_p == 15 and pleno_lr_p != "-" and pleno_vr_p != "-":
                if pleno_l_p == pleno_lr_p and pleno_v_p == pleno_vr_p:
                    acertante_texto = f"Acertó: {titular_p}"

            lista_dobles = [doblero_p] if doblero_p != "" else []
            partidos_limpios.append({
                "num": num_p, "local": p[1], "visitante": p[2], "division": p[3],
                "pronosticador": titular_p, "doble_por": doblero_p, "dobles": lista_dobles,
                "pronostico": pron_p, "resultado_real": real_p,
                "pleno_local": pleno_l_p, "pleno_visitante": pleno_v_p,
                "pleno_local_real": pleno_lr_p, "pleno_visitante_real": pleno_vr_p,
                "acertante_texto": acertante_texto
            })
    else:
        cursor.execute("""
            SELECT num_partido, local, visitante, division, doble_por, pronostico, 
                   resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real, signo_doble, pronosticador_manual
            FROM partidos ORDER BY num_partido ASC
        """)
        for p in cursor.fetchall():
            num = p[0]
            manual = p[12] or ""
            responsable_auto = titulares_14[num - 1] if num <= 14 else pleno_15_resp
            responsable = manual if manual.strip() != "" else responsable_auto
            titulares_reales_jornada.append(responsable)
            
            lista_dobles_partido = [p[4]] if (p[4] and p[4] != "") else []
            partido = {
                "num": num, "local": p[1], "visitante": p[2], "division": p[3],
                "doble_por": p[4], "dobles": lista_dobles_partido, "pronosticador": responsable,
                "pronostico": p[5] if p[5] else "-", "resultado_real": p[6] if p[6] else "-",
                "pleno_local": p[7], "pleno_visitante": p[8],
                "pleno_local_real": p[9], "pleno_visitante_real": p[10],
                "signo_doble": p[11], "acertante_texto": ""
            }
            if p[5] and p[5].strip().upper() == "X":
                partido["pronostico"] = "X"
            partidos_limpios.append(partido)
            
        cursor.execute("SELECT nombre, partidos_asignados FROM usuarios ORDER BY partidos_asignados ASC, id ASC")
        todos_usuarios = cursor.fetchall()
        nombres_convocados = []
        for nom in titulares_reales_jornada + dobleros_6:
            if nom and nom not in nombres_convocados:
                nombres_convocados.append(nom)
        convocados_21 = [{"nombre": u[0], "partidos": u[1]} for u in todos_usuarios if u[0] in nombres_convocados]
        descansan_7 = [{"nombre": u[0], "partidos": u[1]} for u in todos_usuarios if u[0] not in nombres_convocados]
    
    # 📊 CÁLCULO DE CLASIFICACIÓN POR RATIO Y JORNADAS PARTICIPADAS
    cursor.execute("SELECT nombre, aciertos, errores, partidos_asignados FROM usuarios")
    usuarios_db = cursor.fetchall()
    
    peñistas_lista = []
    for u in usuarios_db:
        nombre = u[0]
        aciertos = u[1] or 0
        errores = u[2] or 0
        
        # Contamos en cuántas jornadas distintas del historial participó (como titular o como doble)
        cursor.execute("""
            SELECT COUNT(DISTINCT jornada) 
            FROM historial_jornadas 
            WHERE pronosticador = ? OR doble_por = ?
        """, (nombre, nombre))
        fila_jor = cursor.fetchone()
        jornadas_jugadas = fila_jor[0] if fila_jor else 0
        
        if errores > 0:
            ratio_valor = aciertos / errores
        else:
            ratio_valor = float(aciertos)
            
        peñistas_lista.append({
            "nombre": nombre,
            "aciertos": aciertos,
            "errores": errores,
            "jornadas": jornadas_jugadas,
            "ratio_num": ratio_valor,
            "ratio_texto": f"{ratio_valor:.3f}".replace(".", ",")
        })
        
    peñistas_lista.sort(key=lambda x: (x["ratio_num"], x["aciertos"], -x["errores"]), reverse=True)
    
    conexion.close()
    
    return render_template(
        "index.html", 
        partidos=partidos_limpios, 
        peñistas=peñistas_lista,          
        los_del_doble=dobleros_6,      
        conjunto_dobles=dobleros_6,  
        convocados=convocados_21,            
        descansan=descansan_7,              
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
        es_doble = request.form.get("es_doble") == "1"
        
        if not sig:
            cursor.execute("UPDATE partidos SET pronostico = '-', doble_por = '', signo_doble = '' WHERE num_partido = ?", (num_partido,))
        else:
            sig = sig.strip().upper()
            cursor.execute("SELECT pronostico, signo_doble FROM partidos WHERE num_partido = ?", (num_partido,))
            fila = cursor.fetchone()
            act = (fila[0] if fila and fila[0] else "-").strip().upper()
            sig_doble = (fila[1] if fila and fila[1] else "").strip().upper()
            
            if es_doble:
                if act == "-" or act == "":
                    nuevo = sig
                elif sig not in act:
                    nuevo = "".join(sorted(act + sig))
                else:
                    nuevo = act
            else:
                if act == sig or (sig == act.replace(sig_doble, "") and sig != ""):
                    nuevo = sig_doble if sig_doble else "-"
                else:
                    if sig_doble and sig_doble != sig:
                        nuevo = "".join(sorted(sig + sig_doble))
                    else:
                        nuevo = sig
                        
            cursor.execute("UPDATE partidos SET pronostico = ? WHERE num_partido = ?", (nuevo, num_partido))
            
    conexion.commit()
    conexion.close()
    return redirect(url_for("inicio"))


# 🔥 GUARDAR FIRMA Y SIGNO EXACTO DEL DOBLE DESDE LA PORTADA
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


# 🧹 QUITAR SOLO EL DOBLE DE UN PARTIDO ANTIGUO
@app.route("/quitar_doble", methods=["POST"])
def quitar_doble():
    partido = request.form.get("partido")
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT pronostico, signo_doble FROM partidos WHERE num_partido = ?", (partido,))
    fila = cursor.fetchone()
    
    pronostico_restante = "-"
    if fila:
        actual = (fila[0] or "-").strip().upper()
        sig_doble = (fila[1] or "").strip().upper()
        
        if sig_doble and sig_doble in actual:
            pronostico_restante = actual.replace(sig_doble, "")
            if pronostico_restante == "":
                pronostico_restante = "-"
        else:
            pronostico_restante = actual
            
    cursor.execute("""
        UPDATE partidos 
        SET pronostico = ?, doble_por = '', signo_doble = '' 
        WHERE num_partido = ?
    """, (pronostico_restante, partido))
    
    conexion.commit()
    conexion.close()
    return pronostico_restante, 200


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
        SELECT num_partido, local, visitante, division, resultado_real, pleno_local_real, pleno_visitante_real, pronosticador_manual, doble_por, signo_doble 
        FROM partidos ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    dobleros_seleccionados = []
    for d in range(1, 7):
        cursor.execute("SELECT texto FROM configuracion WHERE clave = ?", (f"doblero_manual_{d}",))
        fila = cursor.fetchone()
        dobleros_seleccionados.append(fila[0] if (fila and fila[0]) else "")
    
    cursor.execute("SELECT id, nombre, aciertos, errores FROM usuarios ORDER BY nombre ASC")
    usuarios = cursor.fetchall()

    # 🔍 CARGAMOS LAS JORNADAS ARCHIVADAS PARA EL REVISOR DE HISTORIAL (VAR)
    cursor.execute("SELECT DISTINCT jornada FROM historial_jornadas ORDER BY jornada DESC")
    jornadas_archivadas = [f[0] for f in cursor.fetchall()]
    
    jornada_revisar = request.args.get("jornada_revisar", type=int)
    if not jornada_revisar and jornadas_archivadas:
        jornada_revisar = jornadas_archivadas[0]
        
    partidos_historial = []
    if jornada_revisar:
        cursor.execute("""
            SELECT id, num_partido, local, visitante, pronosticador, doble_por, signo_doble, 
                   pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
            FROM historial_jornadas 
            WHERE jornada = ? 
            ORDER BY num_partido ASC
        """, (jornada_revisar,))
        partidos_historial = cursor.fetchall()
    
    conexion.close()
    return render_template(
        "admin.html", 
        partidos=partidos, 
        jornada=jornada, 
        temporada=temporada, 
        usuarios=usuarios, 
        dobleros_seleccionados=dobleros_seleccionados,
        jornadas_archivadas=jornadas_archivadas,
        jornada_revisar=jornada_revisar,
        partidos_historial=partidos_historial
    )


# 👤 GUARDAR ASIGNACIÓN MANUAL DE LOS 15 TITULARES Y SOLO LOS NOMBRES DE LOS 6 DOBLEROS
@app.route("/admin/asignar_pronosticadores", methods=["POST"])
def asignar_pronosticadores():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    for i in range(1, 16):
        peñista_elegido = request.form.get(f"pronosticador_{i}", "").strip()
        cursor.execute("""
            UPDATE partidos 
            SET pronosticador_manual = ? 
            WHERE num_partido = ?
        """, (peñista_elegido, i))
        
    for d in range(1, 7):
        peñista_doble = request.form.get(f"doble_penista_{d}", "").strip()
        cursor.execute("""
            UPDATE configuracion 
            SET texto = ? 
            WHERE clave = ?
        """, (peñista_doble, f"doblero_manual_{d}"))
        
    conexion.commit()
    conexion.close()
    return redirect("/admin")


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
                INSERT INTO partidos (num_partido, local, visitante, division, pronosticador_manual, pronostico, doble_por, signo_doble) 
                VALUES (?, ?, ?, ?, '', '-', '', '')
            """, (contador, local, visitante, div_label))
        elif contador == 15:
            cursor.execute("""
                INSERT INTO partidos (num_partido, local, visitante, division, pronosticador_manual, pronostico, pleno_local, pleno_visitante, doble_por, signo_doble) 
                VALUES (15, ?, ?, 'PLENO', '', '-', '-', '-', '', '')
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
    lineas = [l.strip() for l in texto_bruto.strip().split("\n") if l.strip()]
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    num_partido_actual = 1
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


# 📝 GUARDAR EDICIÓN MANUAL DE PARTIDOS Y Nº DE JORNADA
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
                SET local = ?, visitante = ?, pronosticador_manual = '', pronostico = '-', doble_por = '', signo_doble = '', resultado_real = '-', pleno_local = '-', pleno_visitante = '-', pleno_local_real = '-', pleno_visitante_real = '-'
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
    
    titulares_14, dobleros_6, pleno_15_resp, convocados_21, _ = obtener_reparto_equitativo(cursor)
    
    cursor.execute("""
        SELECT num_partido, local, visitante, division, pronostico, resultado_real, 
               doble_por, signo_doble, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real, pronosticador_manual
        FROM partidos 
        ORDER BY num_partido ASC
    """)
    partidos = cursor.fetchall()
    
    cursor.execute("DELETE FROM historial_jornadas WHERE jornada = ?", (jornada_actual,))
    
    participantes_reales_jornada = set()
    
    for p in partidos:
        num, local, visitante, division = p[0], p[1], p[2], p[3]
        pronostico_pena = p[4] or "-"
        resultado_tele = p[5] or "-"
        quien_doble = p[6] or ""
        signo_del_doble = p[7] or ""
        pleno_l, pleno_v, pleno_l_real, pleno_v_real = p[8], p[9], p[10], p[11]
        manual = p[12] or ""
        
        responsable_auto = titulares_14[num - 1] if num <= 14 else pleno_15_resp
        responsable = manual if manual.strip() != "" else responsable_auto
        
        participantes_reales_jornada.add(responsable)
        if quien_doble:
            participantes_reales_jornada.add(quien_doble)
        
        # 1. Guardamos la foto de este partido en el ÁLBUM HISTÓRICO PERMANENTE
        cursor.execute("""
            INSERT INTO historial_jornadas (
                jornada, num_partido, local, visitante, division, pronosticador, doble_por, signo_doble,
                pronostico, resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (jornada_actual, num, local, visitante, division, responsable, quien_doble, signo_del_doble,
              pronostico_pena, resultado_tele, pleno_l, pleno_v, pleno_l_real, pleno_v_real))
        
        # 2. Calculamos aciertos y errores (Partidos 1-14 = 1 punto; Pleno al 15 exacto = 2 puntos)
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
        elif num == 15 and pleno_l_real != "-" and pleno_v_real != "-":
            # Acertar el marcador exacto del Pleno al 15 suma +2 aciertos
            if pleno_l == pleno_l_real and pleno_v == pleno_v_real:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 2 WHERE nombre = ?", (responsable,))
            else:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (responsable,))
                
    # 3. Sumamos +1 partido asignado a quienes realmente participaron
    hay_manuales = any((p[12] or "").strip() != "" for p in partidos)
    if hay_manuales:
        for nombre_part in participantes_reales_jornada:
            cursor.execute("UPDATE usuarios SET partidos_asignados = partidos_asignados + 1 WHERE nombre = ?", (nombre_part,))
    else:
        for c in convocados_21:
            cursor.execute("UPDATE usuarios SET partidos_asignados = partidos_asignados + 1 WHERE nombre = ?", (c["nombre"],))

    # 4. Avanzamos a la siguiente jornada y limpiamos pronosticador_manual y dobleros manuales
    cursor.execute("UPDATE partidos SET pronosticador_manual = ''")
    for d in range(1, 7):
        cursor.execute("UPDATE configuracion SET texto = '' WHERE clave = ?", (f"doblero_manual_{d}",))
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'jornada'")

    conexion.commit()
    conexion.close()
    return redirect("/")


# 🔄 CORREGIR JORNADA ARCHIVADA Y RECALCULAR TODA LA CLASIFICACIÓN DESDE CERO
@app.route("/admin/corregir_jornada_archivada", methods=["POST"])
def corregir_jornada_archivada():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    jornada_editada = request.form.get("jornada_editada", type=int)
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Actualizamos los 15 partidos de esa jornada en historial_jornadas
    for i in range(1, 16):
        titular = request.form.get(f"hist_titular_{i}", "").strip()
        doblero = request.form.get(f"hist_doblero_{i}", "").strip()
        sig_doble = request.form.get(f"hist_sig_doble_{i}", "").strip().upper()
        
        if i <= 14:
            pron = request.form.get(f"hist_pron_{i}", "-").strip().upper() or "-"
            real = request.form.get(f"hist_real_{i}", "-").strip().upper() or "-"
            cursor.execute("""
                UPDATE historial_jornadas 
                SET pronosticador = ?, doble_por = ?, signo_doble = ?, pronostico = ?, resultado_real = ?
                WHERE jornada = ? AND num_partido = ?
            """, (titular, doblero, sig_doble, pron, real, jornada_editada, i))
        else:
            pleno_l = request.form.get("hist_pleno_l", "-").strip().upper() or "-"
            pleno_v = request.form.get("hist_pleno_v", "-").strip().upper() or "-"
            pleno_lr = request.form.get("hist_pleno_lr", "-").strip().upper() or "-"
            pleno_vr = request.form.get("hist_pleno_vr", "-").strip().upper() or "-"
            cursor.execute("""
                UPDATE historial_jornadas 
                SET pronosticador = ?, pleno_local = ?, pleno_visitante = ?, pleno_local_real = ?, pleno_visitante_real = ?
                WHERE jornada = ? AND num_partido = 15
            """, (titular, pleno_l, pleno_v, pleno_lr, pleno_vr, jornada_editada))
            
    # 2. Ponemos a 0 los marcadores de todos los usuarios y recalculamos TODAS las jornadas del historial
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    
    cursor.execute("""
        SELECT jornada, num_partido, pronosticador, doble_por, signo_doble, pronostico, 
               resultado_real, pleno_local, pleno_visitante, pleno_local_real, pleno_visitante_real
        FROM historial_jornadas 
        ORDER BY jornada ASC, num_partido ASC
    """)
    todos_hist = cursor.fetchall()
    
    participantes_por_jornada = {}
    
    for h in todos_hist:
        jor, num, resp, q_doble, s_doble, pron, real, pl, pv, plr, pvr = h
        pron = (pron or "-").strip().upper()
        real = (real or "-").strip().upper()
        q_doble = (q_doble or "").strip()
        s_doble = (s_doble or "").strip().upper()
        
        participantes_por_jornada.setdefault(jor, set())
        if resp:
            participantes_por_jornada[jor].add(resp)
        if q_doble:
            participantes_por_jornada[jor].add(q_doble)
            
        if num <= 14 and real != "-" and pron != "-":
            if q_doble and s_doble:
                sig_titular = pron.replace(s_doble, "")
                if real == sig_titular:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (resp,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (resp,))
                    
                if real == s_doble:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (q_doble,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (q_doble,))
            else:
                if real in pron:
                    cursor.execute("UPDATE usuarios SET aciertos = aciertos + 1 WHERE nombre = ?", (resp,))
                else:
                    cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (resp,))
        elif num == 15 and plr not in ["", "-"] and pvr not in ["", "-"] and pl not in ["", "-"] and pv not in ["", "-"]:
            if pl == plr and pv == pvr:
                cursor.execute("UPDATE usuarios SET aciertos = aciertos + 2 WHERE nombre = ?", (resp,))
            else:
                cursor.execute("UPDATE usuarios SET errores = errores + 1 WHERE nombre = ?", (resp,))
                
    for jor, lista_part in participantes_por_jornada.items():
        for nombre_p in lista_part:
            cursor.execute("UPDATE usuarios SET partidos_asignados = partidos_asignados + 1 WHERE nombre = ?", (nombre_p,))
            
    conexion.commit()
    conexion.close()
    return redirect(f"/admin?jornada_revisar={jornada_editada}")


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


# 🚨 REINICIO MAESTRO DE TEMPORADA (Protegido con palabra clave REINICIO)
@app.route("/admin/reiniciar_temporada", methods=["POST"])
def reiniciar_temporada():
    if not session.get("es_admin"):
        return redirect("/admin")
        
    # Verificamos en el servidor que se haya escrito exactamente REINICIO
    confirmacion = request.form.get("palabra_confirmacion", "").strip()
    if confirmacion != "REINICIO":
        return redirect("/admin")
        
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET aciertos = 0, errores = 0, partidos_asignados = 0")
    cursor.execute("DELETE FROM historial_jornadas")
    cursor.execute("UPDATE partidos SET pronosticador_manual = ''")
    for d in range(1, 7):
        cursor.execute("UPDATE configuracion SET texto = '' WHERE clave = ?", (f"doblero_manual_{d}",))
    cursor.execute("UPDATE configuracion SET valor = 1 WHERE clave = 'jornada'")
    conexion.commit()
    conexion.close()
    return redirect("/admin")


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print(f"🖥️ Motor de la Peña Busto encendido con éxito en el puerto {puerto}...")
    app.run(host="0.0.0.0", port=puerto, debug=False)