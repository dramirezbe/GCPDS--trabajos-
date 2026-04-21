# Script de prueba del endpoint de reportes de cumplimiento normativo

$API_BASE_URL = "http://localhost:3000/api"

Write-Host "`n🧪 Prueba del endpoint de reportes de cumplimiento normativo`n" -ForegroundColor Cyan

# 1. Verificar que el backend esté corriendo
Write-Host "1. Verificando conexión al backend..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE_URL/../" -Method Get
    Write-Host "   ✅ Backend conectado: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Error: Backend no está corriendo en puerto 3000" -ForegroundColor Red
    exit 1
}

# 2. Listar campañas disponibles
Write-Host "`n2. Listando campañas disponibles..." -ForegroundColor Yellow
try {
    $campaigns = Invoke-RestMethod -Uri "$API_BASE_URL/campaigns" -Method Get
    Write-Host "   ✅ Encontradas $($campaigns.Count) campañas" -ForegroundColor Green
    
    if ($campaigns.Count -gt 0) {
        $campaign = $campaigns[0]
        Write-Host "   📋 Campaña de prueba: $($campaign.name) (ID: $($campaign.id))" -ForegroundColor Cyan
        
        # 3. Generar reporte de cumplimiento
        Write-Host "`n3. Generando reporte de cumplimiento para campaña $($campaign.id)..." -ForegroundColor Yellow
        try {
            $report = Invoke-RestMethod -Uri "$API_BASE_URL/reports/compliance/$($campaign.id)" -Method Post -ContentType "application/json"
            
            Write-Host "   ✅ Reporte generado exitosamente" -ForegroundColor Green
            Write-Host "`n   📊 Resumen del Reporte:" -ForegroundColor Cyan
            Write-Host "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
            Write-Host "   📍 Ubicación:" -ForegroundColor White
            Write-Host "      Departamento: $($report.ubicacion.departamento)" -ForegroundColor White
            Write-Host "      Municipio: $($report.ubicacion.municipio)" -ForegroundColor White
            Write-Host "      Código DANE: $($report.ubicacion.codigo_dane)" -ForegroundColor White
            Write-Host "      Coordenadas: $($report.ubicacion.coordenadas.latitud), $($report.ubicacion.coordenadas.longitud)" -ForegroundColor White
            
            Write-Host "`n   📈 Estadísticas:" -ForegroundColor White
            Write-Host "      Total mediciones: $($report.estadisticas.total_mediciones)" -ForegroundColor White
            Write-Host "      Autorizadas: $($report.estadisticas.autorizadas)" -ForegroundColor Green
            Write-Host "      No autorizadas: $($report.estadisticas.no_autorizadas)" -ForegroundColor Red
            Write-Host "      Porcentaje cumplimiento: $($report.estadisticas.porcentaje_cumplimiento)%" -ForegroundColor $(if([decimal]$report.estadisticas.porcentaje_cumplimiento -gt 80) { "Green" } else { "Yellow" })
            Write-Host "      Frecuencias únicas autorizadas: $($report.estadisticas.frecuencias_unicas_autorizadas)" -ForegroundColor White
            
            Write-Host "`n   🔍 Top 5 Mediciones:" -ForegroundColor White
            $report.mediciones | Select-Object -First 5 | ForEach-Object {
                $status = if($_.autorizado) { "✅ Autorizado" } else { "❌ No autorizado" }
                $color = if($_.autorizado) { "Green" } else { "Red" }
                Write-Host "      $($_.frecuencia_medida) MHz - $status - Servicio: $($_.servicio_autorizado)" -ForegroundColor $color
            }
            
            # Guardar reporte en archivo
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $filename = "reporte_cumplimiento_$($campaign.id)_$timestamp.json"
            $report | ConvertTo-Json -Depth 10 | Out-File $filename
            Write-Host "`n   💾 Reporte guardado en: $filename" -ForegroundColor Cyan
            
        } catch {
            Write-Host "   ❌ Error generando reporte:" -ForegroundColor Red
            Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
            
            if ($_.ErrorDetails.Message) {
                $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
                Write-Host "      Detalles: $($errorDetails.details)" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "   ⚠️  No hay campañas disponibles para probar" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Error listando campañas: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Gray
