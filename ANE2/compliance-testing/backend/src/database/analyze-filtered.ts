import { readFileSync } from 'fs';
import { join } from 'path';
import { parse } from 'csv-parse/sync';

const csvPath = join('C:', 'ANE REALTIME', 'consolidado.csv');
const fileContent = readFileSync(csvPath, 'utf-8');

const cleanNumber = (value: string): number => {
  if (!value || value === '') return 0;
  const cleaned = value.toString().replace(/\./g, '').replace(',', '.');
  return parseFloat(cleaned) || 0;
};

const rawRecords = parse(fileContent, {
  columns: true,
  skip_empty_lines: true,
  delimiter: ';',
  trim: true,
  cast: false
});

console.log(`\n📊 Análisis de registros del CSV:\n`);
console.log(`Total de registros en CSV: ${rawRecords.length}`);

let sinFrecuencia = 0;
let sinServicio = 0;
let conCubrimiento = 0;
let validos = 0;

const serviciosUnicos = new Set<string>();
const serviciosFiltrados = new Map<string, number>();

rawRecords.forEach((rec: any) => {
  const freq = cleanNumber(rec.frecuencia);
  const servicio = rec.servicio || '';
  
  serviciosUnicos.add(servicio);
  
  if (freq <= 0) {
    sinFrecuencia++;
    if (!serviciosFiltrados.has(`Sin frecuencia (${servicio})`)) {
      serviciosFiltrados.set(`Sin frecuencia (${servicio})`, 0);
    }
    serviciosFiltrados.set(`Sin frecuencia (${servicio})`, 
      serviciosFiltrados.get(`Sin frecuencia (${servicio})`)! + 1);
    return;
  }
  
  if (!servicio) {
    sinServicio++;
    return;
  }
  
  if (servicio.toLowerCase() === 'cubrimiento') {
    conCubrimiento++;
    return;
  }
  
  validos++;
});

console.log(`\nRegistros válidos (importados): ${validos}`);
console.log(`\nRegistros filtrados:`);
console.log(`  - Sin frecuencia válida: ${sinFrecuencia}`);
console.log(`  - Sin servicio: ${sinServicio}`);
console.log(`  - Con servicio "cubrimiento": ${conCubrimiento}`);
console.log(`  - Total filtrados: ${sinFrecuencia + sinServicio + conCubrimiento}`);

console.log(`\n📋 Todos los servicios encontrados (${serviciosUnicos.size} únicos):`);
[...serviciosUnicos].sort().forEach(s => {
  const count = rawRecords.filter((r: any) => r.servicio === s).length;
  console.log(`  - "${s}": ${count} registros`);
});

console.log(`\n🔍 Desglose de registros sin frecuencia por servicio:`);
[...serviciosFiltrados.entries()]
  .sort((a, b) => b[1] - a[1])
  .forEach(([servicio, count]) => {
    console.log(`  ${servicio}: ${count} registros`);
  });

// Mostrar algunos ejemplos de registros filtrados
console.log(`\n📝 Ejemplos de registros filtrados (sin frecuencia):`);
let ejemplos = 0;
for (const rec of rawRecords) {
  const r = rec as any;
  const freq = cleanNumber(r.frecuencia);
  if (freq <= 0 && ejemplos < 5) {
    console.log(`  Servicio: "${r.servicio}", Frecuencia: "${r.frecuencia}", Municipio: ${r.municipio}`);
    ejemplos++;
  }
}

process.exit(0);
