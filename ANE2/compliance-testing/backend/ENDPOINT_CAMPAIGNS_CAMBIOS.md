# Cambios en Endpoint de Campañas para Sensores

## Resumen de Cambios

Se han realizado las siguientes correcciones en el archivo `backend/src/routes/sensor.ts`:

### 1. Corrección del nombre del endpoint
- **Antes**: `/api/sensor/:mac/campains` (error tipográfico)
- **Ahora**: `/api/sensor/:mac/campaigns` (correcto)

### 2. Eliminación de duplicados
- Se eliminó el endpoint duplicado que había en las líneas 752-851
- Ahora solo hay un endpoint `/api/sensor/:mac/campaigns` consolidado

### 3. Mejoras en la información enviada

El endpoint ahora **siempre** envía información completa para estas 3 variables críticas:

#### `timeframe`
```json
{
  "start": 1704067200000,  // timestamp en ms o null
  "end": 1704672000000      // timestamp en ms o null
}
```
- Se calcula desde `start_date + start_time` y `end_date + end_time` de la campaña
- Si hay errores en el parsing, se registran en consola y se devuelve `null`

#### `center_freq_hz`
```json
{
  "center_freq_hz": 98000000  // frecuencia central en Hz o null
}
```
- Se calcula como el promedio de `start_freq_mhz` y `end_freq_mhz` convertido a Hz
- Si no están disponibles en la campaña, se toma de `config.center_freq_hz`
- Si tampoco está disponible, se devuelve `null`

### 4. Estructura completa de respuesta

El endpoint ahora devuelve:

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

## Uso del Endpoint

### Para Sensores
```bash
GET /api/sensor/{MAC_ADDRESS}/campaigns
```

**Ejemplo:**
```bash
curl http://localhost:3000/api/sensor/d0:65:78:9c:dd:d0/campaigns
```

### Con Filtro de Estado (opcional)
```bash
GET /api/sensor/{MAC_ADDRESS}/campaigns?status=scheduled
```

**Estados válidos:**
- `scheduled` - Campaña programada
- `active` - Campaña activa
- `running` - Campaña en ejecución
- `completed` - Campaña completada
- `cancelled` - Campaña cancelada

**Si no se especifica estado**, el endpoint devuelve solo campañas en estados: `scheduled`, `active` o `running`

## Validaciones Agregadas

1. **Verificación del Sensor**: El endpoint ahora verifica que el sensor existe antes de buscar campañas
   - Si no existe: devuelve `404` con `{"error": "Sensor not found"}`

2. **Manejo de Config NULL**: El config de campaña se maneja de forma segura
   - Si es string JSON, se parsea
   - Si es null/undefined, se usa objeto vacío `{}`

3. **Logging Mejorado**: 
   - Se registra el número de campañas encontradas
   - Se registran errores en parsing de fechas

## Compatibilidad

El endpoint es **100% compatible** con el formato esperado por los sensores físicos en su archivo `GET-campaigns.jsonc`.

## Notas Técnicas

- El cambio de `/jobs` a `/campaigns` sigue las convenciones REST estándar
- La información de `timeframe` y `center_freq_hz` ahora siempre se envía (aunque pueda ser `null` si no hay datos)
- Se mantiene retrocompatibilidad con el filtro opcional de estado

