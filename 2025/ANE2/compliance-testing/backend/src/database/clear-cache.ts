import { query, pool } from './connection';

async function clearCache() {
  console.log('🧹 Clearing compliance reports cache...');
  try {
    await query('DELETE FROM compliance_reports_cache');
    console.log('✅ Cache cleared successfully.');
  } catch (error) {
    console.error('❌ Error clearing cache:', error);
  } finally {
    await pool.end();
  }
}

clearCache();