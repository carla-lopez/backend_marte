-- 1. Tabla de Usuarios (Alumnos y Profes)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(20) DEFAULT 'Alumno',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla del Pizarrón (Los WODs que carga el profe)
CREATE TABLE IF NOT EXISTS wods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    notas_profe VARCHAR(255)
);

-- 3. Tabla de Récords (La evolución del alumno)
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