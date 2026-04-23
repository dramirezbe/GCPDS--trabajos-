# Ejemplos de Uso - Endpoint `/api/sensor/:mac/campaigns`

## 📖 Descripción

Este endpoint permite a los sensores físicos obtener la lista de campañas de medición que tienen asignadas.

**URL:** `GET /api/sensor/:mac/campaigns`

**Autenticación:** No requerida

## 🔗 Parámetros

### Path Parameters
- `mac` (string, requerido): Dirección MAC del sensor
  - Ejemplo: `d0:65:78:9c:dd:d0`

### Query Parameters
- `status` (string, opcional): Filtrar campañas por estado
  - Valores válidos: `scheduled`, `active`, `running`, `completed`, `cancelled`
  - Si no se proporciona, devuelve solo: `scheduled`, `active`, `running`

## 📋 Ejemplos de Solicitudes

### Ejemplo 1: Obtener todas las campañas activas de un sensor

```bash
curl -X GET "http://localhost:3000/api/sensor/d0:65:78:9c:dd:d0/campaigns"
```

**Respuesta (200 OK):**
```json
{
  "campaigns": [
    {
      "campaign_id": 1,
      "status": "scheduled",
      "center_freq_hz": 98000000,
      "timeframe": {
        "start": 1704067200000,
        "end": 1704672000000
      },
      "rbw_hz": 10000,
      "sample_rate_hz": 20000000,
      "antenna_port": 1,
      "acquisition_period_s": 300,
      "span": 20000000,
      "scale": "dbm",
      "window": "hamming",
      "overlap": 0.5,
      "lna_gain": 0,
      "vga_gain": 0,
      "antenna_amp": false,
      "filter": null
    },
    {
      "campaign_id": 2,
      "status": "running",
      "center_freq_hz": 450000000,
      "timeframe": {
        "start": 1704153600000,
        "end": 1704758400000
      },
      "rbw_hz": 50000,
      "sample_rate_hz": 20000000,
      "antenna_port": 2,
      "acquisition_period_s": 600,
      "span": 10000000,
      "scale": "dbm",
      "window": "hann",
      "overlap": 0.75,
      "lna_gain": 10,
      "vga_gain": 15,
      "antenna_amp": true,
      "filter": {
        "type": "bandpass",
        "filter_bw_hz": 5000000,
        "order_filter": 4
      }
    }
  ]
}
```

### Ejemplo 2: Filtrar campañas por estado

```bash
curl -X GET "http://localhost:3000/api/sensor/d0:65:78:9c:dd:d0/campaigns?status=scheduled"
```

**Respuesta (200 OK):**
```json
{
  "campaigns": [
    {
      "campaign_id": 1,
      "status": "scheduled",
      "center_freq_hz": 98000000,
      "timeframe": {
        "start": 1704067200000,
        "end": 1704672000000
      },
      "rbw_hz": 10000,
      "sample_rate_hz": 20000000,
      "antenna_port": 1,
      "acquisition_period_s": 300,
      "span": 20000000,
      "scale": "dbm",
      "window": "hamming",
      "overlap": 0.5,
      "lna_gain": 0,
      "vga_gain": 0,
      "antenna_amp": false,
      "filter": null
    }
  ]
}
```

### Ejemplo 3: Sensor sin campañas asignadas

```bash
curl -X GET "http://localhost:3000/api/sensor/aa:bb:cc:dd:ee:ff/campaigns"
```

**Respuesta (200 OK):**
```json
{
  "campaigns": []
}
```

### Ejemplo 4: Sensor inexistente

```bash
curl -X GET "http://localhost:3000/api/sensor/00:00:00:00:00:00/campaigns"
```

**Respuesta (404 Not Found):**
```json
{
  "error": "Sensor not found"
}
```

## 🔍 Descripción de Campos

### Campos Principales

| Campo | Tipo | Descripción | Puede ser null |
|-------|------|-------------|----------------|
| `campaign_id` | number | ID único de la campaña | No |
| `status` | string | Estado actual: `scheduled`, `active`, `running`, `completed`, `cancelled` | No |
| `center_freq_hz` | number | Frecuencia central en Hz | **Sí** |
| `timeframe` | object | Ventana temporal de la campaña | No |
| `timeframe.start` | number | Timestamp de inicio (ms) | **Sí** |
| `timeframe.end` | number | Timestamp de fin (ms) | **Sí** |
| `rbw_hz` | number | Resolución de ancho de banda (Hz) | No |
| `sample_rate_hz` | number | Tasa de muestreo (Hz) | No |
| `antenna_port` | number | Puerto de antena (1-4) | No |
| `acquisition_period_s` | number | Intervalo de adquisición (segundos) | No |
| `span` | number | Ancho de banda (Hz) | No |
| `scale` | string | Escala: `dbm`, `dBmV`, `dBuV`, `V`, `W` | No |
| `window` | string | Función de ventana: `hamming`, `hann`, `blackman`, etc. | No |
| `overlap` | number | Solapamiento (0.0-1.0) | No |
| `lna_gain` | number | Ganancia LNA (dB) | No |
| `vga_gain` | number | Ganancia VGA (dB) | No |
| `antenna_amp` | boolean | Amplificador de antena activo | No |
| `filter` | object | Configuración de filtro | **Sí** |

### Objeto `filter` (opcional)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `type` | string | Tipo: `lowpass`, `bandpass`, `highpass` |
| `filter_bw_hz` | number | Ancho de banda del filtro (Hz) |
| `order_filter` | number | Orden del filtro |

## ⚠️ Notas Importantes

### 1. Valores null en campos críticos

Los campos `center_freq_hz`, `timeframe.start` y `timeframe.end` **siempre están presentes** en la respuesta, pero pueden tener valor `null` si:

- `center_freq_hz` es `null` cuando:
  - La campaña no tiene `start_freq_mhz` o `end_freq_mhz` configurados
  - Y tampoco tiene `center_freq_hz` en el objeto `config`

- `timeframe.start` es `null` cuando:
  - La campaña no tiene `start_date` o `start_time` configurados
  - O hay un error al parsear las fechas

- `timeframe.end` es `null` cuando:
  - La campaña no tiene `end_date` o `end_time` configurados
  - O hay un error al parsear las fechas

**Recomendación:** Los sensores deben validar estos valores antes de usarlos.

```python
# Ejemplo en Python
campaigns = response.json()['campaigns']
for campaign in campaigns:
    if campaign['center_freq_hz'] is None:
        print(f"⚠️  Campaña {campaign['campaign_id']} sin frecuencia central definida")
        continue
    
    if campaign['timeframe']['start'] is None or campaign['timeframe']['end'] is None:
        print(f"⚠️  Campaña {campaign['campaign_id']} sin timeframe completo")
        continue
    
    # Procesar campaña...
```

### 2. Filtrado automático por estado

Si **no se proporciona** el parámetro `status`, el endpoint devuelve solo campañas en estados "activos":
- `scheduled` (programadas)
- `active` (activas)
- `running` (en ejecución)

Esto evita que los sensores procesen campañas ya completadas o canceladas.

### 3. Lista vacía vs Error 404

- **Lista vacía `[]`**: El sensor existe pero no tiene campañas asignadas (respuesta normal)
- **Error 404**: El sensor no existe en la base de datos (error que debe manejarse)

## 🔄 Flujo de Trabajo Típico

### Para Sensores Físicos

```python
import requests
import time

BACKEND_URL = "http://rsm.ane.gov.co:3000"
SENSOR_MAC = "d0:65:78:9c:dd:d0"

def obtener_campanas():
    """Obtiene las campañas asignadas al sensor."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/sensor/{SENSOR_MAC}/campaigns"
        )
        response.raise_for_status()
        return response.json()['campaigns']
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("❌ Sensor no encontrado en el sistema")
        else:
            print(f"❌ Error HTTP: {e}")
        return []
    except Exception as e:
        print(f"❌ Error al obtener campañas: {e}")
        return []

def ejecutar_campaña(campaign):
    """Ejecuta una campaña de medición."""
    if campaign['center_freq_hz'] is None:
        print(f"⚠️  Campaña {campaign['campaign_id']} sin frecuencia definida, omitiendo...")
        return
    
    print(f"📡 Ejecutando campaña {campaign['campaign_id']}:")
    print(f"  - Frecuencia central: {campaign['center_freq_hz']} Hz")
    print(f"  - RBW: {campaign['rbw_hz']} Hz")
    print(f"  - Período: {campaign['acquisition_period_s']} s")
    
    # Configurar SDR...
    # Adquirir datos...
    # Enviar a POST /api/sensor/data

def main():
    print("🚀 Iniciando sensor...")
    
    while True:
        # Obtener campañas cada 5 minutos
        campaigns = obtener_campanas()
        
        if not campaigns:
            print("ℹ️  No hay campañas asignadas")
            time.sleep(300)  # 5 minutos
            continue
        
        print(f"📋 {len(campaigns)} campaña(s) encontrada(s)")
        
        for campaign in campaigns:
            if campaign['status'] in ['scheduled', 'running']:
                ejecutar_campaña(campaign)
        
        time.sleep(300)  # 5 minutos

if __name__ == "__main__":
    main()
```

## 🧪 Testing

### Script de PowerShell
```powershell
.\backend\test-campaigns-endpoint.ps1
```

### Script de Bash
```bash
#!/bin/bash
BASE_URL="http://localhost:3000"
MAC="d0:65:78:9c:dd:d0"

echo "🧪 Probando endpoint de campañas"
echo ""

# Test 1: Obtener campañas
echo "Test 1: GET /api/sensor/$MAC/campaigns"
curl -s "$BASE_URL/api/sensor/$MAC/campaigns" | jq .
echo ""

# Test 2: Filtrar por estado
echo "Test 2: Con filtro status=scheduled"
curl -s "$BASE_URL/api/sensor/$MAC/campaigns?status=scheduled" | jq .
echo ""

# Test 3: Sensor inexistente
echo "Test 3: Sensor inexistente (debe dar 404)"
curl -s -w "\nHTTP Status: %{http_code}\n" "$BASE_URL/api/sensor/00:00:00:00:00:00/campaigns"
echo ""
```

## 📚 Referencias

- [GET-campaigns.jsonc](../json/GET-campaigns.jsonc) - Formato completo del endpoint
- [API_SENSOR_COMPATIBILITY.md](../API_SENSOR_COMPATIBILITY.md) - Compatibilidad general
- [backend/ENDPOINT_CAMPAIGNS_CAMBIOS.md](ENDPOINT_CAMPAIGNS_CAMBIOS.md) - Log de cambios

---

**Última actualización:** 14 de Diciembre de 2025

