# Migración a PostgreSQL + TimescaleDB

Este documento describe el proceso de migración de SQLite a PostgreSQL con soporte para TimescaleDB.

## 🎯 Motivación

- **Problema**: SQLite se llena muy rápido y la aplicación se cuelga al llegar a ~2GB
- **Solución**: PostgreSQL + TimescaleDB para datos de series temporales
- **Beneficios**:
  - Escalable a millones de sensores
  - Compresión automática de datos antiguos
  - Retención automática de datos
  - Sin límite de 2GB
  - Mejor rendimiento en consultas complejas
  - Transacciones ACID completas
  - Soporte para múltiples conexiones simultáneas

## 📋 Requisitos

### Desarrollo Local
- PostgreSQL 13 o superior instalado
- Node.js 18 o superior
- Puerto 5432 disponible

### Producción
- PostgreSQL 13 o superior
- TimescaleDB extension instalada
- Base de datos configurada

## 🔧 Configuración Local

### 1. Instalar PostgreSQL

**Windows:**
```powershell
# Descargar desde: https://www.postgresql.org/download/windows/
# O usar chocolatey:
choco install postgresql
```

**Linux/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

### 2. Crear Base de Datos

```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear la base de datos
CREATE DATABASE ane_db;

# Salir
\q
```

### 3. Configurar Variables de Entorno

Copiar el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ane_db
DB_USER=postgres
DB_PASSWORD=tu_contraseña_aqui
PORT=3000
NODE_ENV=development
```

### 4. Instalar Dependencias

```bash
cd backend
npm install
```

### 5. Ejecutar Migraciones

```bash
npm run migrate
```

Este comando:
- Crea todas las tablas necesarias
- Crea índices para optimizar consultas
- Intenta crear hypertables con TimescaleDB (si está instalado)

### 6. Cargar Datos Iniciales (Opcional)

```bash
npm run seed
```

## 🚀 Instalación de TimescaleDB (Opcional para Desarrollo)

TimescaleDB proporciona optimizaciones adicionales para datos de series temporales pero **NO es obligatorio** para desarrollo local.

### Windows
```powershell
# Descargar desde: https://docs.timescale.com/install/latest/self-hosted/installation-windows/
```

### Linux/Debian
```bash
# Agregar repositorio
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"

# Importar clave GPG
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Instalar
sudo apt update
sudo apt install timescaledb-2-postgresql-14

# Configurar
sudo timescaledb-tune

# Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

### Habilitar TimescaleDB en la Base de Datos

```bash
psql -U postgres -d ane_db

# Crear extensión
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Verificar
\dx

# Salir
\q
```

## 📊 Diferencias Clave: SQLite vs PostgreSQL

### Sintaxis de Consultas

**SQLite:**
```sql
SELECT * FROM sensors WHERE id = ?
INSERT INTO sensors (...) VALUES (?, ?, ?)
SELECT strftime('%s', 'now') * 1000  -- timestamp
SELECT last_insert_rowid()
```

**PostgreSQL:**
```sql
SELECT * FROM sensors WHERE id = $1
INSERT INTO sensors (...) VALUES ($1, $2, $3) RETURNING id
SELECT EXTRACT(EPOCH FROM NOW())::BIGINT * 1000  -- timestamp
-- RETURNING id reemplaza last_insert_rowid()
```

### Tipos de Datos

| SQLite | PostgreSQL |
|--------|------------|
| INTEGER PRIMARY KEY AUTOINCREMENT | SERIAL PRIMARY KEY |
| TEXT | VARCHAR(n) o TEXT |
| REAL | NUMERIC(m,n) o DOUBLE PRECISION |
| INTEGER (timestamp) | BIGINT o TIMESTAMP |
| INTEGER (boolean) | BOOLEAN o INTEGER |

### Funciones de Fecha

| SQLite | PostgreSQL |
|--------|------------|
| datetime('now') | NOW() |
| strftime('%s', 'now') | EXTRACT(EPOCH FROM NOW()) |
| date('now') | CURRENT_DATE |

## 🏗️ Estructura de Archivos Modificados

```
backend/
├── package.json                      # ✅ Actualizado (pg, @types/pg)
├── .env.example                      # ✅ Nuevo
├── src/
│   ├── app.ts                        # ✅ Actualizado (usa migrate-postgres)
│   ├── database/
│   │   ├── connection.ts             # ✅ Reescrito (pg.Pool)
│   │   ├── migrate.ts                # ⚠️  Obsoleto (SQLite)
│   │   ├── migrate-postgres.ts       # ✅ Nuevo (PostgreSQL)
│   │   └── seed.ts                   # ⏳ Pendiente actualizar
│   ├── models/
│   │   ├── Antenna.ts                # ✅ Actualizado ($1, $2, RETURNING)
│   │   ├── Sensor.ts                 # ✅ Actualizado ($1, $2, RETURNING)
│   │   └── SensorData.ts             # ✅ Actualizado ($1, $2, RETURNING)
│   └── routes/
│       ├── campaign.ts               # ✅ Actualizado (pg client, transacciones)
│       ├── management.ts             # ✅ OK (usa modelos)
│       └── sensor.ts                 # ⏳ Revisar si usa queries directas
```

## 📝 Scripts NPM

```json
{
  "migrate": "ts-node src/database/migrate-postgres.ts",
  "seed": "ts-node src/database/seed.ts",
  "dev": "nodemon src/app.ts",
  "build": "tsc",
  "start": "node dist/app.js"
}
```

## 🧪 Verificar Migración

```bash
# Verificar tablas creadas
psql -U postgres -d ane_db -c "\dt"

# Verificar índices
psql -U postgres -d ane_db -c "\di"

# Verificar hypertables (si TimescaleDB está instalado)
psql -U postgres -d ane_db -c "SELECT * FROM timescaledb_information.hypertables;"

# Ver tamaño de la base de datos
psql -U postgres -d ane_db -c "SELECT pg_size_pretty(pg_database_size('ane_db'));"
```

## 🐳 Despliegue con Docker

### Dockerfile Backend

El Dockerfile ya no necesita Python para compilar better-sqlite3:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
EXPOSE 3000
CMD ["node", "dist/app.js"]
```

### docker-compose.yml (Recomendado)

```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: ane_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ane_db
      DB_USER: postgres
      DB_PASSWORD: ${DB_PASSWORD}
      PORT: 3000
    ports:
      - "3000:3000"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

## 📈 Beneficios de TimescaleDB

Una vez instalado TimescaleDB, obtienes:

### 1. Hypertables
Convierte `sensor_data` en una hypertable optimizada para series temporales:
```sql
SELECT create_hypertable('sensor_data', 'timestamp', if_not_exists => TRUE);
```

### 2. Compresión Automática
Comprime datos antiguos para ahorrar espacio:
```sql
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

### 3. Retención Automática
Elimina datos antiguos automáticamente:
```sql
SELECT add_retention_policy('sensor_data', INTERVAL '90 days');
```

### 4. Consultas Optimizadas
Mejora el rendimiento de agregaciones temporales:
```sql
SELECT 
  time_bucket('1 hour', timestamp) AS hour,
  mac,
  AVG(excursion_peak_to_peak_hz) as avg_excursion
FROM sensor_data
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour, mac
ORDER BY hour DESC;
```

## 🔄 Migrar Datos Existentes (Opcional)

Si necesitas migrar datos de SQLite a PostgreSQL:

```bash
# 1. Exportar datos de SQLite
sqlite3 data/ane.db .dump > dump.sql

# 2. Convertir sintaxis SQLite a PostgreSQL (script personalizado)
node scripts/convert-sqlite-to-postgres.js dump.sql > postgres.sql

# 3. Importar a PostgreSQL
psql -U postgres -d ane_db < postgres.sql
```

## ⚠️ Notas Importantes

1. **Backup**: Siempre haz backup de tus datos antes de migrar
2. **Testing**: Prueba completamente en desarrollo antes de producción
3. **TimescaleDB**: No es obligatorio para desarrollo local, pero recomendado para producción
4. **Conexiones**: PostgreSQL maneja múltiples conexiones simultáneas (configurado en Pool max: 20)
5. **Transacciones**: Usa transacciones para operaciones que modifican múltiples tablas (BEGIN/COMMIT/ROLLBACK)

## 📞 Soporte

Para problemas con la migración:
1. Verificar logs del backend: `npm run dev` muestra errores de conexión
2. Verificar logs de PostgreSQL: `sudo tail -f /var/log/postgresql/postgresql-14-main.log`
3. Verificar conexión: `psql -U postgres -d ane_db -c "SELECT NOW();"`

## ✅ Checklist de Migración

- [x] Instalar PostgreSQL localmente
- [x] Crear base de datos `ane_db`
- [x] Configurar variables de entorno en `.env`
- [x] Actualizar `package.json` con dependencias `pg`
- [x] Reescribir `connection.ts` con Pool de PostgreSQL
- [x] Crear `migrate-postgres.ts` con esquemas PostgreSQL
- [x] Actualizar modelos (Sensor, Antenna, SensorData)
- [x] Actualizar rutas (campaign.ts con transacciones)
- [ ] Actualizar `seed.ts` con sintaxis PostgreSQL
- [ ] Revisar `sensor.ts` para queries directas
- [ ] Ejecutar `npm install`
- [ ] Ejecutar `npm run migrate`
- [ ] Ejecutar `npm run seed` (si aplica)
- [ ] Probar endpoints en Postman/Thunder Client
- [ ] Verificar WebSocket funciona
- [ ] (Opcional) Instalar TimescaleDB en producción
- [ ] Desplegar a servidor con PostgreSQL configurado
