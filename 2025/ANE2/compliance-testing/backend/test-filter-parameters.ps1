# Script para probar los parámetros de filtro
$BaseUrl = "http://localhost:3000/api"
$SensorMac = "00:11:22:33:44:55" # Ajustar a una MAC válida

Write-Host "🧪 Probando configuración de filtros..." -ForegroundColor Cyan

# 1. Configurar sensor con filtros
$Config = @{
    mac = $SensorMac
    center_frequency = 98500000
    span = 20000000
    sample_rate_hz = 20000000
    resolution_hz = 1000
    antenna_port = 1
    filter = @{
        type = "bandpass"
        bw_hz = 500000
        order = 4
    }
}

$JsonConfig = $Config | ConvertTo-Json -Depth 5

Write-Host "📤 Enviando configuración:" -ForegroundColor Yellow
Write-Host $JsonConfig

try {
    $Response = Invoke-RestMethod -Uri "$BaseUrl/sensor/$SensorMac/configure" -Method Post -Body $JsonConfig -ContentType "application/json"
    Write-Host "✅ Configuración aceptada:" -ForegroundColor Green
    $Response | ConvertTo-Json -Depth 5 | Write-Host
} catch {
    Write-Host "❌ Error al configurar: $_" -ForegroundColor Red
    exit
}

# 2. Verificar configuración guardada
Write-Host "`n🔍 Verificando configuración guardada (GET /realtime)..." -ForegroundColor Yellow

try {
    $Realtime = Invoke-RestMethod -Uri "$BaseUrl/sensor/$SensorMac/realtime" -Method Get
    
    if ($Realtime.configuration.filter) {
        Write-Host "✅ Filtro encontrado en la configuración:" -ForegroundColor Green
        $Realtime.configuration.filter | ConvertTo-Json | Write-Host
        
        if ($Realtime.configuration.filter.type -eq "bandpass" -and $Realtime.configuration.filter.bw_hz -eq 500000) {
            Write-Host "✨ ¡Prueba exitosa! Los parámetros coinciden." -ForegroundColor Green
        } else {
            Write-Host "⚠️ Los parámetros no coinciden exactamente." -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ No se encontró objeto 'filter' en la respuesta." -ForegroundColor Red
        $Realtime.configuration | ConvertTo-Json | Write-Host
    }
} catch {
    Write-Host "❌ Error al obtener realtime: $_" -ForegroundColor Red
}
