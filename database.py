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
    """Crea las tablas necesarias, ejecuta migraciones e inserta datos semilla."""
    conexion = obtener_conexion()
    if not conexion:
        return

    cursor = conexion.cursor()

    # 1. Tabla de Usuarios (Estructura base)
    tabla_usuarios = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        rol VARCHAR(20) DEFAULT 'Alumno',
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'Activo'
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
    
    # 4. El Plan General (Padre)
    tabla_planes = """
    CREATE TABLE IF NOT EXISTS planes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        descripcion TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 5. Las Semanas del Plan
    tabla_semanas = """
    CREATE TABLE IF NOT EXISTS plan_semanas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_plan INT NOT NULL,
        numero_semana INT NOT NULL,
        objetivo VARCHAR(255),
        FOREIGN KEY (id_plan) REFERENCES planes(id) ON DELETE CASCADE
    );
    """

    # 6. Los Días de la Semana
    tabla_dias = """
    CREATE TABLE IF NOT EXISTS plan_dias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_semana INT NOT NULL,
        numero_dia INT NOT NULL,
        nombre_dia VARCHAR(50), 
        FOREIGN KEY (id_semana) REFERENCES plan_semanas(id) ON DELETE CASCADE
    );
    """

    # 7. Los Bloques del Día
    tabla_bloques = """
    CREATE TABLE IF NOT EXISTS plan_bloques (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_dia INT NOT NULL,
        nombre_bloque VARCHAR(100) NOT NULL,
        orden INT DEFAULT 0,
        FOREIGN KEY (id_dia) REFERENCES plan_dias(id) ON DELETE CASCADE
    );
    """

    # 8. Los Ejercicios
    tabla_ejercicios = """
    CREATE TABLE IF NOT EXISTS plan_ejercicios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_bloque INT ,
        nombre_ejercicio VARCHAR(255) NOT NULL,
        series VARCHAR(100) DEFAULT '',
        reps VARCHAR(100) DEFAULT '',
        rpe VARCHAR(100) DEFAULT '',
        pausa VARCHAR(100) DEFAULT '',
        modalidad VARCHAR(100) DEFAULT 'Normal',
        link_yt VARCHAR(255) NULL,
        anotaciones TEXT NULL,
        orden INT DEFAULT 0,
        FOREIGN KEY (id_bloque) REFERENCES plan_bloques(id) ON DELETE CASCADE
    );
    """
    
    # 9. Recursos del Menú (Nuevo Requerimiento del Profe)
    tabla_recursos_menu = """
    CREATE TABLE IF NOT EXISTS recursos_menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        titulo VARCHAR(100) NOT NULL,
        url_destino VARCHAR(255) NOT NULL,
        icono_name VARCHAR(50) DEFAULT 'link',
        orden INT NOT NULL
    );
    """ # 💡 CORRECCIÓN 1: Comillas triples cerradas correctamente
    
    # 10. Catálogo Maestro de Ejercicios (Para autocompletado del Profe)
    tabla_catalogo = """
    CREATE TABLE IF NOT EXISTS catalogo_ejercicios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL UNIQUE,
        grupo_muscular VARCHAR(50),
        link_yt VARCHAR(255)
    );
    """

    # Usuario semilla base
    usuario_defecto = """
    INSERT IGNORE INTO usuarios (id, nombre, email, password, rol) 
    VALUES (1, 'Facu', 'facu@marte.com', '1234', 'Admin');
    """

    try:
        # Ejecutamos la creación de todas las tablas base
        cursor.execute(tabla_usuarios)
        cursor.execute(tabla_wods)
        cursor.execute(tabla_records)
        cursor.execute(tabla_planes)
        cursor.execute(tabla_semanas)
        cursor.execute(tabla_dias)
        cursor.execute(tabla_bloques)
        cursor.execute(tabla_ejercicios)
        cursor.execute(tabla_recursos_menu) # 💡 CORRECCIÓN 2: Agregamos la orden de ejecución para crear la tabla
        cursor.execute(tabla_catalogo) # 💡 CORRECCIÓN 3: Agregamos la orden de ejecución para crear la tabla
        cursor.execute(usuario_defecto)
        conexion.commit()
        
        # 🛠️ Inyectamos ejercicios base para el autocompletado
        ejercicios_base = [
            ("Sentadilla Tras Nuca", "Piernas", "https://youtube.com/shorts/sentadilla"),
            ("Sentadilla Frontal", "Piernas", "https://youtube.com/shorts/frontal"),
            ("Peso Muerto Convencional", "Espalda/Isquios", "https://youtube.com/shorts/pesomuerto"),
            ("Banco Plano con Barra", "Pecho", "https://youtube.com/shorts/bancoplano"),
            ("Dominadas Estrictas", "Espalda", "https://youtube.com/shorts/dominadas"),
            ("Press Militar con Mancuernas", "Hombros", "https://youtube.com/shorts/militar"),
            ("Burpees", "Cardio/Fullbody", "https://youtube.com/shorts/burpees")
        ]
        
        cursor.executemany("""
            INSERT IGNORE INTO catalogo_ejercicios (nombre, grupo_muscular, link_yt) 
            VALUES (%s, %s, %s)
        """, ejercicios_base)
        
        conexion.commit()

        # 🛠️ --- BLOQUE DE MIGRACIÓN DE ALUMNOS ---
        print("MIGRACIÓN: Verificando nuevas columnas de membresía en la tabla usuarios...")
        
        # 1. Intentamos agregar la fecha del último abono
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN fecha_pago DATE NULL;")
            conexion.commit()
            print("  ✅ Columna 'fecha_pago' añadida con éxito.")
        except Error:
            pass  # Si tira error es porque la columna ya existía, pasamos de largo.

        # 2. Intentamos agregar el ID del plan asignado
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN id_plan INT NULL;")
            cursor.execute("ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_planes FOREIGN KEY (id_plan) REFERENCES planes(id) ON DELETE SET NULL;")
            conexion.commit()
            print("  ✅ Columna 'id_plan' y su Clave Foránea añadidas con éxito.")
        except Error:
            pass
        
        # 3. Intentamos agregar la columna status (Activo/Inactivo)
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN status VARCHAR(20) DEFAULT 'Activo';")
            conexion.commit()
            print("  ✅ Columna 'status' añadida con éxito.")
        except Error:
            pass  # Si ya existe, pasa de largo sin chistar
        
        # 4. Intentamos agregar la categoría a los planes
        try:
            cursor.execute("ALTER TABLE planes ADD COLUMN categoria VARCHAR(50) DEFAULT 'Fuerza';")
            conexion.commit()
            print("  ✅ Columna 'categoria' en planes añadida con éxito.")
        except Error:
            pass  # Si ya existe, pasa de largo sin chistar
        
        # 5. Agregar campos de seguimiento al alumno
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN categoria VARCHAR(50) DEFAULT 'Fuerza';")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN semana_actual INT DEFAULT 1;")
            conexion.commit()
            print("  ✅ Columnas 'categoria' y 'semana_actual' añadidas.")
        except Error:
            pass  # Si ya existen, pasa de largo sin chistar
        
        # 6. Tabla de Historial de Ciclos Asignados
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_rutinas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_alumno INT,
                id_plan INT,
                nombre_ciclo VARCHAR(100),
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conexion.commit()
            print("  ✅ Tabla 'historial_rutinas' lista.")
        except Error as e:
            print(f"  ❌ Error en historial_rutinas: {e}")
        
        # Creamos un alumno de prueba (ID 2)
        alumno_prueba = """
        INSERT IGNORE INTO usuarios (id, nombre, email, password, rol, fecha_pago, id_plan) 
        VALUES (2, 'Juan Perez', 'juan@marte.com', '1234', 'Alumno', '2026-06-01', 1);
        """
        cursor.execute(alumno_prueba)
        conexion.commit()

        print("✅ Base de datos, tablas, migraciones y datos semilla verificados con éxito.")

    except Error as e:
        print(f"❌ Error al estructurar las tablas o migraciones: {e}")
    finally:
        cursor.close()
        conexion.close()