import { query } from './connection';

async function validateData() {
  console.log('\n📊 Validando datos importados:\n');
  
  // Contar registros por servicio
  const servicios = await query(`
    SELECT servicio, COUNT(*) as total, COUNT(DISTINCT municipio) as municipios
    FROM frecuencias_consolidadas
    GROUP BY servicio
    ORDER BY COUNT(*) DESC
  `);
  
  console.log('Registros por servicio:');
  servicios.rows.forEach(row => {
    console.log(`  ${row.servicio}: ${row.total} registros en ${row.municipios} municipios`);
  });
  
  // Muestras de frecuencias FM
  console.log('\n📻 Muestra de frecuencias FM:');
  const fm = await query(`
    SELECT frecuencia, potencia, unidad_potencia, municipio
    FROM frecuencias_consolidadas
    WHERE servicio = 'Radiodifusión Sonora en FM'
    ORDER BY frecuencia
    LIMIT 10
  `);
  
  fm.rows.forEach(row => {
    console.log(`  ${row.frecuencia} MHz - ${row.potencia} ${row.unidad_potencia} - ${row.municipio}`);
  });
  
  // Rango de frecuencias
  console.log('\n📡 Rangos de frecuencias por servicio:');
  const rangos = await query(`
    SELECT servicio, 
           MIN(frecuencia) as min_freq, 
           MAX(frecuencia) as max_freq
    FROM frecuencias_consolidadas
    GROUP BY servicio
    ORDER BY MIN(frecuencia)
  `);
  
  rangos.rows.forEach(row => {
    console.log(`  ${row.servicio}: ${row.min_freq} - ${row.max_freq} MHz`);
  });
  
  process.exit(0);
}

validateData().catch(console.error);
