import { SensorModel } from '../models/Sensor';
import { AntennaModel } from '../models/Antenna';

// Datos de prueba para sensores
const sampleSensors = [
  {
    mac: '00:11:22:33:44:55',
    name: 'Sensor Medellín Centro',
    description: 'Sensor principal en el centro de Medellín',
    lat: 6.2476,
    lng: -75.5658,
    alt: 1495,
    status: 'active' as const
  },
  {
    mac: 'AA:BB:CC:DD:EE:FF',
    name: 'Sensor Bogotá Norte',
    description: 'Sensor de monitoreo en zona norte de Bogotá',
    lat: 4.7110,
    lng: -74.0721,
    alt: 2640,
    status: 'active' as const
  },
  {
    mac: '11:22:33:44:55:66',
    name: 'Sensor Cali Sur',
    description: 'Estación de medición sur de Cali',
    lat: 3.4516,
    lng: -76.5320,
    alt: 1018,
    status: 'inactive' as const
  }
];

// Datos de prueba para antenas
const sampleAntennas = [
  {
    name: 'Antena FM-1',
    type: 'Dipolo',
    frequency_min_hz: 88000000,
    frequency_max_hz: 108000000,
    gain_db: 3.5,
    description: 'Antena omnidireccional para banda FM comercial'
  },
  {
    name: 'Antena UHF-TV',
    type: 'Yagi',
    frequency_min_hz: 470000000,
    frequency_max_hz: 698000000,
    gain_db: 12.0,
    description: 'Antena direccional para televisión UHF'
  },
  {
    name: 'Antena Wideband',
    type: 'Log-periódica',
    frequency_min_hz: 30000000,
    frequency_max_hz: 512000000,
    gain_db: 8.5,
    description: 'Antena de banda ancha para monitoreo general'
  },
  {
    name: 'Antena VHF',
    type: 'Dipolo',
    frequency_min_hz: 136000000,
    frequency_max_hz: 174000000,
    gain_db: 5.0,
    description: 'Antena para banda VHF alta'
  }
];

export async function seedDatabase() {
  console.log('🌱 Seeding database with sample data...');
  
  try {
    // Crear sensores
    console.log('\n📡 Creating sensors...');
    const createdSensors = [];
    for (const sensor of sampleSensors) {
      try {
        const existing = await SensorModel.getByMac(sensor.mac);
        if (existing) {
          console.log(`  ⚠️  Sensor ${sensor.name} already exists (${sensor.mac})`);
          createdSensors.push(existing);
        } else {
          const created = await SensorModel.create(sensor);
          console.log(`  ✅ Created sensor: ${sensor.name} (${sensor.mac})`);
          createdSensors.push(created);
        }
      } catch (error: any) {
        console.error(`  ❌ Error creating sensor ${sensor.name}:`, error.message);
      }
    }

    // Crear antenas
    console.log('\n📶 Creating antennas...');
    const createdAntennas = [];
    for (const antenna of sampleAntennas) {
      try {
        const created = await AntennaModel.create(antenna);
        console.log(`  ✅ Created antenna: ${antenna.name}`);
        createdAntennas.push(created);
      } catch (error: any) {
        console.error(`  ❌ Error creating antenna ${antenna.name}:`, error.message);
      }
    }

    // Asignar antenas a sensores
    console.log('\n🔗 Assigning antennas to sensors...');
    if (createdSensors.length > 0 && createdAntennas.length > 0) {
      try {
        // Sensor 1: Antenas FM y Wideband
        await AntennaModel.assignToSensor(createdSensors[0].id!, createdAntennas[0].id!, 1);
        await AntennaModel.assignToSensor(createdSensors[0].id!, createdAntennas[2].id!, 2);
        console.log(`  ✅ Assigned antennas to ${createdSensors[0].name}`);

        // Sensor 2: Antena UHF-TV
        if (createdSensors.length > 1) {
          await AntennaModel.assignToSensor(createdSensors[1].id!, createdAntennas[1].id!, 1);
          console.log(`  ✅ Assigned antennas to ${createdSensors[1].name}`);
        }

        // Sensor 3: Antena VHF
        if (createdSensors.length > 2) {
          await AntennaModel.assignToSensor(createdSensors[2].id!, createdAntennas[3].id!, 1);
          console.log(`  ✅ Assigned antennas to ${createdSensors[2].name}`);
        }
      } catch (error: any) {
        console.error('  ❌ Error assigning antennas:', error.message);
      }
    }

    console.log('\n✅ Database seeded successfully!');
    console.log('\n📊 Summary:');
    console.log(`  - Sensors: ${createdSensors.length}`);
    console.log(`  - Antennas: ${createdAntennas.length}`);
    
  } catch (error: any) {
    console.error('❌ Error seeding database:', error);
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  (async () => {
    // Primero inicializar la base de datos
    const { initDatabase } = require('./migrate');
    await initDatabase();
    
    // Luego hacer el seed
    await seedDatabase();
    
    process.exit(0);
  })();
}
