"""!
@file main.py
@brief API REST y Servidor Web para gestión de sensores SDR.
"""

from fastapi import FastAPI, Path
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os
import json

app = FastAPI(title="SDR Sensor Fleet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === AÑADE ESTA LÍNEA AQUÍ ===
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "frontend", "dist", "assets")), name="assets")
# =============================

# ==========================================
# SERVIR EL FRONTEND (HTML)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "dist", "index.html")
    if not os.path.exists(html_path):
        return "<h1>Error: Archivo index.html no encontrado.</h1>"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# ==========================================
# MODELOS DE DATOS
# ==========================================
class FilterConfig(BaseModel):
    start_freq_hz: int
    end_freq_hz: int

class ServerRealtimeConfig(BaseModel):
    method_psd: str = "pfb"
    center_freq_hz: int
    sample_rate_hz: int
    rbw_hz: int
    window: str = "hamming"
    overlap: float = 0.0
    lna_gain: int = 0
    vga_gain: int = 0
    antenna_amp: bool = False
    antenna_port: int = 1  
    ppm_error: int = 0
    demodulation: Optional[str] = None
    filter: Optional[FilterConfig] = None

class SensorDataPayload(BaseModel):
    mac: str
    campaign_id: Optional[int] = None
    Pxx: List[float]
    start_freq_hz: int
    end_freq_hz: int
    timestamp: int

SENSORS_DB: Dict[str, Dict[str, Any]] = {}

def get_or_create_sensor(mac: str):
    if mac not in SENSORS_DB:
        SENSORS_DB[mac] = {
            "config": ServerRealtimeConfig(
                method_psd="pfb", 
                center_freq_hz=0, 
                sample_rate_hz=0,
                rbw_hz=0, 
                window="hamming", 
                overlap=0.0, 
                lna_gain=0, 
                vga_gain=0,
                antenna_amp=False, 
                antenna_port=1, 
                ppm_error=0, 
                demodulation=None
            ),
            "latest_data": None
        }
        print(f"\n[INFO] Nuevo sensor detectado ({mac}). Inicializado con config en 0.")

# ==========================================
# ENDPOINTS DE LA API (VERBOSE)
# ==========================================
@app.get("/{mac}/realtime", response_model=ServerRealtimeConfig)
def get_config(mac: str = Path(...)):
    get_or_create_sensor(mac)
    config_dict = SENSORS_DB[mac]["config"].model_dump()
    
    print(f"\n[VERBOSE] GET /{mac}/realtime -> Enviando config al sensor:")
    print(json.dumps(config_dict, indent=2))
    
    return SENSORS_DB[mac]["config"]

@app.post("/{mac}/realtime", response_model=ServerRealtimeConfig)
def update_config(new_config: ServerRealtimeConfig, mac: str = Path(...)):
    get_or_create_sensor(mac)
    SENSORS_DB[mac]["config"] = new_config
    config_dict = new_config.model_dump()
    
    print(f"\n[VERBOSE] POST /{mac}/realtime -> Nueva config recibida del Frontend:")
    print(json.dumps(config_dict, indent=2))
    
    return SENSORS_DB[mac]["config"]

# NUEVO: Ya no pide la MAC en la URL.
@app.post("/data")
def upload_sensor_data(payload: SensorDataPayload):
    # Extraemos la MAC directamente del cuerpo del JSON
    mac = payload.mac
    get_or_create_sensor(mac)
    
    payload_dict = payload.model_dump()
    
    # Clonar y truncar Pxx para el log (para no saturar la consola)
    log_data = payload_dict.copy()
    if len(log_data["Pxx"]) > 3:
        log_data["Pxx"] = log_data["Pxx"][:3] + [f"... ({len(payload_dict['Pxx'])} items en total)"]
        
    print(f"\n[VERBOSE] POST /data -> Datos subidos por el sensor SDR ({mac}):")
    print(json.dumps(log_data, indent=2))
    
    # Guardar los datos completos (sin truncar) en la base de datos
    SENSORS_DB[mac]["latest_data"] = payload_dict
    return {"status": "success"}

@app.get("/{mac}/data")
def get_sensor_data(mac: str = Path(...)):
    get_or_create_sensor(mac)
    
    if SENSORS_DB[mac]["latest_data"] is None:
        empty_state = {
            "mac": mac,
            "Pxx": [],
            "start_freq_hz": 0,
            "end_freq_hz": 0,
            "timestamp": 0
        }
        return empty_state
        
    return SENSORS_DB[mac]["latest_data"]

# ==========================================
# EJECUCIÓN DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    print("=====================================================")
    print(" Iniciando SDR Dashboard y API en http://0.0.0.0:8005 ")
    print("=====================================================")
    uvicorn.run(app, host="0.0.0.0", port=8005)