import mysql.connector
from mysql.connector import Error

def obtener_conexion():
    """Establece y devuelve la conexión con la base de datos MySQL."""
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',        # Ajustalo con tu usuario de MySQL (por defecto 'root')
            password='1234',        # Ajustalo con tu contraseña de MySQL
            database='marte_training'
        )
        return conexion
    except Error as e:
        print(f"❌ Error al conectar a MySQL: {e}")
        return None

def inicializar_base_de_datos():
    """Crea las tablas necesarias si no existen en el sistema."""
    # Primero nos conectamos sin especificar la BD para asegurarnos de que exista
    try:
        conexion_inicial = mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234'
        )
        cursor = conexion_inicial.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS marte_training")
        cursor.close()
        conexion_inicial.close()
    except Error as e:
        print(f"❌ Error al verificar/crear la base de datos: {e}")
        return

    # Ahora sí nos conectamos a nuestra base de datos para armar las tablas
    conexion = obtener_conexion()
    if not conexion:
        return

    cursor = conexion.cursor()

    # 1. Tabla de Usuarios
    tabla_usuarios = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        rol VARCHAR(20) DEFAULT 'Alumno',
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 2. Tabla del Pizarrón (WODs)
    tabla_wods = """
    CREATE TABLE IF NOT EXISTS wods (
        id INT AUTO_INCREMENT PRIMARY KEY,
        fecha DATE NOT NULL UNIQUE,
        titulo VARCHAR(100) NOT NULL,
        descripcion TEXT NOT NULL,
        notas_profe VARCHAR(255)
    );
    """

    # 3. Tabla de Historial de RMs
    tabla_records = """
    CREATE TABLE IF NOT EXISTS records_rm (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NOT NULL,
        ejercicio VARCHAR(100) NOT NULL,
        peso_levantado DECIMAL(5,2) NOT NULL,
        repeticiones INT NOT NULL,
        rm_calculado DECIMAL(5,2) NOT NULL,
        fecha DATE NOT NULL,
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
    );
    """

    try:
        cursor.execute(tabla_usuarios)
        cursor.execute(tabla_wods)
        cursor.execute(tabla_records)
        conexion.commit()
        print("✅ Base de datos y tablas verificadas/creadas con éxito.")
    except Error as e:
        print(f"❌ Error al estructurar las tablas: {e}")
    finally:
        cursor.close()
        conexion.close()