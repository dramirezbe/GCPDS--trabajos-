import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv, find_dotenv

# 1. Encontrar y cargar el .env más cercano (prioriza la carpeta actual)
ruta_env = find_dotenv()
load_dotenv(ruta_env)

print(f"Cargando configuración desde: {ruta_env or 'No se encontró archivo .env'}")

# 2. Leer las variables de entorno
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 

def consultar_base_datos():
    # Validación rápida para asegurar que sí leyó el archivo correcto
    if not DB_PASSWORD:
        print("❌ Error: No se encontraron las credenciales en el archivo .env")
        return

    conexion = None
    try:
        print(f"Intentando conectar a la base de datos '{DB_NAME}' en {DB_HOST}...")
        
        # Conexión usando las variables del .env
        conexion = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✅ ¡Conexión exitosa!\n")

        cursor = conexion.cursor()

        # Consulta de prueba
        cursor.execute("SELECT version();")
        resultado = cursor.fetchone()
        
        print("=== Respuesta del Servidor ===")
        print(resultado[0])
        print("==============================\n")

        cursor.close()

    except OperationalError as error:
        print(f"❌ Error al conectar a la base de datos:\n{error}")
        
    finally:
        if conexion is not None:
            conexion.close()
            print("Conexión cerrada correctamente.")

if __name__ == "__main__":
    consultar_base_datos()