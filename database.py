import mysql.connector
from mysql.connector import Error

def obtener_conexion():
    """Establece y devuelve la conexión con la base de datos MySQL en Railway."""
    try:
        conexion = mysql.connector.connect(
            host='acela.proxy.rlwy.net',  
            port='42641',  
            user='root',        
            password='AAbZPSnDcdNeJTOdJRdGAbvpGccsIpEh',        
            database='railway'     
        )
        return conexion
    except Error as e:
        print(f"❌ Error al conectar a MySQL: {e}")
        return None

def inicializar_base_de_datos():
    """Crea las tablas necesarias e inserta datos iniciales de prueba."""
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

    # 4. Usuario semilla para evitar fallos de clave foránea
    usuario_defecto = """
    INSERT IGNORE INTO usuarios (id, nombre, email, password, rol) 
    VALUES (1, 'Carla', 'carla@marte.com', '1234', 'Admin');
    """

    try:
        cursor.execute(tabla_usuarios)
        cursor.execute(tabla_wods)
        cursor.execute(tabla_records)
        cursor.execute(usuario_defecto) # Creamos el usuario base si no existe
        conexion.commit()
        print("✅ Base de datos, tablas y datos iniciales verificados con éxito.")
    except Error as e:
        print(f"❌ Error al estructurar las tablas: {e}")
    finally:
        cursor.close()
        conexion.close()