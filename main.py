from fastapi import FastAPI
from pydantic import BaseModel
import database

app = FastAPI(title="API de Marte Training")

@app.on_event("startup")
def startup_event():
    print("Iniciando servidor y verificando base de datos...")
    database.inicializar_base_de_datos()

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(request: LoginRequest):
    print(f"Intento de login recibido de: {request.email}")
    return {
        "success": True, 
        "mensaje": "Login exitoso", 
        "usuario": {
            "nombre": "Carla", 
            "rol": "Admin"
        }
    }
    
class RMRequest(BaseModel):
    usuario: str
    ejercicio: str
    peso: float

# RUTA DE GUARDADO REAL CONECTADA A MYSQL
@app.post("/guardar_rm")
def guardar_rm(request: RMRequest):
    print(f"💪 ¡Procesando récord de {request.usuario} en {request.ejercicio} ({request.peso}kg)!")
    
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión con la base de datos"}
            
        cursor = conexion.cursor()
        
        # Buscamos el ID del usuario por su nombre. Si no existe, usamos el 1 por defecto.
        cursor.execute("SELECT id FROM usuarios WHERE nombre = %s LIMIT 1", (request.usuario,))
        resultado_usuario = cursor.fetchone()
        id_usuario = resultado_usuario[0] if resultado_usuario else 1
        
        # Insertamos el registro en records_rm usando la fecha del servidor (CURDATE())
        sql = """
        INSERT INTO records_rm (id_usuario, ejercicio, peso_levantado, repeticiones, rm_calculado, fecha)
        VALUES (%s, %s, %s, %s, %s, CURDATE())
        """
        # Mapeamos provisionalmente el peso enviado como el RM calculado
        valores = (id_usuario, request.ejercicio, request.peso, 1, request.peso)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        cursor.close()
        conexion.close()
        
        return {
            "success": True, 
            "mensaje": f"¡Récord de {request.ejercicio} guardado con éxito en MySQL!"
        }
        
    except Exception as e:
        print(f"❌ Error al insertar en la base de datos: {e}")
        return {
            "success": False, 
            "mensaje": f"No se pudo guardar el récord en la base de datos: {e}"
        }
        
# RUTA PARA OBTENER EL HISTORIAL DE RÉCORDS
@app.get("/historial_rm")
def obtener_historial(usuario: str = "Carla"):
    print(f"🔍 Buscando el historial de RMs para: {usuario}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión con la base de datos"}
            
        cursor = conexion.cursor(dictionary=True)
        
        sql = """
        SELECT r.id, r.ejercicio, r.peso_levantado, r.repeticiones, r.rm_calculado, r.fecha
        FROM records_rm r
        JOIN usuarios u ON r.id_usuario = u.id
        WHERE u.nombre = %s
        ORDER BY r.fecha DESC, r.id DESC
        """
        
        cursor.execute(sql, (usuario,))
        historial = cursor.fetchall()
        
        cursor.close()
        conexion.close()
        
        return {
            "success": True, 
            "historial": historial
        }
        
    except Exception as e:
        print(f"❌ Error al consultar el historial: {e}")
        return {
            "success": False, 
            "mensaje": f"No se pudo obtener el historial: {e}"
        }
        
# --- NUEVO MODELO PARA RECIBIR LOS PESOS ---
class PesosSesionRequest(BaseModel):
    alumno_id: int
    nombre_ejercicio: str
    pesos: list[float]  # Recibe una lista de números, ej: [50.0, 55.0, 60.0]

# --- NUEVA RUTA PARA GUARDAR LOS PESOS DEL DÍA ---
@app.post("/guardar_pesos_sesion")
def guardar_pesos_sesion(request: PesosSesionRequest):
    print(f"🏋️ Guardando pesos de {request.nombre_ejercicio}: {request.pesos}")
    
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de base de datos"}
            
        cursor = conexion.cursor()
        
        # 1. Creamos una tabla rápida para el historial diario si no existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_diario (
            id INT AUTO_INCREMENT PRIMARY KEY,
            id_usuario INT NOT NULL,
            nombre_ejercicio VARCHAR(100) NOT NULL,
            pesos_levantados VARCHAR(255) NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 2. Convertimos la lista de Python [50, 55] a un texto "50.0, 55.0" para MySQL
        pesos_texto = ", ".join(map(str, request.pesos))
        
        # 3. Insertamos el registro
        sql = "INSERT INTO historial_diario (id_usuario, nombre_ejercicio, pesos_levantados) VALUES (%s, %s, %s)"
        cursor.execute(sql, (request.alumno_id, request.nombre_ejercicio, pesos_texto))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        return {"success": True, "mensaje": "¡Pesos guardados correctamente!"}
        
    except Exception as e:
        print(f"❌ Error al guardar pesos: {e}")
        return {"success": False, "mensaje": str(e)}

# --- NUEVA RUTA PARA LEER LOS PESOS DEL DÍA ---
@app.get("/obtener_pesos_sesion")
def obtener_pesos_sesion(alumno_id: int, nombre_ejercicio: str):
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "pesos": []}
            
        cursor = conexion.cursor(dictionary=True)
        
        # Buscamos el último registro de pesos para ese alumno y ese ejercicio
        sql = """
        SELECT pesos_levantados 
        FROM historial_diario 
        WHERE id_usuario = %s AND nombre_ejercicio = %s 
        ORDER BY fecha DESC LIMIT 1
        """
        cursor.execute(sql, (alumno_id, nombre_ejercicio))
        resultado = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        # Si encontró algo (ej: "50.0, 60.5"), lo separamos y lo mandamos como lista
        if resultado and resultado["pesos_levantados"]:
            lista_pesos = [p.strip() for p in resultado["pesos_levantados"].split(",")]
            return {"success": True, "pesos": lista_pesos}
            
        return {"success": True, "pesos": []}
        
    except Exception as e:
        print(f"❌ Error al obtener pesos: {e}")
        return {"success": False, "pesos": []}
    
# --- RUTA TEMPORAL PARA INYECTAR LOS DATOS DEL BOCETO ---
@app.get("/inyectar_datos_prueba")
def inyectar_datos():
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Sin conexión a BD"}
            
        cursor = conexion.cursor()

        # 1. Crear el Plan
        cursor.execute("INSERT INTO planes (nombre, descripcion) VALUES ('Fuerza y Acondicionamiento', 'Microciclo Base')")
        id_plan = cursor.lastrowid

        # 2. Crear la Semana (Conectada al Plan)
        cursor.execute("INSERT INTO plan_semanas (id_plan, numero_semana, objetivo) VALUES (%s, 1, 'Adaptación')", (id_plan,))
        id_semana = cursor.lastrowid

        # 3. Crear Día 1 y Día 2 (Conectados a la Semana)
        cursor.execute("INSERT INTO plan_dias (id_semana, numero_dia, nombre_dia) VALUES (%s, 1, 'Lunes')", (id_semana,))
        id_dia1 = cursor.lastrowid
        
        cursor.execute("INSERT INTO plan_dias (id_semana, numero_dia, nombre_dia) VALUES (%s, 2, 'Martes')", (id_semana,))
        id_dia2 = cursor.lastrowid

        # 4. Crear Bloques para el Día 1 (Conectados al Día 1)
        cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque, orden) VALUES (%s, 'BLOQUE A - SENTADILLA', 1)", (id_dia1,))
        id_bloque1_A = cursor.lastrowid

        cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque, orden) VALUES (%s, 'BLOQUE B - EMPUJE', 2)", (id_dia1,))
        id_bloque1_B = cursor.lastrowid

        # 5. Insertar Ejercicios Día 1 (Conectados a sus respectivos Bloques)
        cursor.execute("""
            INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, link_yt, anotaciones, orden) 
            VALUES (%s, 'Back Squat con pausa + Back Squat', '4', '2+2', '8', '2 MIN', 'Normal', 'https://youtube.com/...', 'Pausa de 2 seg en el fondo. Mantener el core firme.', 1)
        """, (id_bloque1_A,))

        cursor.execute("""
            INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, link_yt, anotaciones, orden) 
            VALUES (%s, 'Prensa', '3', '8', '8', '2 MIN', 'Normal', '', 'No bloquear las rodillas al extender.', 1)
        """, (id_bloque1_B,))

        # 6. Crear Bloque y Ejercicio para el Día 2
        cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque, orden) VALUES (%s, 'BLOQUE A - EMPUJE HORIZONTAL', 1)", (id_dia2,))
        id_bloque2_A = cursor.lastrowid

        cursor.execute("""
            INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, link_yt, anotaciones, orden) 
            VALUES (%s, 'Banco Plano con pausa', '4', '4', '8', '2 MIN', 'Normal', '', 'Pausa de 1 seg en el pecho.', 1)
        """, (id_bloque2_A,))

        conexion.commit()
        cursor.close()
        conexion.close()

        return {"success": True, "mensaje": "✅ ¡Datos del boceto inyectados a la perfección en MySQL!"}

    except Exception as e:
        return {"success": False, "mensaje": f"❌ Error: {e}"}

# --- RUTA REAL PARA OBTENER LA PLANIFICACIÓN DESDE MYSQL ---
@app.get("/rutina/{alumno_id}")
def obtener_rutina(alumno_id: int):
    print(f"📅 Buscando rutina real en MySQL para el alumno ID: {alumno_id}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"info_rutina": {}, "dias": []}
            
        cursor = conexion.cursor(dictionary=True)
        
        # Súper Consulta SQL: Unimos las 5 tablas respetando la jerarquía
        sql = """
        SELECT 
            p.nombre AS nombre_plan,
            ps.numero_semana,
            pd.numero_dia,
            pd.nombre_dia,
            pb.id AS bloque_id,
            pb.nombre_bloque,
            pe.id AS ejercicio_id,
            pe.nombre_ejercicio,
            pe.series,
            pe.reps,
            pe.rpe,
            pe.pausa,
            pe.modalidad,
            pe.link_yt,
            pe.anotaciones,
            pe.orden AS orden_ejercicio
        FROM planes p
        JOIN plan_semanas ps ON p.id = ps.id_plan
        JOIN plan_dias pd ON ps.id = pd.id_semana
        JOIN plan_bloques pb ON pd.id = pb.id_dia
        JOIN plan_ejercicios pe ON pb.id = pe.id_bloque
        ORDER BY pd.numero_dia, pb.orden, pe.orden
        """
        
        cursor.execute(sql)
        resultados = cursor.fetchall()
        
        cursor.close()
        conexion.close()

        # Si no hay datos, devolvemos la estructura vacía para que Flutter no falle
        if not resultados:
            return {"info_rutina": {}, "dias": []}

        # 1. Armamos la cabecera (Microciclo y Semana)
        info_rutina = {
            "microciclo": resultados[0]['nombre_plan'],
            "semanas_transcurridas": resultados[0]['numero_semana']
        }

        # 2. Agrupamos los datos usando diccionarios de Python
        dias_dict = {}
        for fila in resultados:
            dia_id = fila['numero_dia']
            
            # Creamos el Día si todavía no existe en nuestro diccionario
            if dia_id not in dias_dict:
                dias_dict[dia_id] = {
                    "numero_dia": dia_id,
                    "duracion_minutos": 60, 
                    "notas_atleta": "Calentamiento general: 10 min movilidad articular.", 
                    "bloques": {}
                }

            bloque_id = fila['bloque_id']
            
            # Creamos el Bloque dentro del Día si todavía no existe
            if bloque_id not in dias_dict[dia_id]['bloques']:
                dias_dict[dia_id]['bloques'][bloque_id] = {
                    "nombre_bloque": fila['nombre_bloque'],
                    "ejercicios": []
                }

            # Evaluamos si es un WOD/CrossFit según la modalidad
            es_wod = fila['modalidad'].upper() in ['AMRAP', 'EMOM', 'FOR TIME']

            # Empaquetamos el Ejercicio
            ejercicio = {
                "id_ejercicio": fila['ejercicio_id'],
                "nombre_ejercicio": fila['nombre_ejercicio'],
                "series": fila['series'],
                "reps": fila['reps'],
                "rpe_objetivo": str(fila['rpe']),
                "pausa": fila['pausa'],
                "modalidad": fila['modalidad'],
                "anotaciones": fila['anotaciones'],
                "link_yt": fila['link_yt'] if fila['link_yt'] else "",
                "es_wod": es_wod
            }
            
            # Lo metemos en su bloque correspondiente
            dias_dict[dia_id]['bloques'][bloque_id]['ejercicios'].append(ejercicio)

        # 3. Convertimos los diccionarios internos a listas para enviarlo como JSON limpio
        dias_list = []
        for d in dias_dict.values():
            d['bloques'] = list(d['bloques'].values())
            dias_list.append(d)

        return {
            "info_rutina": info_rutina,
            "dias": dias_list
        }

    except Exception as e:
        print(f"❌ Error al armar la rutina: {e}")
        return {"info_rutina": {}, "dias": []}