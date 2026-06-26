import { readFileSync } from 'fs';
import { join } from 'path';
import { parse } from 'csv-parse/sync';
import { query } from './connection';

interface CoberturaRecord {
  ancho_de_banda: number;
  unidad_ancho_de_banda: string;
  potencia: number;
  unidad_potencia: string;
  municipio: string;
  frecuencia?: number | null;
}

async function createCoberturasTable() {
  console.log('📋 Creando tabla coberturas...');
  
  await query(`
    CREATE TABLE IF NOT EXISTS coberturas (
      id SERIAL PRIMARY KEY,
      frecuencia NUMERIC(15, 4),
      ancho_de_banda NUMERIC(15, 4),
      unidad_ancho_de_banda VARCHAR(10),
      potencia NUMERIC(15, 4),
      unidad_potencia VARCHAR(10),
      municipio VARCHAR(200),
      created_at TIMESTAMP DEFAULT NOW()
    )
  `);
  
  await query(`
    CREATE INDEX IF NOT EXISTS idx_coberturas_municipio ON coberturas(municipio);
  `);
  
  await query(`
    CREATE INDEX IF NOT EXISTS idx_coberturas_frecuencia ON coberturas(frecuencia) WHERE frecuencia IS NOT NULL;
  `);
  
  console.log('✅ Tabla coberturas creada con índices');
}

async function loadCSVData() {
  const csvPath = join('C:', 'ANE REALTIME', 'consolidado.csv');
  console.log(`📂 Leyendo archivo: ${csvPath}`);
  
  const fileContent = readFileSync(csvPath, 'utf-8');
  
  const cleanNumber = (value: string): number | null => {
    if (!value || value === '') return null;
    const cleaned = value.toString().replace(/\./g, '').replace(',', '.');
    const num = parseFloat(cleaned);
    return isNaN(num) ? null : num;
  };

  const rawRecords = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    delimiter: ';',
    trim: true,
    cast: false
  });
  
  // Filtrar solo registros de "cubrimiento"
  const records: CoberturaRecord[] = rawRecords
    .filter((rec: any) => {
      return rec.servicio && rec.servicio.toLowerCase() === 'cubrimiento';
    })
    .map((rec: any) => ({
      frecuencia: cleanNumber(rec.frecuencia),
      ancho_de_banda: cleanNumber(rec.ancho_de_banda) || 0,
      unidad_ancho_de_banda: rec.unidad_ancho_de_banda || '',
      potencia: cleanNumber(rec.potencia) || 0,
      unidad_potencia: rec.unidad_potencia || '',
      municipio: rec.municipio || ''
    }));
  
  console.log(`📊 Total de registros de cobertura a importar: ${records.length}`);
  
  // Verificar si ya hay datos
  const existingCount = await query('SELECT COUNT(*) as count FROM coberturas');
  const count = parseInt(existingCount.rows[0].count);
  
  if (count > 0) {
    console.log(`⚠️  La tabla ya contiene ${count} registros.`);
    const readline = require('readline').createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    await new Promise((resolve) => {
      readline.question('¿Desea eliminar los datos existentes y recargar? (si/no): ', (answer: string) => {
        readline.close();
        if (answer.toLowerCase() === 'si' || answer.toLowerCase() === 's') {
          resolve(true);
        } else {
          console.log('❌ Importación cancelada');
          process.exit(0);
        }
      });
    });
    
    await query('TRUNCATE TABLE coberturas RESTART IDENTITY');
    console.log('🗑️  Datos existentes eliminados');
  }
  
  // Insertar en lotes de 1000 registros
  const batchSize = 1000;
  let imported = 0;
  
  console.log('📤 Importando datos en lotes...');
  
  for (let i = 0; i < records.length; i += batchSize) {
    const batch = records.slice(i, i + batchSize);
    
    const values: any[] = [];
    const placeholders: string[] = [];
    
    batch.forEach((record, index) => {
      const offset = index * 6;
      placeholders.push(`($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6})`);
      values.push(
        record.frecuencia,
        record.ancho_de_banda,
        record.unidad_ancho_de_banda,
        record.potencia,
        record.unidad_potencia,
        record.municipio
      );
    });
    
    const sql = `INSERT INTO coberturas 
       (frecuencia, ancho_de_banda, unidad_ancho_de_banda, potencia, unidad_potencia, municipio)
       VALUES ${placeholders.join(', ')}`;
    
    await query(sql, values);
    
    imported += batch.length;
    const progress = ((imported / records.length) * 100).toFixed(1);
    process.stdout.write(`\r   Progreso: ${imported}/${records.length} (${progress}%)`);
  }
  
  console.log('\n✅ Datos importados exitosamente');
  
  // Estadísticas
  const stats = await query(`
    SELECT 
      COUNT(*) as total,
      COUNT(DISTINCT municipio) as municipios_unicos,
      COUNT(*) FILTER (WHERE frecuencia IS NOT NULL) as con_frecuencia,
      COUNT(*) FILTER (WHERE frecuencia IS NULL) as sin_frecuencia,
      MIN(frecuencia) as frecuencia_min,
      MAX(frecuencia) as frecuencia_max
    FROM coberturas
  `);
  
  const municipios = await query(`
    SELECT municipio, COUNT(*) as registros
    FROM coberturas
    GROUP BY municipio
    ORDER BY COUNT(*) DESC
    LIMIT 10
  `);
  
  console.log('\n📊 Estadísticas de la importación:');
  console.log(`   Total de registros: ${stats.rows[0].total}`);
  console.log(`   Municipios únicos: ${stats.rows[0].municipios_unicos}`);
  console.log(`   Con frecuencia: ${stats.rows[0].con_frecuencia}`);
  console.log(`   Sin frecuencia: ${stats.rows[0].sin_frecuencia}`);
  if (stats.rows[0].frecuencia_min) {
    console.log(`   Frecuencia mínima: ${stats.rows[0].frecuencia_min} MHz`);
    console.log(`   Frecuencia máxima: ${stats.rows[0].frecuencia_max} MHz`);
  }
  
  console.log('\n📍 Top 10 municipios con más registros de cobertura:');
  municipios.rows.forEach((row, index) => {
    console.log(`   ${index + 1}. ${row.municipio}: ${row.registros} registros`);
  });
  
  console.log('\n🎉 Importación completada exitosamente!');
}

async function main() {
  console.log('🚀 Iniciando importación de datos de cobertura\n');
  
  try {
    await createCoberturasTable();
    await loadCSVData();
  } catch (error) {
    console.error('\n❌ Error en la importación:', error);
    process.exit(1);
  }
  
  process.exit(0);
}

main();
