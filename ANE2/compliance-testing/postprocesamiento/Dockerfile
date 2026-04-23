FROM python:3.11-slim

LABEL maintainer="ANE REALTIME"
LABEL description="Microservicio de análisis espectral para reportes de cumplimiento"

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para datos
RUN mkdir -p /opt/ane-realtime/data

# Copiar CSV de licencias
COPY consolidado_bbdd_asignación.csv /opt/ane-realtime/data/licencias.csv

# Puerto del servicio
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Configuración via variables de entorno (gunicorn no acepta args custom)
ENV ANE_LIC_CSV=/opt/ane-realtime/data/licencias.csv

# Comando de inicio - gunicorn con 4 workers (multi-proceso, sin GIL)
CMD ["gunicorn", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "3600", \
     "--keep-alive", "5", \
     "server_flask:app"]

