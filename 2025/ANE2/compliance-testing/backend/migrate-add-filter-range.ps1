#!/usr/bin/env pwsh
# Script para agregar columnas de rango de filtro a la base de datos

Write-Host "🔧 Agregando columnas de RANGO de filtro a sensor_configurations..." -ForegroundColor Cyan

# Verificar si el archivo SQL existe
if (-not (Test-Path "add-filter-range-columns.sql")) {
    Write-Host "❌ Error: No se encontró el archivo add-filter-range-columns.sql" -ForegroundColor Red
    exit 1
}

# Ejecutar el script SQL en el contenedor de PostgreSQL
Write-Host "📝 Ejecutando migración..." -ForegroundColor Yellow

try {
    # Ejecutar directamente pasando el contenido por pipe a docker exec
    Get-Content add-filter-range-columns.sql | docker exec -i ane-postgres psql -U admin -d ane_realtime_db
    
    Write-Host "✅ Migración completada exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "Las siguientes columnas fueron agregadas a sensor_configurations:" -ForegroundColor Green
    Write-Host "  - filter_start_freq_hz (BIGINT)" -ForegroundColor White
    Write-Host "  - filter_end_freq_hz (BIGINT)" -ForegroundColor White
}
catch {
    Write-Host "❌ Error ejecutando migración: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Puedes ejecutar manualmente el contenido de add-filter-range-columns.sql" -ForegroundColor Yellow
    exit 1
}
