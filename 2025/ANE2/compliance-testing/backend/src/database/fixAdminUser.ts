import { query } from './connection';
import bcrypt from 'bcrypt';

async function fixAdminUser() {
  try {
    console.log('🔍 Verificando usuario admin...');
    
    // Verificar usuario actual
    const result = await query('SELECT * FROM users WHERE username = $1', ['admin']);
    
    if (result.rows.length === 0) {
      console.log('❌ Usuario admin no existe');
      
      // Crear usuario admin
      const hashedPassword = await bcrypt.hash('admin123', 10);
      await query(`
        INSERT INTO users (username, password, full_name, email, role, is_active)
        VALUES ($1, $2, $3, $4, $5, $6)
      `, ['admin', hashedPassword, 'Administrador', 'admin@ane.gov.co', 'administrador', true]);
      
      console.log('✅ Usuario admin creado con rol: administrador');
    } else {
      const user = result.rows[0];
      console.log('📋 Usuario admin encontrado:');
      console.log(`   - ID: ${user.id}`);
      console.log(`   - Username: ${user.username}`);
      console.log(`   - Full Name: ${user.full_name}`);
      console.log(`   - Email: ${user.email}`);
      console.log(`   - Role: ${user.role}`);
      console.log(`   - Is Active: ${user.is_active}`);
      
      if (user.role !== 'administrador') {
        console.log('⚠️  Rol incorrecto detectado. Actualizando...');
        
        // Actualizar rol y contraseña
        const hashedPassword = await bcrypt.hash('admin123', 10);
        await query(`
          UPDATE users 
          SET role = $1, password = $2, is_active = $3
          WHERE username = $4
        `, ['administrador', hashedPassword, true, 'admin']);
        
        console.log('✅ Usuario admin actualizado con rol: administrador');
      } else {
        console.log('✅ Usuario admin tiene el rol correcto');
        
        // Actualizar solo la contraseña para asegurar que sea admin123
        const hashedPassword = await bcrypt.hash('admin123', 10);
        await query(`
          UPDATE users 
          SET password = $1
          WHERE username = $2
        `, [hashedPassword, 'admin']);
        
        console.log('✅ Contraseña actualizada');
      }
    }
    
    // Mostrar todos los usuarios
    const allUsers = await query('SELECT id, username, full_name, email, role, is_active FROM users ORDER BY id');
    console.log('\n📋 Todos los usuarios en la base de datos:');
    allUsers.rows.forEach(u => {
      console.log(`   ${u.id}. ${u.username} (${u.role}) - ${u.full_name} - Active: ${u.is_active}`);
    });
    
  } catch (error) {
    console.error('❌ Error:', error);
  }
  
  process.exit(0);
}

fixAdminUser();
