import { Pool, PoolClient, QueryResult } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// Configuración de PostgreSQL
const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT || '5432'),
  max: 20, // Máximo de conexiones en el pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Manejo de errores del pool
pool.on('error', (err: Error) => {
  console.error('Error inesperado en el pool de PostgreSQL:', err);
});

// Función para ejecutar queries
export async function query(text: string, params?: any[]): Promise<QueryResult> {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    if (duration > 1000) {
      console.log('🐌 Query lenta ejecutada:', { text, duration, rows: res.rowCount });
    }
    return res;
  } catch (error) {
    console.error('❌ Error en query:', { text, params, error });
    throw error;
  }
}

// Función para obtener un cliente del pool (para transacciones)
export async function getClient(): Promise<PoolClient> {
  return await pool.connect();
}

// Funciones auxiliares para mantener compatibilidad con código anterior
export async function dbRun(sql: string, params: any[] = []): Promise<QueryResult> {
  return await query(sql, params);
}

export async function dbGet(sql: string, params: any[] = []): Promise<any> {
  const result = await query(sql, params);
  return result.rows[0] || null;
}

export async function dbAll(sql: string, params: any[] = []): Promise<any[]> {
  const result = await query(sql, params);
  return result.rows;
}

export async function dbExec(sql: string): Promise<void> {
  await query(sql);
}

// Función para cerrar el pool (útil para testing y shutdown)
export async function closePool(): Promise<void> {
  await pool.end();
  console.log('🔌 Pool de PostgreSQL cerrado');
}

// Verificar conexión al iniciar
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('❌ Error conectando a PostgreSQL:', err);
  } else {
    console.log('✅ Conectado a PostgreSQL:', res.rows[0].now);
  }
});

export { pool };
export default pool;
