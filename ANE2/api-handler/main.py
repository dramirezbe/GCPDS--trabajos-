import socket
import time
import json
import os

SOCKET_PATH = "/tmp/test_socket"

# Borrar socket previo si existe
try:
    os.unlink(SOCKET_PATH)
except FileNotFoundError:
    pass

# Crear socket servidor
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCKET_PATH)
server.listen(1)

print("Servidor Python esperando conexión...")
conn, _ = server.accept()
print("Cliente C conectado.")

while True:
    # Crear un JSON simple
    payload = {"command": "get_status", "timestamp": time.time()}
    json_str = json.dumps(payload)

    # Enviar al cliente
    conn.sendall(json_str.encode() + b"\n")
    print(">> Enviado a C:", json_str)

    # Recibir respuesta del cliente
    data = conn.recv(1024).decode().strip()
    if not data:
        break

    try:
        response = json.loads(data)
        print("<< Respuesta de C:", response)
    except json.JSONDecodeError:
        print("Error: no es JSON válido:", data)

    time.sleep(10)

conn.close()
server.close()
