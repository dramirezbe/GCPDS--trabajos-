# Frontend Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Argumentos de build para URLs (con valores por defecto para producción)
ARG VITE_API_URL=/api
ARG VITE_WS_URL=/ws

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm install && npm cache clean --force

# Copiar código fuente
COPY . .

# Build de producción
# Definir variables de entorno para Vite
# FORZAMOS URL RELATIVA para evitar problemas de Mixed Content
ENV VITE_API_URL=/api
ENV VITE_WS_URL=/ws

# Mostrar variables para debug
RUN echo "Building with VITE_API_URL=${VITE_API_URL} VITE_WS_URL=${VITE_WS_URL}"

RUN npm run build

# Imagen de producción con nginx
FROM nginx:alpine

# Copiar archivos compilados
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
