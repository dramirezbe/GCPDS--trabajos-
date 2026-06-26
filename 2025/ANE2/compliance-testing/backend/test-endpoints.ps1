# Test de endpoints del backend ANE
Write-Host "🧪 Iniciando pruebas de endpoints..." -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:3000"

# Función para hacer requests con manejo de errores
function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [string]$Description
    )
    
    Write-Host "📡 $Description" -ForegroundColor Yellow
    Write-Host "   Método: $Method" -ForegroundColor Gray
    Write-Host "   URL: $Url" -ForegroundColor Gray
    
    try {
        if ($Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Body $jsonBody -ContentType "application/json"
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method
        }
        
        Write-Host "   ✅ Success" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 5
        Write-Host ""
        return $response
    }
    catch {
        Write-Host "   ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        return $null
    }
}

# Test 1: Endpoint raíz
Test-Endpoint -Method "GET" -Url "$baseUrl/" -Description "Test 1: Endpoint raíz"

# Test 2: Listar sensores
Test-Endpoint -Method "GET" -Url "$baseUrl/api/sensors" -Description "Test 2: GET /api/sensors - Listar sensores"

# Test 3: Listar antenas
Test-Endpoint -Method "GET" -Url "$baseUrl/api/antennas" -Description "Test 3: GET /api/antennas - Listar antenas"

# Test 4: Listar campañas
Test-Endpoint -Method "GET" -Url "$baseUrl/api/campaigns" -Description "Test 4: GET /api/campaigns - Listar campañas"

# Test 5: Crear un sensor de prueba
$newSensor = @{
    mac = "AA:BB:CC:DD:EE:FF"
    name = "Sensor Test"
    description = "Sensor de prueba PostgreSQL"
    lat = 4.6097
    lng = -74.0817
    alt = 2640
    status = "active"
}
$sensor = Test-Endpoint -Method "POST" -Url "$baseUrl/api/sensors" -Body $newSensor -Description "Test 5: POST /api/sensors - Crear sensor"

# Test 6: Crear una antena de prueba
$newAntenna = @{
    name = "Antena Test"
    type = "VHF"
    frequency_min_hz = 25000000
    frequency_max_hz = 1000000000
    gain_db = 1.5
    description = "Antena de prueba PostgreSQL"
}
$antenna = Test-Endpoint -Method "POST" -Url "$baseUrl/api/antennas" -Body $newAntenna -Description "Test 6: POST /api/antennas - Crear antena"

# Test 7: Obtener el sensor creado
if ($sensor -and $sensor.id) {
    Test-Endpoint -Method "GET" -Url "$baseUrl/api/sensors/$($sensor.id)" -Description "Test 7: GET /api/sensors/:id - Obtener sensor por ID"
}

# Test 8: Obtener la antena creada
if ($antenna -and $antenna.id) {
    Test-Endpoint -Method "GET" -Url "$baseUrl/api/antennas/$($antenna.id)" -Description "Test 8: GET /api/antennas/:id - Obtener antena por ID"
}

# Test 9: Asignar antena a sensor
if ($sensor -and $sensor.id -and $antenna -and $antenna.id) {
    $assignment = @{
        antenna_id = $antenna.id
        port = 1
    }
    Test-Endpoint -Method "POST" -Url "$baseUrl/api/sensors/$($sensor.id)/antennas" -Body $assignment -Description "Test 9: POST /api/sensors/:id/antennas - Asignar antena a sensor"
}

# Test 10: Listar antenas del sensor
if ($sensor -and $sensor.id) {
    Test-Endpoint -Method "GET" -Url "$baseUrl/api/sensors/$($sensor.id)/antennas" -Description "Test 10: GET /api/sensors/:id/antennas - Listar antenas del sensor"
}

# Test 11: Crear una campaña de prueba
if ($sensor) {
    $newCampaign = @{
        name = "Campaña Test PostgreSQL"
        description = "Campaña de prueba"
        start_date = "2025-12-14"
        end_date = "2025-12-15"
        start_time = "08:00"
        end_time = "18:00"
        interval_seconds = 300
        start_freq_mhz = 88
        end_freq_mhz = 108
        bandwidth_mhz = 20
        resolution_khz = 100
        sensors = @($sensor.mac)
        preset = "custom"
        config = @{
            antenna_port = 1
            lna_gain = 20
            vga_gain = 30
        }
    }
    $campaign = Test-Endpoint -Method "POST" -Url "$baseUrl/api/campaigns" -Body $newCampaign -Description "Test 11: POST /api/campaigns - Crear campaña"
    
    # Test 12: Obtener la campaña creada
    if ($campaign -and $campaign.id) {
        Test-Endpoint -Method "GET" -Url "$baseUrl/api/campaigns/$($campaign.id)" -Description "Test 12: GET /api/campaigns/:id - Obtener campaña por ID"
    }
}

Write-Host "🎉 Pruebas completadas!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Resumen:" -ForegroundColor Cyan
Write-Host "   - Endpoints probados: 12" -ForegroundColor White
Write-Host "   - Base de datos: PostgreSQL" -ForegroundColor White
Write-Host "   - Servidor: http://localhost:3000" -ForegroundColor White
