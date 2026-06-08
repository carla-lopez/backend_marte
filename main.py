from fastapi import FastAPI
from pydantic import BaseModel
import database

# Inicializamos la app de FastAPI
app = FastAPI(title="API de Marte Training")

# Al arrancar, le decimos que verifique y cree las tablas en MySQL
@app.on_event("startup")
def startup_event():
    print("Iniciando servidor y verificando base de datos...")
    database.inicializar_base_de_datos()

# Modelo de datos que espera recibir desde Flutter para el Login
class LoginRequest(BaseModel):
    email: str
    password: str

# Ruta de prueba para el Login
@app.post("/login")
def login(request: LoginRequest):
    print(f"Intento de login recibido de: {request.email}")
    
    # Por ahora aceptamos cualquier cosa para que puedas probar la app
    # Más adelante acá conectaremos con la tabla de usuarios
    return {
        "success": True, 
        "mensaje": "Login exitoso", 
        "usuario": {
            "nombre": "Carla", 
            "rol": "Alumno"
        }
    }
    
# 1. El molde de los datos que esperamos recibir de Flutter
class RMRequest(BaseModel):
    usuario: str
    ejercicio: str
    peso: float

# 2. La nueva ruta para guardar el récord
@app.post("/guardar_rm")
def guardar_rm(request: RMRequest):
    print(f"💪 ¡Récord recibido en la nube! {request.usuario} levantó {request.peso}kg en {request.ejercicio}")
    
    # Por ahora le avisamos a la app que llegó bien. 
    # En el próximo paso acá metemos el código para guardarlo en la tabla de MySQL.
    return {
        "success": True, 
        "mensaje": "¡Récord guardado exitosamente en el servidor!"
    }