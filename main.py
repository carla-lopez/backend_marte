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