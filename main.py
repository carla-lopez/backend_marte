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