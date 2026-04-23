# Simulador de Audio AM/FM

## ✅ Implementación Completa

Se ha agregado al simulador de sensores la capacidad de simular **demodulación AM/FM con audio en tiempo real**.

## 🎯 Características Implementadas

### 1. Menú Interactivo
Al iniciar el simulador, ahora pregunta:
- Número de puntos de frecuencia (1K, 10K, 100K, 500K)
- **Tipo de demodulación**: No, AM, o FM

### 2. Generación de Audio Simulado
- **Tono sinusoidal de 1 kHz** con ruido
- Sample rate: **48 kHz**
- Duración por paquete: **500 ms**
- Formato: PCM codificado en **base64**
- Envío cada **500 ms** cuando hay demodulación activa

### 3. Métricas Simuladas

#### Para AM (Profundidad de Modulación):
```javascript
{
  unit: "percent",
  peak_to_peak: 30-50%,
  peak_deviation: 90-100%,
  rms_deviation: 15-25%
}
```

#### Para FM (Excursión de Frecuencia):
```javascript
{
  unit: "hz",
  peak_to_peak_hz: 70-80 kHz,
  peak_deviation_hz: 220-235 kHz,
  rms_deviation_hz: 40-50 kHz
}
```

### 4. Endpoints Utilizados

**Datos de Espectro + Métricas:**
```
POST /api/sensor/data
{
  mac, timestamp, start_freq_hz, end_freq_hz, Pxx,
  excursion: {...},  // Si es FM
  depth: {...}       // Si es AM
}
```

**Audio Streaming:**
```
POST /api/sensor/audio
{
  mac, audio (base64), demodType, timestamp
}
```

## 🚀 Cómo Usar

### Opción 1: Menú Interactivo
```bash
cd backend
npm run simulator
# Seleccionar opción 1 (1,000 puntos)
# Seleccionar opción 2 (AM) o 3 (FM)
```

### Opción 2: Argumentos por Línea de Comandos
```bash
cd backend
npm run simulator 1000
# Luego seleccionar AM o FM en el menú
```

## 📊 Salida del Simulador

Con demodulación AM activa:
```
╔════════════════════════════════════════════════════════╗
║  SIMULADOR DE SENSOR DE ESPECTRO RADIOELÉCTRICO        ║
╚════════════════════════════════════════════════════════╝

📍 Sensor: Sensor Cali Sur
🆔 MAC: 11:22:33:44:55:66
📻 Rango: 88 - 108 MHz (FM)
📊 Puntos: 1,000
⏱️  Intervalo: 2s
🎵 Demodulación: AM en 95.5 MHz
🔊 Audio: Tono simulado de 1 kHz cada 500ms
🌐 API: http://localhost:3000/api

📡 [4:34:47 PM] Datos enviados: {...}
🎵 [4:34:48 PM] Audio AM enviado
🎵 [4:34:48 PM] Audio AM enviado
```

## 🔄 Flujo de Datos

```
┌─────────────┐
│  Simulador  │
└──────┬──────┘
       │
       ├─── Cada 2s  ──> POST /api/sensor/data (Espectro + Métricas)
       │
       └─── Cada 500ms ─> POST /api/sensor/audio (Audio PCM)
                          │
                          ▼
                    ┌──────────┐
                    │ WebSocket│
                    └────┬─────┘
                         │
                         ▼
                   ┌──────────┐
                   │ Frontend │
                   │  - AudioPlayer
                   │  - Métricas AM/FM
                   └──────────┘
```

## 🎨 Visualización en Frontend

Cuando el preset AM/FM está activo y el sensor envía datos:

1. **AudioPlayer** muestra:
   - Control Play/Pause
   - Volumen ajustable
   - Indicador de streaming en vivo

2. **Métricas** se muestran en tarjetas:
   - **AM**: Tarjeta verde con profundidad de modulación
   - **FM**: Tarjeta azul con excursión de frecuencia

## ✅ Estado Actual

- ✅ Simulador genera audio PCM
- ✅ Envía métricas AM/FM
- ✅ Backend recibe y broadcast por WebSocket
- ✅ Frontend tiene AudioPlayer funcional
- ✅ Frontend muestra métricas en tiempo real

## 🧪 Prueba Realizada

Ejecutado exitosamente con:
- 1,000 puntos de frecuencia
- Demodulación AM activa
- Audio enviado cada 500ms
- Métricas incluidas en datos de espectro
