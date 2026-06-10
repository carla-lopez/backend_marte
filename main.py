from fastapi import FastAPI
from pydantic import BaseModel
import database
from datetime import date, timedelta

app = FastAPI(title="API de Marte Training")

@app.on_event("startup")
def startup_event():
    print("Iniciando servidor y verificando base de datos...")
    database.inicializar_base_de_datos()

class LoginRequest(BaseModel):
    email: str
    password: str

    
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

# --- RUTA DE RUTINA ACTUALIZADA CON CONTROL DE CANDADO ---
@app.get("/rutina/{alumno_id}")
def obtener_rutina(alumno_id: int):
    print(f"📅 Verificando acceso y rutina para el alumno ID: {alumno_id}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"membresia": {"status": "Error"}, "info_rutina": {}, "dias": []}
            
        cursor = conexion.cursor(dictionary=True)
        
        # 1. PASO CLAVE: Consultar la fecha de pago del alumno primero
        cursor.execute("SELECT fecha_pago FROM usuarios WHERE id = %s", (alumno_id,))
        usuario = cursor.fetchone()
        
        membresia = {"status": "Al Día", "dias_restantes": 30}
        if usuario and usuario['fecha_pago']:
            dias_pasados = (date.today() - usuario['fecha_pago']).days
            dias_restantes = 30 - dias_pasados
            
            if dias_restantes < 0:
                membresia = {"status": "Vencido", "dias_restantes": dias_restantes}
            elif dias_restantes <= 3:
                membresia = {"status": "Por Vencer", "dias_restantes": dias_restantes}
            else:
                membresia = {"status": "Al Día", "dias_restantes": dias_restantes}
        else:
            membresia = {"status": "Vencido", "dias_restantes": 0}

        # 2. Si está vencido, cortamos acá y no gastamos recursos en buscar la rutina
        if membresia["status"] == "Vencido":
            cursor.close()
            conexion.close()
            return {"membresia": membresia, "info_rutina": {}, "dias": []}

        # 3. Si tiene acceso, traemos la rutina relacional completa
        sql = """
        SELECT 
            p.nombre AS nombre_plan, ps.numero_semana, pd.numero_dia, pd.nombre_dia,
            pb.id AS bloque_id, pb.nombre_bloque, pe.id AS ejercicio_id, pe.nombre_ejercicio,
            pe.series, pe.reps, pe.rpe, pe.pausa, pe.modalidad, pe.link_yt, pe.anotaciones
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

        if not resultados:
            return {"membresia": membresia, "info_rutina": {}, "dias": []}

        info_rutina = {
            "microciclo": resultados[0]['nombre_plan'],
            "semanas_transcurridas": resultados[0]['numero_semana']
        }

        dias_dict = {}
        for fila in resultados:
            dia_id = fila['numero_dia']
            if dia_id not in dias_dict:
                dias_dict[dia_id] = {
                    "numero_dia": dia_id,
                    "duracion_minutos": 60, 
                    "notas_atleta": "Calentamiento general: 10 min movilidad articular.", 
                    "bloques": {}
                }

            bloque_id = fila['bloque_id']
            if bloque_id not in dias_dict[dia_id]['bloques']:
                dias_dict[dia_id]['bloques'][bloque_id] = {
                    "nombre_bloque": fila['nombre_bloque'],
                    "ejercicios": []
                }

            es_wod = fila['modalidad'].upper() in ['AMRAP', 'EMOM', 'FOR TIME']

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
            dias_dict[dia_id]['bloques'][bloque_id]['ejercicios'].append(ejercicio)

        dias_list = []
        for d in dias_dict.values():
            d['bloques'] = list(d['bloques'].values())
            dias_list.append(d)

        return {
            "membresia": membresia, # Le adjuntamos las llaves del candado
            "info_rutina": info_rutina,
            "dias": dias_list
        }

    except Exception as e:
        print(f"❌ Error al armar rutina: {e}")
        return {"membresia": {"status": "Error"}, "info_rutina": {}, "dias": []}
    
# --- NUEVA RUTA PARA EL PANEL DEL PROFESOR: LISTAR ALUMNOS ---
# --- NUEVA RUTA PARA EL PANEL DEL PROFESOR: LISTAR ALUMNOS ---
@app.get("/alumnos")
def obtener_alumnos():
    print("👥 Petición recibida: Listando todos los alumnos con su ficha deportiva...")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return [] # Devolvemos lista vacía en vez de dict para no romper Flutter
            
        cursor = conexion.cursor(dictionary=True)
        
        # 💡 MODIFICACIÓN 1: Agregamos 'categoria' y 'semana_actual' a la consulta SQL
        cursor.execute("SELECT id, nombre, email, fecha_pago, status, categoria, semana_actual FROM usuarios WHERE rol = 'Alumno'")
        lista_usuarios = cursor.fetchall()
        
        cursor.close()
        conexion.close()
        
        hoy = date.today()
        alumnos_procesados = []
        
        for u in lista_usuarios:
            fecha_pago = u["fecha_pago"]
            
            # Si nunca pagó o la fecha está vacía, evitamos que Python crashee
            if fecha_pago is None:
                estado = "Sin Registrar"
                dias_restantes = 0
            else:
                # Si la fecha es un string, la convertimos a objeto date
                if isinstance(fecha_pago, str):
                    from datetime import datetime
                    fecha_pago = datetime.strptime(fecha_pago, "%Y-%m-%d").date()
                
                # Calculamos el vencimiento (30 días después del pago)
                fecha_vencimiento = fecha_pago + timedelta(days=30)
                dias_restantes = (fecha_vencimiento - hoy).days
                
                # Determinamos el color del semáforo
                if dias_restantes <= 0:
                    estado = "Vencido"
                elif dias_restantes <= 5:
                    estado = "Por Vencer"
                else:
                    estado = "Al Día"
            
            # 💡 MODIFICACIÓN 2: Agregamos las nuevas propiedades al diccionario que se envía a Flutter
            alumnos_procesados.append({
                "id": u["id"],
                "nombre": u["nombre"],
                "email": u["email"],
                "estado": estado,
                "dias_restantes": max(0, dias_restantes),
                "status_usuario": u["status"],
                "categoria": u["categoria"] if u["categoria"] else "Fuerza",
                "semana_actual": u["semana_actual"] if u["semana_actual"] is not None else 1
            })
            
        # IMPORTANTE: Devolvemos una lista plana directamente
        return alumnos_procesados
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN /ALUMNOS: {e}")
        return []
    
# --- MODELO PARA RECIBIR EL ALTA DE ALUMNO ---
class AltaAlumnoRequest(BaseModel):
    nombre: str
    email: str
    fecha_pago: str  # Formato YYYY-MM-DD que manda el calendario de Flutter

@app.post("/profesor/crear_alumno")
def crear_alumno(request: AltaAlumnoRequest):
    print(f"👤 Registrando nuevo alumno: {request.nombre} ({request.email})")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión con la base de datos"}
            
        cursor = conexion.cursor()
        
        # Insertamos el usuario con rol 'Alumno' y contraseña inicial '1234' por defecto
        sql = """
        INSERT INTO usuarios (nombre, email, password, rol, fecha_pago, id_plan)
        VALUES (%s, %s, '1234', 'Alumno', %s, 1)
        """
        cursor.execute(sql, (request.nombre, request.email, request.fecha_pago))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "¡Alumno registrado con éxito!"}
        
    except Exception as e:
        print(f"❌ Error al crear alumno: {e}")
        return {"success": False, "mensaje": "El email ya está registrado o los datos son inválidos."}
    
# --- MODELO PARA AGREGAR UN EJERCICIO DESDE EL CELU ---
class AgregarEjercicioRequest(BaseModel):
    id_plan: int
    numero_semana: int
    numero_dia: int
    nombre_bloque: str  # Ej: "BLOQUE A - FUERZA"
    nombre_ejercicio: str
    series: str
    reps: str
    rpe: str
    pausa: str
    modalidad: str  # Normal, AMRAP, EMOM...
    anotaciones: str

@app.post("/profesor/agregar_ejercicio")
def agregar_ejercicio_plan(request: AgregarEjercicioRequest):
    print(f"🏋️ Profe agregando ejercicio a Plan {request.id_plan}, Día {request.numero_dia}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de base de datos"}
            
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Buscar o Crear la Semana
        cursor.execute("SELECT id FROM plan_semanas WHERE id_plan = %s AND numero_semana = %s", (request.id_plan, request.numero_semana))
        semana = cursor.fetchone()
        if semana:
            id_semana = semana['id']
        else:
            cursor.execute("INSERT INTO plan_semanas (id_plan, numero_semana, objetivo) VALUES (%s, %s, 'Planificación Express')", (request.id_plan, request.numero_semana))
            id_semana = cursor.lastrowid

        # 2. Buscar o Crear el Día
        cursor.execute("SELECT id FROM plan_dias WHERE id_semana = %s AND numero_dia = %s", (id_semana, request.numero_dia))
        dia = cursor.fetchone()
        if dia:
            id_dia = dia['id']
        else:
            cursor.execute("INSERT INTO plan_dias (id_semana, numero_dia, nombre_dia) VALUES (%s, %s, %s)", (id_semana, request.numero_dia, f"Día {request.numero_dia}"))
            id_dia = cursor.lastrowid

        # 3. Buscar o Crear el Bloque
        cursor.execute("SELECT id FROM plan_bloques WHERE id_dia = %s AND nombre_bloque = %s", (id_dia, request.nombre_bloque.upper()))
        bloque = cursor.fetchone()
        if bloque:
            id_bloque = bloque['id']
        else:
            cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque, orden) VALUES (%s, %s, 1)", (id_dia, request.nombre_bloque.upper()))
            id_bloque = cursor.lastrowid

        # 4. Insertar el Ejercicio Final
        sql_ejercicio = """
        INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, anotaciones, orden)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        valores = (
            id_bloque, request.nombre_ejercicio, request.series, request.reps,
            request.rpe, request.pausa, request.modalidad, request.anotaciones
        )
        cursor.execute(sql_ejercicio, valores)
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "¡Ejercicio acoplado al plan con éxito!"}
    
        
    except Exception as e:
        print(f"❌ Error al planificar: {e}")
        return {"success": False, "mensaje": str(e)}

# --- MODELO PARA RECIBIR LAS CREDENCIALES ---
# --- MODELO PARA RECIBIR LAS CREDENCIALES ---
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login_usuarios(request: LoginRequest):
    print(f"🔐 Intento de login REAL para: {request.email}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión con la base de datos"}
            
        cursor = conexion.cursor(dictionary=True)
        
        # 🕵️‍♂️ Acá está la magia: Buscamos coincidencia EXACTA de mail y contraseña
        sql = "SELECT id, nombre, email, rol FROM usuarios WHERE email = %s AND password = %s"
        cursor.execute(sql, (request.email.strip(), request.password.strip()))
        usuario = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if usuario:
            # Si encontró al usuario en MySQL, lo deja pasar y manda sus datos (INCLUYENDO EL ID)
            return {
                "success": True, 
                "mensaje": "Login exitoso", 
                "usuario": {
                    "id": usuario["id"],
                    "nombre": usuario["nombre"],
                    "rol": usuario["rol"]
                }
            }
        else:
            # Si no lo encontró, lo rebota sin piedad
            return {"success": False, "mensaje": "Correo o contraseña incorrectos."}
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return {"success": False, "mensaje": "Error interno del servidor."}
    
from datetime import date

# --- RUTA PARA RENOVAR EL ABONO DE UN ALUMNO ---
@app.put("/profesor/renovar_abono/{alumno_id}")
def renovar_abono(alumno_id: int):
    print(f"💰 Registrando nuevo pago para el alumno ID: {alumno_id}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de BD"}
            
        cursor = conexion.cursor()
        hoy = date.today()
        
        # Actualizamos la fecha de pago al día de hoy
        cursor.execute("UPDATE usuarios SET fecha_pago = %s WHERE id = %s", (hoy, alumno_id))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "¡Abono renovado exitosamente!"}
        
    except Exception as e:
        print(f"❌ Error al renovar abono: {e}")
        return {"success": False, "mensaje": "Error interno al renovar."}
    
# --- MODELO PARA EDITAR UN ALUMNO ---
class EditarAlumnoRequest(BaseModel):
    nombre: str
    email: str
    status: str
    categoria: str = "Fuerza"
    semana_actual: int = 1

@app.put("/profesor/editar_alumno/{alumno_id}")
def editar_alumno(alumno_id: int, request: EditarAlumnoRequest):
    print(f"💾 Actualizando ficha del alumno ID {alumno_id}...")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "No se pudo conectar a la base de datos"}
            
        cursor = conexion.cursor()
        
        # 💡 CORRECCIÓN: Cambiamos 'status_usuario = %s' por 'status = %s' 
        # para que coincida exactamente con tu columna de MySQL
        sql = """
        UPDATE usuarios 
        SET nombre = %s, email = %s, status = %s, categoria = %s, semana_actual = %s 
        WHERE id = %s
        """
        cursor.execute(sql, (
            request.nombre, 
            request.email, 
            request.status, 
            request.categoria, 
            request.semana_actual, 
            alumno_id
        ))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        print("✅ Ficha actualizada con éxito en la base de datos.")
        return {"success": True, "mensaje": "Ficha deportiva actualizada correctamente"}
        
    except Exception as e:
        print(f"❌ Error real en MySQL al editar alumno: {e}")
        return {"success": False, "mensaje": str(e)}
    
# --- RUTA PARA OBTENER EL CATÁLOGO DE EJERCICIOS (AUTOCOMPLETADO EN FLUTTER) ---
@app.get("/catalogo_ejercicios")
def obtener_catalogo():
    print("📚 Petición recibida: Enviando catálogo maestro para autocompletado...")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return []
            
        cursor = conexion.cursor(dictionary=True)
        
        # Seleccionamos los campos necesarios ordenados alfabéticamente
        cursor.execute("SELECT nombre, grupo_muscular, link_yt FROM catalogo_ejercicios ORDER BY nombre ASC")
        catalogo = cursor.fetchall()
        
        cursor.close()
        conexion.close()
        
        return catalogo  # Devolvemos la lista plana directamente, igual que hicimos con /alumnos
        
    except Exception as e:
        print(f"❌ Error al obtener el catálogo de ejercicios: {e}")
        return []

# --- RUTA PARA LISTAR LOS PLANES MAESTROS DE LA LIBRERÍA ---
@app.get("/profesor/planes")
def obtener_planes_maestros():
    print("📋 Petición recibida: Listando plantillas de planes maestros...")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return []
            
        cursor = conexion.cursor(dictionary=True)
        
        # Traemos las plantillas incluyendo su categoría
        cursor.execute("SELECT id, nombre, descripcion, categoria, fecha_creacion FROM planes ORDER BY id DESC")
        planes = cursor.fetchall()
        
        cursor.close()
        conexion.close()
        
        # Convertimos la fecha a texto para evitar problemas de serialización JSON
        for p in planes:
            if p["fecha_creacion"]:
                p["fecha_creacion"] = str(p["fecha_creacion"])
                
        return planes
        
    except Exception as e:
        print(f"❌ Error al obtener planes maestros: {e}")
        return []
    
# --- MODELO PARA CREAR UN PLAN NUEVO ---
class CrearPlanRequest(BaseModel):
    nombre: str
    descripcion: str
    categoria: str # 'Fuerza' o 'CrossFit'

@app.post("/profesor/crear_plan")
def crear_plan(request: CrearPlanRequest):
    print(f"📝 Creando nueva plantilla: {request.nombre} ({request.categoria})")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión"}
            
        cursor = conexion.cursor()
        
        sql = "INSERT INTO planes (nombre, descripcion, categoria) VALUES (%s, %s, %s)"
        cursor.execute(sql, (request.nombre, request.descripcion, request.categoria))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "¡Plan creado exitosamente!"}
        
    except Exception as e:
        print(f"❌ Error al crear plan: {e}")
        return {"success": False, "mensaje": str(e)}
    
# --- RUTA PARA VER LOS EJERCICIOS DE UN PLAN ESPECÍFICO ---
@app.get("/profesor/plan/{plan_id}/ejercicios")
def obtener_ejercicios_plan(plan_id: int):
    print(f"🔍 Buscando radiografía de ejercicios para el plan ID: {plan_id}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return []
            
        cursor = conexion.cursor(dictionary=True)
        
        # Unimos todas las tablas hijas para traer el mapa completo del plan
        sql = """
        SELECT 
            ps.numero_semana, pd.numero_dia,
            pb.nombre_bloque,
            pe.id, pe.nombre_ejercicio, pe.series, pe.reps, pe.modalidad
        FROM plan_semanas ps
        JOIN plan_dias pd ON ps.id = pd.id_semana
        JOIN plan_bloques pb ON pd.id = pb.id_dia
        JOIN plan_ejercicios pe ON pb.id = pe.id_bloque
        WHERE ps.id_plan = %s
        ORDER BY ps.numero_semana ASC, pd.numero_dia ASC, pb.id ASC, pe.id ASC
        """
        cursor.execute(sql, (plan_id,))
        ejercicios = cursor.fetchall()
        
        cursor.close()
        conexion.close()
        return ejercicios
        
    except Exception as e:
        print(f"❌ Error al cargar ejercicios del plan {plan_id}: {e}")
        return []
    
class AsignarPlanRequest(BaseModel):
    alumno_id: int
    plan_id: int  # ID de la Plantilla Maestra elegida
    categoria: str

@app.put("/profesor/asignar_plan")
def asignar_plantilla_clonada(request: AsignarPlanRequest):
    print(f"👥 Clonando plantilla ID {request.plan_id} para alumno ID {request.alumno_id}")
    try:
        conexion = database.obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Traer nombre del alumno y nombre de la plantilla
        cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (request.alumno_id,))
        alumno = cursor.fetchone()
        cursor.execute("SELECT nombre FROM planes WHERE id = %s", (request.plan_id,))
        plantilla = cursor.fetchone()
        
        if not alumno or not plantilla:
            return {"success": False, "mensaje": "Alumno o plantilla no encontrados"}
            
        # Generar sufijo de fecha (Ej: "Junio 2026")
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_actual = meses[datetime.now().month - 1]
        anio_actual = datetime.now().year
        nombre_clonado = f"Rutina: {plantilla['nombre']} - {alumno['nombre']} ({mes_actual} {anio_actual})"
        
        # 2. Crear el nuevo plan individual en la tabla 'planes'
        cursor.execute("INSERT INTO planes (nombre, categoria) VALUES (%s, %s)", (nombre_clonado, request.categoria))
        nuevo_plan_id = cursor.lastrowid
        
        # 3. Traer todos los ejercicios de la plantilla original
        sql_ejercicios_plantilla = """
        SELECT 
            ps.numero_semana, pd.numero_dia, pb.nombre_bloque,
            pe.nombre_ejercicio, pe.series, pe.reps, pe.rpe, pe.pausa, pe.modalidad, pe.anotaciones
        FROM plan_semanas ps
        JOIN plan_dias pd ON ps.id = pd.id_semana
        JOIN plan_bloques pb ON pd.id = pb.id_dia
        JOIN plan_ejercicios pe ON pb.id = pe.id_bloque
        WHERE ps.id_plan = %s
        """
        cursor.execute(sql_ejercicios_plantilla, (request.plan_id,))
        ejercicios_a_copiar = cursor.fetchall()
        
        # Iteramos y copiamos
        for ej in ejercicios_a_copiar:
            # --- SEMANAS ---
            cursor.execute("SELECT id FROM plan_semanas WHERE id_plan = %s AND numero_semana = %s", (nuevo_plan_id, ej['numero_semana']))
            semana_row = cursor.fetchone()
            
            if not semana_row:  # 💡 ACÁ ESTÁ CORREGIDO EL ERROR
                cursor.execute("INSERT INTO plan_semanas (id_plan, numero_semana) VALUES (%s, %s)", (nuevo_plan_id, ej['numero_semana']))
                id_semana_nueva = cursor.lastrowid
            else:
                id_semana_nueva = semana_row['id']
                
            # --- DÍAS ---
            cursor.execute("SELECT id FROM plan_dias WHERE id_semana = %s AND numero_dia = %s", (id_semana_nueva, ej['numero_dia']))
            dia_row = cursor.fetchone()
            
            if not dia_row:
                cursor.execute("INSERT INTO plan_dias (id_semana, numero_dia) VALUES (%s, %s)", (id_semana_nueva, ej['numero_dia']))
                id_dia_nuevo = cursor.lastrowid
            else:
                id_dia_nuevo = dia_row['id']
                
            # --- BLOQUES ---
            cursor.execute("SELECT id FROM plan_bloques WHERE id_dia = %s AND nombre_bloque = %s", (id_dia_nuevo, ej['nombre_bloque']))
            bloque_row = cursor.fetchone()
            
            if not bloque_row:
                cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque) VALUES (%s, %s)", (id_dia_nuevo, ej['nombre_bloque']))
                id_bloque_nuevo = cursor.lastrowid
            else:
                id_bloque_nuevo = bloque_row['id']
                
            # --- EJERCICIOS ---
            sql_ins_ej = """
            INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, anotaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_ins_ej, (id_bloque_nuevo, ej['nombre_ejercicio'], ej['series'], ej['reps'], ej['rpe'], ej['pausa'], ej['modalidad'], ej['anotaciones']))

        # 4. Enlazar el plan clonado al alumno y registrar en el historial
        cursor.execute("UPDATE usuarios SET id_plan = %s, categoria = %s, semana_actual = 1 WHERE id = %s", (nuevo_plan_id, request.categoria, request.alumno_id))
        cursor.execute("INSERT INTO historial_rutinas (id_alumno, id_plan, nombre_ciclo) VALUES (%s, %s, %s)", (request.alumno_id, nuevo_plan_id, nombre_clonado))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "Plantilla clonada con éxito para el ciclo actual del atleta"}
    except Exception as e:
        print(f"❌ Error en clonación: {e}")
        return {"success": False, "mensaje": str(e)}
    
class PlanPersonalizadoRequest(BaseModel):
    alumno_id: int
    categoria: str

@app.post("/profesor/crear_plan_personalizado")
def crear_plan_personalizado(request: PlanPersonalizadoRequest):
    print(f"🛠️ Creando rutina a mano para el alumno ID: {request.alumno_id} ({request.categoria})")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return {"success": False, "mensaje": "Error de conexión a la base de datos"}
            
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Buscamos el nombre del alumno para bautizar su plan personalizado
        cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (request.alumno_id,))
        alumno = cursor.fetchone()
        if not alumno:
            return {"success": False, "mensaje": "Alumno no encontrado"}
            
        nombre_plan_personalizado = f"Rutina - {alumno['nombre']}"
        
        # 2. Insertamos el nuevo esqueleto de plan en la tabla 'planes'
        sql_plan = "INSERT INTO planes (nombre, categoria) VALUES (%s, %s)"
        cursor.execute(sql_plan, (nombre_plan_personalizado, request.categoria))
        nuevo_plan_id = cursor.lastrowid
        
        # 3. Se lo enlazamos al alumno inmediatamente y reseteamos su ciclo a Semana 1
        sql_usuario = """
        UPDATE usuarios 
        SET id_plan = %s, categoria = %s, semana_actual = 1 
        WHERE id = %s
        """
        cursor.execute(sql_usuario, (nuevo_plan_id, request.categoria, request.alumno_id))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        # Devolvemos los datos clave para que Flutter pueda abrir la pantalla del editor
        return {
            "success": True,
            "plan_id": nuevo_plan_id,
            "plan_nombre": nombre_plan_personalizado,
            "mensaje": "Esqueleto personalizado creado con éxito"
        }
        
    except Exception as e:
        print(f"❌ Error al crear plan personalizado: {e}")
        return {"success": False, "mensaje": str(e)}
    
@app.delete("/profesor/eliminar_ejercicio/{ejercicio_id}")
def eliminar_ejercicio(ejercicio_id: int):
    print(f"🗑️ Eliminando ejercicio ID: {ejercicio_id}")
    try:
        conexion = database.obtener_conexion()
        cursor = conexion.cursor()
        
        # Eliminamos el ejercicio directamente de la tabla plan_ejercicios
        cursor.execute("DELETE FROM plan_ejercicios WHERE id = %s", (ejercicio_id,))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "Ejercicio removido con éxito"}
    except Exception as e:
        print(f"❌ Error al eliminar ejercicio: {e}")
        return {"success": False, "mensaje": str(e)}
    
@app.get("/profesor/historial_alumno/{alumno_id}")
def obtener_historial_alumno(alumno_id: int):
    print(f"📋 Consultando historial de planificaciones para el atleta ID: {alumno_id}")
    try:
        conexion = database.obtener_conexion()
        if not conexion:
            return []
            
        cursor = conexion.cursor(dictionary=True)
        
        # Cruzamos la tabla de historial con la de planes para saber la categoría (Fuerza/CrossFit)
        sql = """
        SELECT h.id AS historial_id, h.id_plan, h.nombre_ciclo, h.fecha_asignacion, p.categoria
        FROM historial_rutinas h
        JOIN planes p ON h.id_plan = p.id
        WHERE h.id_alumno = %s
        ORDER BY h.fecha_asignacion DESC
        """
        cursor.execute(sql, (alumno_id,))
        historial = cursor.fetchall()
        
        # Formateamos la fecha para mostrarla prolija en la app (Día/Mes/Año)
        for h in historial:
            if h['fecha_asignacion']:
                h['fecha_asignacion'] = h['fecha_asignacion'].strftime("%d/%m/%Y")
                
        cursor.close()
        conexion.close()
        return historial
    except Exception as e:
        print(f"❌ Error al recuperar historial en MySQL: {e}")
        return []

@app.delete("/profesor/eliminar_rutina_historial/{id_plan}")
def eliminar_rutina_historial(id_plan: int):
    print(f"🗑️ Solicitud de purga total para la rutina histórica ID: {id_plan}")
    try:
        conexion = database.obtener_conexion()
        cursor = conexion.cursor()
        
        # 1. Borramos la entrada del registro de historial
        cursor.execute("DELETE FROM historial_rutinas WHERE id_plan = %s", (id_plan,))
        
        # 2. Borramos los ejercicios de forma limpia para no dejar registros huérfanos
        cursor.execute("""
            DELETE pe FROM plan_ejercicios pe
            JOIN plan_bloques pb ON pe.id_bloque = pb.id
            JOIN plan_dias pd ON pb.id_dia = pd.id
            JOIN plan_semanas ps ON pd.id_semana = ps.id
            WHERE ps.id_plan = %s
        """, (id_plan,))
        
        # 3. Finalmente, borramos el contenedor del plan
        cursor.execute("DELETE FROM planes WHERE id = %s", (id_plan,))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "Planificación eliminada del historial con éxito"}
    except Exception as e:
        print(f"❌ Error al purgar rutina del historial: {e}")
        return {"success": False, "mensaje": str(e)}


@app.put("/profesor/finalizar_plan/{plan_id}")
def finalizar_plan(plan_id: int):
    print(f"💾 Guardando y renombrando planificación ID: {plan_id}...")
    try:
        from datetime import datetime
        
        conexion = database.obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Buscamos el alumno asignado a este plan para extraer su ID y su Nombre
        cursor.execute("SELECT id, nombre FROM usuarios WHERE id_plan = %s", (plan_id,))
        usuario = cursor.fetchone()
        
        if usuario:
            nombre_atleta = usuario['nombre']
            alumno_id = usuario['id']
        else:
            # Salvaguarda: si no está asignado de forma activa, usamos el nombre base del plan
            cursor.execute("SELECT nombre FROM planes WHERE id = %s", (plan_id,))
            plan_row = cursor.fetchone()
            nombre_atleta = plan_row['nombre'] if plan_row else "Atleta"
            alumno_id = None
            
        # Limpiamos prefijos redundantes
        nombre_atleta = nombre_atleta.replace("Rutina - ", "").replace("Rutina: ", "")
        
        # 2. Calcular los meses dinámicamente (Ej: JUN-JUL 2026)
        hoy = datetime.now()
        meses_abrev = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        
        idx_mes_actual = hoy.month - 1
        idx_mes_siguiente = hoy.month if hoy.month < 12 else 0
        
        abrev_actual = meses_abrev[idx_mes_actual]
        abrev_siguiente = meses_abrev[idx_mes_siguiente]
        anio = hoy.year
        
        nuevo_titulo = f"Rutina {nombre_atleta} {abrev_actual}-{abrev_siguiente} {anio}"
        
        # 3. Actualizar el nombre definitivo en la tabla general de planes
        cursor.execute("UPDATE planes SET nombre = %s WHERE id = %s", (nuevo_titulo, plan_id))
        
        # 4. 💡 LA SOLUCIÓN: Verificar si ya tiene una entrada en el historial
        if alumno_id:
            cursor.execute("SELECT id FROM historial_rutinas WHERE id_plan = %s", (plan_id,))
            historial_row = cursor.fetchone()
            
            if not historial_row:
                # Si fue armada a mano, no existía en el historial. ¡La creamos ahora mismo!
                cursor.execute(
                    "INSERT INTO historial_rutinas (id_alumno, id_plan, nombre_ciclo) VALUES (%s, %s, %s)",
                    (alumno_id, plan_id, nuevo_titulo)
                )
                print(f"✨ Fila inexistente detectada: Indexada rutina a mano en el historial del alumno {alumno_id}")
            else:
                # Si vino de una plantilla clonada, ya existía, así que solo actualizamos el nombre bimensual
                cursor.execute("UPDATE historial_rutinas SET nombre_ciclo = %s WHERE id_plan = %s", (nuevo_titulo, plan_id))
                print("📝 Registro existente actualizado con el formato de fecha bimensual")
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        print(f"✅ Planificación indexada y sellada con éxito: {nuevo_titulo}")
        return {"success": True, "nuevo_titulo": nuevo_titulo}
        
    except Exception as e:
        print(f"❌ Error al finalizar plan: {e}")
        return {"success": False, "mensaje": str(e)}
    
class ClonarSemanaRequest(BaseModel):
    plan_id: int
    semana_origen: int
    semana_destino: int

@app.post("/profesor/clonar_semana")
def clonar_semana(request: ClonarSemanaRequest):
    print(f"🔄 Clonando Semana {request.semana_origen} hacia Semana {request.semana_destino} (Plan ID: {request.plan_id})")
    try:
        conexion = database.obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        # 1. Traer todos los ejercicios exactos de la semana origen
        sql_origen = """
        SELECT 
            pd.numero_dia, pb.nombre_bloque,
            pe.nombre_ejercicio, pe.series, pe.reps, pe.rpe, pe.pausa, pe.modalidad, pe.anotaciones
        FROM plan_semanas ps
        JOIN plan_dias pd ON ps.id = pd.id_semana
        JOIN plan_bloques pb ON pd.id = pb.id_dia
        JOIN plan_ejercicios pe ON pb.id = pe.id_bloque
        WHERE ps.id_plan = %s AND ps.numero_semana = %s
        """
        cursor.execute(sql_origen, (request.plan_id, request.semana_origen))
        ejercicios_a_copiar = cursor.fetchall()

        if not ejercicios_a_copiar:
            return {"success": False, "mensaje": "La semana anterior está vacía."}

        # 2. Replicar la estructura (Semanas > Días > Bloques > Ejercicios) en el destino
        for ej in ejercicios_a_copiar:
            # Semana
            cursor.execute("SELECT id FROM plan_semanas WHERE id_plan = %s AND numero_semana = %s", (request.plan_id, request.semana_destino))
            semana_row = cursor.fetchone()
            if not semana_row:
                cursor.execute("INSERT INTO plan_semanas (id_plan, numero_semana) VALUES (%s, %s)", (request.plan_id, request.semana_destino))
                id_semana_nueva = cursor.lastrowid
            else:
                id_semana_nueva = semana_row['id']
                
            # Día
            cursor.execute("SELECT id FROM plan_dias WHERE id_semana = %s AND numero_dia = %s", (id_semana_nueva, ej['numero_dia']))
            dia_row = cursor.fetchone()
            if not dia_row:
                cursor.execute("INSERT INTO plan_dias (id_semana, numero_dia) VALUES (%s, %s)", (id_semana_nueva, ej['numero_dia']))
                id_dia_nuevo = cursor.lastrowid
            else:
                id_dia_nuevo = dia_row['id']
                
            # Bloque
            cursor.execute("SELECT id FROM plan_bloques WHERE id_dia = %s AND nombre_bloque = %s", (id_dia_nuevo, ej['nombre_bloque']))
            bloque_row = cursor.fetchone()
            if not bloque_row:
                cursor.execute("INSERT INTO plan_bloques (id_dia, nombre_bloque) VALUES (%s, %s)", (id_dia_nuevo, ej['nombre_bloque']))
                id_bloque_nuevo = cursor.lastrowid
            else:
                id_bloque_nuevo = bloque_row['id']
                
            # Ejercicio
            sql_ins_ej = """
            INSERT INTO plan_ejercicios (id_bloque, nombre_ejercicio, series, reps, rpe, pausa, modalidad, anotaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_ins_ej, (id_bloque_nuevo, ej['nombre_ejercicio'], ej['series'], ej['reps'], ej['rpe'], ej['pausa'], ej['modalidad'], ej['anotaciones']))

        conexion.commit()
        cursor.close()
        conexion.close()
        return {"success": True, "mensaje": "Estructura replicada con éxito"}
    except Exception as e:
        print(f"❌ Error al clonar semana: {e}")
        return {"success": False, "mensaje": str(e)}