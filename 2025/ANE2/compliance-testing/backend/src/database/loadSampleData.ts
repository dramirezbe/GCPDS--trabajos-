import * as fs from 'fs';
import * as path from 'path';
import { SensorDataModel } from '../models/SensorData';
import { SensorModel } from '../models/Sensor';

interface JsonData {
  device_id: number;
  campaign_id: number;
  Pxx: number[];
  start_freq_hz: number;
  end_freq_hz: number;
  timestamp: number;
}

async function loadSampleData() {
  console.log('📊 Loading sample spectrum data from JSON files...\n');

  try {
    // Obtener sensores existentes
    const sensors = await SensorModel.getAll();
    if (sensors.length === 0) {
      console.log('❌ No sensors found. Please run seed first.');
      return;
    }

    console.log(`Found ${sensors.length} sensors:\n`);
    sensors.forEach((sensor, index) => {
      console.log(`  ${index + 1}. ${sensor.name} (${sensor.mac})`);
    });
    console.log('');

    // Rutas a los archivos JSON
    const frontendDataPath = path.join(__dirname, '../../../frontend/data');
    const amJsonPath = path.join(frontendDataPath, 'comparative_AM_json');
    const fmJsonPath = path.join(frontendDataPath, 'comparative_FM_json');

    // Verificar que existen las carpetas
    if (!fs.existsSync(amJsonPath) || !fs.existsSync(fmJsonPath)) {
      console.log('❌ Sample data folders not found.');
      console.log('   Expected paths:');
      console.log(`   - ${amJsonPath}`);
      console.log(`   - ${fmJsonPath}`);
      return;
    }

    // Cargar datos AM para el primer sensor (Medellín)
    const amFiles = fs.readdirSync(amJsonPath).filter(f => f.endsWith('.json'));
    console.log(`📡 Loading ${amFiles.length} AM spectrum files for ${sensors[0].name}...`);
    
    let amCount = 0;
    for (const filename of amFiles) {
      const filePath = path.join(amJsonPath, filename);
      const jsonData: JsonData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      
      await SensorDataModel.saveData({
        mac: sensors[0].mac,
        campaign_id: jsonData.campaign_id,
        Pxx: jsonData.Pxx,
        start_freq_hz: jsonData.start_freq_hz,
        end_freq_hz: jsonData.end_freq_hz,
        timestamp: jsonData.timestamp,
        lat: sensors[0].lat,
        lng: sensors[0].lng
      });
      
      amCount++;
      if (amCount % 5 === 0) {
        process.stdout.write(`  Loaded ${amCount}/${amFiles.length}...\r`);
      }
    }
    console.log(`  ✅ Loaded ${amCount} AM spectrum captures for ${sensors[0].name}\n`);

    // Cargar datos FM para el segundo sensor (Bogotá)
    if (sensors.length > 1) {
      const fmFiles = fs.readdirSync(fmJsonPath).filter(f => f.endsWith('.json'));
      console.log(`📡 Loading ${fmFiles.length} FM spectrum files for ${sensors[1].name}...`);
      
      let fmCount = 0;
      for (const filename of fmFiles) {
        const filePath = path.join(fmJsonPath, filename);
        const jsonData: JsonData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        
        await SensorDataModel.saveData({
          mac: sensors[1].mac,
          campaign_id: jsonData.campaign_id,
          Pxx: jsonData.Pxx,
          start_freq_hz: jsonData.start_freq_hz,
          end_freq_hz: jsonData.end_freq_hz,
          timestamp: jsonData.timestamp,
          lat: sensors[1].lat,
          lng: sensors[1].lng
        });
        
        fmCount++;
        if (fmCount % 5 === 0) {
          process.stdout.write(`  Loaded ${fmCount}/${fmFiles.length}...\r`);
        }
      }
      console.log(`  ✅ Loaded ${fmCount} FM spectrum captures for ${sensors[1].name}\n`);
    }

    console.log('');
    console.log('✅ Sample data loaded successfully!');
    console.log('');
    console.log('You can now:');
    console.log('  1. Start the backend: npm run dev');
    console.log('  2. View data in frontend analysis panel');
    console.log(`  3. Query: GET /api/sensor/${sensors[0].mac}/latest-data?limit=10`);
    
  } catch (error: any) {
    console.error('❌ Error loading sample data:', error.message);
    console.error(error);
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  loadSampleData()
    .then(() => {
      console.log('\n✅ Done!');
      process.exit(0);
    })
    .catch((error) => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

export { loadSampleData };
