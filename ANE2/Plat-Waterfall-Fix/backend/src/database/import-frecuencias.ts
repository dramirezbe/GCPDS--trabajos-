import { query, pool } from './connection';
import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';

interface FrecuenciaRecord {
  frecuencia: number;
  ancho_de_banda: number;
  unidad_ancho_de_banda: string;
  potencia: number;
  unidad_potencia: string;
  servicio: string;
  municipio: string;
}

async function createFrecuenciasTable() {
  console.log('📋 Creando tabla frecuencias_consolidadas...');
  
  await query(`
    CREATE TABLE IF NOT EXISTS frecuencias_consolidadas (
      id SERIAL PRIMARY KEY,
      frecuencia NUMERIC(15, 4) NOT NULL,
      ancho_de_banda NUMERIC(15, 4),
      unidad_ancho_de_banda VARCHAR(10),
      potencia NUMERIC(15, 4),
      unidad_potencia VARCHAR(10),
      servicio VARCHAR(200),
      municipio VARCHAR(200),
      created_at TIMESTAMP DEFAULT NOW()
    )
  `);
  
  // Crear índices
  await query(`
    CREATE INDEX IF NOT EXISTS idx_frecuencias_frecuencia ON frecuencias_consolidadas(frecuencia);
    CREATE INDEX IF NOT EXISTS idx_frecuencias_servicio ON frecuencias_consolidadas(servicio);
    CREATE INDEX IF NOT EXISTS idx_frecuencias_municipio ON frecuencias_consolidadas(municipio);
  `);
  
  console.log('✅ Tabla frecuencias_consolidadas creada con índices');
}

async function loadCSVData() {
  const csvPath = path.join(__dirname, '../../../consolidado.csv');
  
  console.log(`📂 Leyendo archivo: ${csvPath}`);
  
  if (!fs.existsSync(csvPath)) {
    throw new Error(`Archivo no encontrado: ${csvPath}`);
  }
  
  const fileContent = fs.readFileSync(csvPath, 'utf-8');
  
  // Parsear CSV con punto y coma como delimitador
  // No usar cast automático porque los números tienen formato colombiano (puntos como separadores)
  const rawRecords = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    delimiter: ';',
    trim: true,
    cast: false  // Desactivar cast automático
  });
  
  // Limpiar y convertir números con formato colombiano
  const cleanNumber = (value: string): number => {
    if (!value || value === '') return 0;
    // Remover puntos usados como separadores de miles y convertir coma a punto decimal
    const cleaned = value.toString().replace(/\./g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
  };
  
  const records: FrecuenciaRecord[] = rawRecords
    .filter((rec: any) => {
      // Filtrar registros sin frecuencia válida o con servicio "cubrimiento"
      const freq = cleanNumber(rec.frecuencia);
      return freq > 0 && rec.servicio && rec.servicio.toLowerCase() !== 'cubrimiento';
    })
    .map((rec: any) => ({
      frecuencia: cleanNumber(rec.frecuencia),
      ancho_de_banda: cleanNumber(rec.ancho_de_banda),
      unidad_ancho_de_banda: rec.unidad_ancho_de_banda || '',
      potencia: cleanNumber(rec.potencia),
      unidad_potencia: rec.unidad_potencia || '',
      servicio: rec.servicio || '',
      municipio: rec.municipio || ''
    }));
  
  console.log(`📊 Total de registros a importar: ${records.length}`);
  
  // Verificar si ya hay datos
  const existingCount = await query('SELECT COUNT(*) as count FROM frecuencias_consolidadas');
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
    
    await query('TRUNCATE TABLE frecuencias_consolidadas RESTART IDENTITY');
    console.log('🗑️  Datos existentes eliminados');
  }
  
  // Insertar en lotes de 1000 registros
  const batchSize = 1000;
  let imported = 0;
  
  console.log('📤 Importando datos en lotes...');
  
  for (let i = 0; i < records.length; i += batchSize) {
    const batch = records.slice(i, i + batchSize);
    
    // Construir query de inserción múltiple
    const values: any[] = [];
    const placeholders: string[] = [];
    
    batch.forEach((record, idx) => {
      const baseIdx = idx * 7;
      placeholders.push(
        `($${baseIdx + 1}, $${baseIdx + 2}, $${baseIdx + 3}, $${baseIdx + 4}, $${baseIdx + 5}, $${baseIdx + 6}, $${baseIdx + 7})`
      );
      
      values.push(
        record.frecuencia || null,
        record.ancho_de_banda || null,
        record.unidad_ancho_de_banda || null,
        record.potencia || null,
        record.unidad_potencia || null,
        record.servicio || null,
        record.municipio || null
      );
    });
    
    await query(
      `INSERT INTO frecuencias_consolidadas 
       (frecuencia, ancho_de_banda, unidad_ancho_de_banda, potencia, unidad_potencia, servicio, municipio)
       VALUES ${placeholders.join(', ')}`,
      values
    );
    
    imported += batch.length;
    const progress = ((imported / records.length) * 100).toFixed(1);
    process.stdout.write(`\r   Progreso: ${imported}/${records.length} (${progress}%)`);
  }
  
  console.log('\n✅ Datos importados exitosamente');
  
  // Mostrar estadísticas
  const stats = await query(`
    SELECT 
      COUNT(*) as total_registros,
      COUNT(DISTINCT servicio) as servicios_unicos,
      COUNT(DISTINCT municipio) as municipios_unicos,
      MIN(frecuencia) as freq_min,
      MAX(frecuencia) as freq_max
    FROM frecuencias_consolidadas
  `);
  
  console.log('\n📊 Estadísticas de la importación:');
  console.log(`   Total de registros: ${stats.rows[0].total_registros}`);
  console.log(`   Servicios únicos: ${stats.rows[0].servicios_unicos}`);
  console.log(`   Municipios únicos: ${stats.rows[0].municipios_unicos}`);
  console.log(`   Frecuencia mínima: ${stats.rows[0].freq_min} MHz`);
  console.log(`   Frecuencia máxima: ${stats.rows[0].freq_max} MHz`);
  
  // Mostrar top 5 servicios
  const topServicios = await query(`
    SELECT servicio, COUNT(*) as cantidad
    FROM frecuencias_consolidadas
    GROUP BY servicio
    ORDER BY cantidad DESC
    LIMIT 5
  `);
  
  console.log('\n📡 Top 5 servicios más frecuentes:');
  topServicios.rows.forEach((row, idx) => {
    console.log(`   ${idx + 1}. ${row.servicio}: ${row.cantidad} registros`);
  });
}

async function main() {
  try {
    console.log('🚀 Iniciando importación de frecuencias consolidadas\n');
    
    await createFrecuenciasTable();
    await loadCSVData();
    
    console.log('\n🎉 Importación completada exitosamente!');
    await pool.end();
    process.exit(0);
  } catch (error: any) {
    console.error('\n❌ Error en la importación:', error.message);
    console.error(error);
    await pool.end();
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { createFrecuenciasTable, loadCSVData };
