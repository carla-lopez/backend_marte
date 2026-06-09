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

# RUTA PARA OBTENER LA PLANIFICACIÓN (DATOS SIMULADOS ESTILO EXCEL)
@app.get("/rutina/{alumno_id}")
def obtener_rutina(alumno_id: int):
    return {
        "info_rutina": {
            "microciclo": "Fuerza y Acondicionamiento",
            "semanas_transcurridas": 1
        },
        "dias": [
            {
                "numero_dia": 1,
                "duracion_minutos": 60,
                "notas_atleta": "3 rondas: 5+5 rotaciones, 6 curl squat...",
                "bloques": [
                    {
                        "nombre_bloque": "BLOQUE A - SENTADILLA",
                        "ejercicios": [
                            {
                                "id_ejercicio": 101,
                                "nombre_ejercicio": "Back Squat con pausa + Back Squat",
                                "series": 4, 
                                "reps": "2+2",
                                "rpe_objetivo": "8",
                                "pausa": "2 MIN",
                                "modalidad": "Normal",
                                "anotaciones": "Pausa de 2 seg en el fondo. Mantener el core firme.",
                                "link_yt": "https://youtube.com/watch?v=12345",
                                "es_wod": False
                            }
                        ]
                    },
                    {
                        "nombre_bloque": "BLOQUE B - EMPUJE",
                        "ejercicios": [
                            {
                                "id_ejercicio": 102,
                                "nombre_ejercicio": "Prensa",
                                "series": 3,
                                "reps": "8",
                                "rpe_objetivo": "8",
                                "pausa": "2 MIN",
                                "modalidad": "Normal",
                                "anotaciones": "No bloquear las rodillas al extender.",
                                "link_yt": "",
                                "es_wod": False
                            }
                        ]
                    }
                ]
            },
            {
                "numero_dia": 2,
                "duracion_minutos": 45,
                "notas_atleta": "Día enfocado en tren superior.",
                "bloques": [
                    {
                        "nombre_bloque": "BLOQUE A - EMPUJE HORIZONTAL",
                        "ejercicios": [
                            {
                                "id_ejercicio": 103,
                                "nombre_ejercicio": "Banco Plano con pausa",
                                "series": 4,
                                "reps": "4",
                                "rpe_objetivo": "8",
                                "pausa": "2 MIN",
                                "modalidad": "Normal",
                                "anotaciones": "Pausa de 1 seg en el pecho.",
                                "link_yt": "",
                                "es_wod": False
                            }
                        ]
                    }
                ]
            }
        ]
    }