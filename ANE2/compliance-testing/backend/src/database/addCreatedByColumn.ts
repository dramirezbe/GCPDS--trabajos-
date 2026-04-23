import { query } from './connection';

async function addCreatedByColumn() {
  try {
    console.log('🔄 Verificando columna created_by en tabla campaigns...');
    
    // Verificar si la columna existe
    const checkColumn = await query(`
      SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name='campaigns' 
      AND column_name='created_by'
    `);

    if (checkColumn.rows.length === 0) {
      console.log('⚙️  Agregando columna created_by...');
      
      // Agregar la columna
      await query(`
        ALTER TABLE campaigns 
        ADD COLUMN created_by INTEGER,
        ADD CONSTRAINT fk_campaigns_created_by 
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
      `);
      
      console.log('✅ Columna created_by agregada exitosamente');
    } else {
      console.log('✅ Columna created_by ya existe');
    }

    // Verificar si el índice existe
    const checkIndex = await query(`
      SELECT indexname 
      FROM pg_indexes 
      WHERE tablename='campaigns' 
      AND indexname='idx_campaigns_created_by'
    `);

    if (checkIndex.rows.length === 0) {
      console.log('⚙️  Creando índice en created_by...');
      await query(`
        CREATE INDEX idx_campaigns_created_by ON campaigns(created_by)
      `);
      console.log('✅ Índice creado exitosamente');
    } else {
      console.log('✅ Índice ya existe');
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    // Si el error es que la constraint ya existe, ignorarlo
    if (error.message.includes('already exists')) {
      console.log('✅ La columna y constraint ya existen');
    } else {
      throw error;
    }
  }
  
  process.exit(0);
}

addCreatedByColumn();
