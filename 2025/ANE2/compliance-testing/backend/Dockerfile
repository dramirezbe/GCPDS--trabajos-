# Backend Dockerfile - PostgreSQL Version
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias incluyendo dev dependencies
RUN npm install && npm cache clean --force

# Copiar código fuente
COPY src ./src
COPY tsconfig.json ./

# Compilar TypeScript
RUN npx tsc

# Imagen de producción
FROM node:18-alpine

WORKDIR /app

# Instalar solo dependencias de producción
COPY package*.json ./
RUN npm install --omit=dev && npm cache clean --force

# Copiar código compilado
COPY --from=builder /app/dist ./dist

# Exponer puerto
EXPOSE 3000

# Variables de entorno por defecto
ENV NODE_ENV=production
ENV PORT=3000

# Comando de inicio
CMD ["node", "dist/app.js"]
