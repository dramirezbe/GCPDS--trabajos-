# Script para probar el nuevo endpoint /api/sensor/:mac/campaigns

Write-Host "🧪 Probando endpoint de campañas para sensores" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:3000"
$sensorMac = "d0:65:78:9c:dd:d0"

# Test 1: Obtener campañas del sensor
Write-Host "📋 Test 1: GET /api/sensor/$sensorMac/campaigns" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/sensor/$sensorMac/campaigns" -Method Get
    Write-Host "✅ Respuesta exitosa:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
    Write-Host ""
    
    # Verificar estructura de respuesta
    if ($response.campaigns) {
        Write-Host "✅ Campo 'campaigns' presente" -ForegroundColor Green
        
        if ($response.campaigns.Count -gt 0) {
            $campaign = $response.campaigns[0]
            
            # Verificar campos críticos
            Write-Host "Verificando campos críticos de la primera campaña:" -ForegroundColor Cyan
            
            if ($null -ne $campaign.center_freq_hz) {
                Write-Host "  ✅ center_freq_hz: $($campaign.center_freq_hz)" -ForegroundColor Green
            } else {
                Write-Host "  ❌ center_freq_hz es null" -ForegroundColor Red
            }
            
            if ($null -ne $campaign.timeframe) {
                Write-Host "  ✅ timeframe presente" -ForegroundColor Green
                Write-Host "    - start: $($campaign.timeframe.start)" -ForegroundColor Gray
                Write-Host "    - end: $($campaign.timeframe.end)" -ForegroundColor Gray
            } else {
                Write-Host "  ❌ timeframe es null" -ForegroundColor Red
            }
            
            # Otros campos importantes
            $requiredFields = @('campaign_id', 'status', 'rbw_hz', 'sample_rate_hz', 'antenna_port', 
                               'acquisition_period_s', 'span', 'scale', 'window', 'overlap')
            
            foreach ($field in $requiredFields) {
                if ($null -ne $campaign.$field) {
                    Write-Host "  ✅ $field`: $($campaign.$field)" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠️  $field es null" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "ℹ️  No hay campañas asignadas a este sensor" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Campo 'campaigns' no presente en la respuesta" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Test 2: Obtener campañas con filtro de estado
Write-Host "📋 Test 2: GET /api/sensor/$sensorMac/campaigns?status=scheduled" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/sensor/$sensorMac/campaigns?status=scheduled" -Method Get
    Write-Host "✅ Respuesta exitosa con filtro 'scheduled':" -ForegroundColor Green
    Write-Host "  Número de campañas: $($response.campaigns.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Test 3: Sensor inexistente
Write-Host "📋 Test 3: GET /api/sensor/00:00:00:00:00:00/campaigns (sensor inexistente)" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/sensor/00:00:00:00:00:00/campaigns" -Method Get
    Write-Host "⚠️  Respuesta recibida cuando se esperaba 404" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
        Write-Host "✅ Error 404 esperado: Sensor no encontrado" -ForegroundColor Green
    } else {
        Write-Host "❌ Error inesperado: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "🎉 Tests completados" -ForegroundColor Green
Write-Host ""
Write-Host "Notas:" -ForegroundColor Cyan
Write-Host "  - El endpoint cambió de /jobs a /campaigns" -ForegroundColor Gray
Write-Host "  - Ahora siempre envía 'timeframe' y 'center_freq_hz'" -ForegroundColor Gray
Write-Host "  - Estos valores pueden ser null si no hay datos en la campaña" -ForegroundColor Gray

