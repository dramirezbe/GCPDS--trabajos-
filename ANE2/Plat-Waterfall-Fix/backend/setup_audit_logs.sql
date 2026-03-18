-- =========================================
-- Tabla de Auditoría para Auto-Registro
-- =========================================
-- Este script crea la tabla audit_logs para 
-- rastrear automáticamente los usuarios 
-- creados mediante Azure AD

-- Crear tabla de logs de auditoría
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Comentarios descriptivos
COMMENT ON TABLE audit_logs IS 'Tabla de auditoría para rastrear acciones importantes del sistema';
COMMENT ON COLUMN audit_logs.user_id IS 'ID del usuario asociado a la acción';
COMMENT ON COLUMN audit_logs.action IS 'Tipo de acción realizada (ej: user_auto_created, role_changed, user_deactivated)';
COMMENT ON COLUMN audit_logs.details IS 'Información adicional en formato JSON (email, source, domain, etc)';
COMMENT ON COLUMN audit_logs.created_at IS 'Fecha y hora de la acción';

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Verificar que se creó correctamente
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'audit_logs'
ORDER BY ordinal_position;

-- Consulta de ejemplo: Ver últimos usuarios auto-creados
SELECT 
    al.id,
    al.created_at,
    u.email,
    u.username,
    u.role,
    al.details->>'source' as source,
    al.details->>'domain' as domain
FROM audit_logs al
JOIN users u ON al.user_id = u.id
WHERE al.action = 'user_auto_created'
ORDER BY al.created_at DESC
LIMIT 10;
