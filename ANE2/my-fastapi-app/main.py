# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime

app = FastAPI(title="API REST de prueba (FastAPI)")

class CommandRequest(BaseModel):
    command: str
    data: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    print("[SERVER] GET / -> health check")
    return {"status": "ok", "server_time": datetime.utcnow().isoformat()}

@app.get("/init")
async def get_init():
    print("[SERVER] GET /init -> init requested")
    # Respuesta dummy (simula initResponse)
    resp = {
        "device": "internal-sim",
        "version": "1.0",
        "features": ["streaming", "rec"],
        "timestamp": datetime.utcnow().isoformat()
    }
    print("[SERVER] returning init payload:", resp)
    return {"ok": True, "init": resp}

@app.get("/dataStreaming")
async def get_data_streaming():
    print("[SERVER] GET /dataStreaming -> pedido de streaming")
    # Datos dummy (simulan jsonData.data)
    dummy = {
        "count": 5,
        "data": [
            {"t": 0, "value": 0.1},
            {"t": 1, "value": 0.2},
            {"t": 2, "value": 0.15},
            {"t": 3, "value": 0.4},
            {"t": 4, "value": 0.33}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    print("[SERVER] dataStreaming payload preparado")
    return {"ok": True, "data": dummy}

@app.get("/data")
async def get_data():
    print("[SERVER] GET /data -> pedido de data (one-shot)")
    # Reusar dummy
    dummy = {
        "count": 3,
        "data": [10, 20, 30],
        "timestamp": datetime.utcnow().isoformat()
    }
    print("[SERVER] data payload preparado")
    return {"ok": True, "data": dummy}

@app.post("/command")
async def post_command(cmd: CommandRequest):
    # Solo imprimimos para verificar que llegan los datos
    print("[SERVER] POST /command -> recibido:")
    print("  command:", cmd.command)
    print("  data:", cmd.data)
    # Simulamos comportamiento: aceptamos comandos conocidos
    if cmd.command not in ("startLiveData", "scheduleMeasurement", "stopLiveData"):
        print("[SERVER] comando no soportado:", cmd.command)
        raise HTTPException(status_code=400, detail="command not supported")
    # devolver ack
    ack = {
        "ok": True,
        "received": True,
        "command": cmd.command,
        "ts": datetime.utcnow().isoformat()
    }
    print("[SERVER] ack ->", ack)
    return ack
