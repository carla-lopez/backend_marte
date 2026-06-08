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
    """Crea las tablas necesarias e inserta datos iniciales de prueba en el orden correcto."""
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

    # 3. Tabla de Historial de RMs (Depende de usuarios)
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
    
    # --- TABLAS DE LA PLANIFICACIÓN (Basadas en el boceto del profesor) ---

    # 4. El Plan General (Padre)
    tabla_planes = """
    CREATE TABLE IF NOT EXISTS planes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        descripcion TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 5. Las Semanas del Plan (Hijo - Depende de planes)
    tabla_semanas = """
    CREATE TABLE IF NOT EXISTS plan_semanas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_plan INT NOT NULL,
        numero_semana INT NOT NULL,
        objetivo VARCHAR(255),
        FOREIGN KEY (id_plan) REFERENCES planes(id) ON DELETE CASCADE
    );
    """

    # 6. Los Días de la Semana (Nieto - Depende de plan_semanas) -> Pestañas Día 1, Día 2...
    tabla_dias = """
    CREATE TABLE IF NOT EXISTS plan_dias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_semana INT NOT NULL,
        numero_dia INT NOT NULL,
        nombre_dia VARCHAR(50), 
        FOREIGN KEY (id_semana) REFERENCES plan_semanas(id) ON DELETE CASCADE
    );
    """

    # 7. Los Bloques del Día (Bisnieto - Depende de plan_dias) -> Bloque 1, Bloque 2...
    tabla_bloques = """
    CREATE TABLE IF NOT EXISTS plan_bloques (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_dia INT NOT NULL,
        nombre_bloque VARCHAR(100) NOT NULL,
        orden INT NOT NULL,
        FOREIGN KEY (id_dia) REFERENCES plan_dias(id) ON DELETE CASCADE
    );
    """

    # 8. Los Ejercicios (Tataranieto - Depende de plan_bloques) -> Detalle final con series, reps, etc.
    tabla_ejercicios = """
    CREATE TABLE IF NOT EXISTS plan_ejercicios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_bloque INT NOT NULL,
        nombre_ejercicio VARCHAR(100) NOT NULL,
        series VARCHAR(20),
        reps VARCHAR(20),
        rpe VARCHAR(20),
        pausa VARCHAR(50),
        modalidad VARCHAR(50),
        link_yt VARCHAR(255),
        anotaciones TEXT,
        orden INT NOT NULL,
        FOREIGN KEY (id_bloque) REFERENCES plan_bloques(id) ON DELETE CASCADE
    );
    """

    # Usuario semilla para evitar fallos de clave foránea en pruebas locales/remotas
    usuario_defecto = """
    INSERT IGNORE INTO usuarios (id, nombre, email, password, rol) 
    VALUES (1, 'Carla', 'carla@marte.com', '1234', 'Admin');
    """

    try:
        # Ejecución secuencial estricta para respetar integridad referencial
        cursor.execute(tabla_usuarios)
        cursor.execute(tabla_wods)
        cursor.execute(tabla_records)
        
        cursor.execute(tabla_planes)
        cursor.execute(tabla_semanas)
        cursor.execute(tabla_dias)
        cursor.execute(tabla_bloques)
        cursor.execute(tabla_ejercicios)
        
        cursor.execute(usuario_defecto)
        
        conexion.commit()
        print("✅ Base de datos, tablas y datos iniciales verificados con éxito.")
    except Error as e:
        print(f"❌ Error al estructurar las tablas: {e}")
    finally:
        cursor.close()
        conexion.close()