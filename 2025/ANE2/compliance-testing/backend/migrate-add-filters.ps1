#!/usr/bin/env pwsh
# Script para agregar columnas de filtro a la base de datos

Write-Host "🔧 Agregando columnas de filtro a sensor_configurations..." -ForegroundColor Cyan

# Verificar si el archivo SQL existe
if (-not (Test-Path "add-filter-columns.sql")) {
    Write-Host "❌ Error: No se encontró el archivo add-filter-columns.sql" -ForegroundColor Red
    exit 1
}

# Ejecutar el script SQL en el contenedor de PostgreSQL
Write-Host "📝 Ejecutando migración..." -ForegroundColor Yellow

try {
    # Opción 1: Si usas Docker
    docker exec -i ane-postgres psql -U admin -d ane_realtime_db -f /docker-entrypoint-initdb.d/add-filter-columns.sql
    
    # Si el archivo no está en el volumen, ejecutarlo directamente
    Get-Content add-filter-columns.sql | docker exec -i ane-postgres psql -U admin -d ane_realtime_db
    
    Write-Host "✅ Migración completada exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "Las siguientes columnas fueron agregadas a sensor_configurations:" -ForegroundColor Green
    Write-Host "  - filter_type (VARCHAR)" -ForegroundColor White
    Write-Host "  - filter_bw_hz (INTEGER)" -ForegroundColor White
    Write-Host "  - filter_order (INTEGER)" -ForegroundColor White
}
catch {
    Write-Host "❌ Error ejecutando migración: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Puedes ejecutar manualmente el contenido de add-filter-columns.sql" -ForegroundColor Yellow
    exit 1
}
